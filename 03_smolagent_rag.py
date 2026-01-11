from smolagents import OpenAIServerModel, ToolCallingAgent, HfApiModel, tool, GradioUI
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os



load_dotenv()

reasoning_model_id = os.getenv("REASONING_MODEL_ID")
tool_model_id = os.getenv("TOOL_MODEL_ID")
huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")
model_provider = os.getenv("MODEL_PROVIDER")

def get_model(model_id):
    using_huggingface = os.getenv("USE_HUGGINGFACE", "yes").lower() == "yes"
    if using_huggingface:
        model = HfApiModel(model_id=model_id, token=huggingface_api_token)
        assert model is not None, f"Failed to call {model_id} from HuggingFace API"
        return model
    else:
        return OpenAIServerModel(
            model_id=model_id,
            api_base="http://localhost:11434/v1",
            api_key="ollama"
        )

# Create the reasoner model for better RAG (direct text generation, not code)
reasoning_model = get_model(reasoning_model_id)

# Initialize vector store and embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    model_kwargs={'device': 'cpu'}
)
db_dir = os.path.join(os.path.dirname(__file__), "chroma_db")
vectordb = Chroma(persist_directory=db_dir, embedding_function=embeddings)

@tool
def rag_with_reasoner(user_query: str) -> str:
    """
    This is a RAG tool that takes in a user query about GDPR-related cases and searches for relevant 
    GDPR articles from the vector database. Returns answers with specific article citations and source URLs.
    
    Args:
        user_query: The user's question about GDPR-related cases or regulations to query the vector database with.
    """
    # Search for relevant documents - increase k for better coverage
    docs = vectordb.similarity_search(user_query, k=5)

    assert len(docs) > 0, f"No documents found for query: {user_query}"
    
    # Organize documents by article number to group related content and avoid duplicates
    articles_dict = {}
    for doc in docs:
        metadata = doc.metadata
        article_num = metadata.get('article_number', 'Unknown')
        article_id = metadata.get('id', 'Unknown')
        title = metadata.get('title', 'Unknown')
        url = metadata.get('url', '')
        
        if article_num not in articles_dict:
            articles_dict[article_num] = {
                'title': title,
                'id': article_id,
                'url': url,
                'chunks': []
            }
        articles_dict[article_num]['chunks'].append(doc.page_content)
    
    assert len(articles_dict) > 0, f"No articles found for query: {user_query}"

    # Build structured context with article metadata
    context_parts = []
    article_list = []
    
    for article_num, article_info in sorted(articles_dict.items()):
        # Combine chunks for this article (limit to avoid token bloat)
        article_content = "\n\n[...continued...]\n\n".join(article_info['chunks'][:2])
        
        context_parts.append(f"""
--- ARTICLE {article_num}: {article_info['title']} ---
Article ID: {article_info['id']}
Source: {article_info['url']}

Relevant Content:
{article_content}
""")
        
        # Track for citation list
        article_list.append({
            'num': article_num,
            'title': article_info['title'],
            'url': article_info['url']
        })
    
    context = "\n".join(context_parts)
    
    # Improved GDPR-specific prompt with citation requirements
    prompt = f"""You are an expert GDPR legal assistant. Analyze the following GDPR articles retrieved from the database 
and provide a comprehensive, well-cited answer to the user's question.

YOUR TASK:
1. Analyze the user's question in the context of GDPR regulations
2. Identify which specific GDPR article(s) are most relevant to the question
3. Extract and explain the key provisions from those articles that address the question
4. Always cite article numbers explicitly (e.g., "According to Article 15 GDPR..." or "Article 32 states...")

RESPONSE FORMAT:
Your response MUST follow this structure:

**Direct Answer:**
[Provide a clear, direct answer to the user's question]

**Relevant GDPR Articles:**

For each relevant article, include:
- **Article [number] GDPR - [article title]**
  - Key provisions: [Explain how this article relates to the question]
  - Citation: {article_list[0]['url'] if article_list else 'Source URL'}

[Repeat for each relevant article]

**Summary:**
[Brief summary tying together how the cited articles collectively address the question]

**Additional Notes:**
[If applicable, mention any limitations, related articles not found, or practical considerations]

IMPORTANT:
- ALWAYS cite specific article numbers (e.g., "Article 15", "Article 32")
- Include source URLs in citations
- Be precise about which article provisions apply
- If the context doesn't fully answer the question, clearly state what's missing
- Use legal terminology accurately

CONTEXT FROM GDPR DATABASE:
{context}

USER QUESTION: {user_query}

YOUR RESPONSE (with proper citations):"""
    
    # Get response from reasoning model (direct text generation)
    # Use the model's chat completion interface for text generation
    messages = [{"role": "user", "content": prompt}]
    
    try:
        # Try calling the model directly with messages
        response = reasoning_model(messages)
        
        # Extract text from response (handle different response formats)
        if isinstance(response, str):
            response_text = response
        elif hasattr(response, 'content'):
            response_text = response.content
        elif hasattr(response, 'choices') and len(response.choices) > 0:
            # OpenAI-style response with choices
            choice = response.choices[0]
            if hasattr(choice, 'message'):
                response_text = choice.message.content
            elif hasattr(choice, 'text'):
                response_text = choice.text
            elif isinstance(choice, dict):
                response_text = choice.get('message', {}).get('content', str(response))
            else:
                response_text = str(choice)
        elif isinstance(response, dict):
            # Dictionary response - try common keys
            if 'content' in response:
                response_text = response['content']
            elif 'text' in response:
                response_text = response['text']
            elif 'choices' in response and len(response['choices']) > 0:
                response_text = response['choices'][0].get('message', {}).get('content', str(response))
            else:
                response_text = str(response)
        elif isinstance(response, list) and len(response) > 0:
            # List response - get first item
            if isinstance(response[0], dict):
                response_text = response[0].get('content', str(response))
            else:
                response_text = str(response[0])
        else:
            assert False, f"Unknown response type: {type(response)}"
    except Exception as e:
        # Fallback: if direct call fails, try alternative methods
        try:
            # Try using complete method if available
            if hasattr(reasoning_model, 'complete'):
                response_text = reasoning_model.complete(prompt)
            else:
                raise e
        except:
            response_text = f"Error generating response: {str(e)}"
    
    # Append formatted source list
    if article_list:
        response_text += "\n\n" + "="*60 + "\n"
        response_text += "CITED SOURCES:\n"
        response_text += "="*60 + "\n"
        for article in article_list:
            response_text += f"• Article {article['num']} GDPR - {article['title']}\n"
            response_text += f"  Source: {article['url']}\n\n"
    
    return response_text

# Create the primary agent to direct the conversation
tool_model = get_model(tool_model_id)
assert tool_model is not None, f"Failed to call {tool_model_id}"
print(tool_model.__dict__)
primary_agent = ToolCallingAgent(tools=[rag_with_reasoner], model=tool_model, add_base_tools=False, max_steps=6, planning_interval=5,  verbosity_level=4)

# Example prompt: Compare and contrast the services offered by RankBoost and Omni Marketing
def main():
    GradioUI(primary_agent).launch()

if __name__ == "__main__":
    main()
    