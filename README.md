# Agentic RAG for GDPR Articles and NOYB Decision Cases

An Agentic Retrieval-Augmented Generation (RAG) system that helps users navigate GDPR regulations and find relevant NOYB (None Of Your Business) decision cases. The system uses an agentic approach with reasoning capabilities to provide accurate, well-cited answers about GDPR articles and historical enforcement decisions.

## Overview

This project implements an agentic RAG system that combines:
- **GDPR Articles**: Comprehensive knowledge base of GDPR articles sourced from [gdprhub.eu](https://gdprhub.eu)
- **NOYB Decision Cases**: Historical enforcement decisions from NOYB, Europe's privacy enforcement organization
- **Intelligent Query Handling**: The system automatically determines whether queries require GDPR article information or historical case precedents

## Features

### 🎯 Dual Knowledge Base Search
- **GDPR Article Queries**: Ask about GDPR regulations, articles, and legal requirements. The system retrieves and cites relevant GDPR articles with proper source attribution.
- **Historical Decision Queries**: Ask about past enforcement cases, precedents, or decisions. The system searches through NOYB's decision cases to find relevant historical examples.

### 🤖 Agentic Architecture
- **Two-Model System**: 
  - **Reasoning Model**: Analyzes retrieved context and generates well-structured, cited responses
  - **Tool-Calling Model**: Orchestrates the conversation and decides when to use the RAG tool
- **Citation Support**: All responses include proper citations with article numbers and source URLs
- **Context-Aware Responses**: The system understands query intent and retrieves the most relevant information

### 💬 Interactive Interface
- **Streamlit Web UI**: User-friendly chat interface for asking questions
- **Chat History**: Maintains conversation context throughout the session
- **Gradio Alternative**: Also supports Gradio UI for interactive usage

## Architecture

```
User Query
    ↓
Primary Agent (Tool-Calling Model)
    ↓
RAG Tool with Reasoner
    ↓
Vector Database (ChromaDB)
    ├── GDPR Articles (from gdprhub.eu)
    └── NOYB Decision Cases
    ↓
Similarity Search (Embeddings: all-mpnet-base-v2)
    ↓
Reasoning Model (Processes context + generates answer)
    ↓
Formatted Response with Citations
```

## Technology Stack

- **Python**: 3.11+
- **LangChain**: Vector store integration and document processing
- **ChromaDB**: Vector database for semantic search (supports both local and cloud)
- **HuggingFace**: Embeddings (`sentence-transformers/all-mpnet-base-v2`) and model APIs
- **smolagents**: Agent framework for tool-calling and reasoning
- **Streamlit**: Web interface for user interactions
- **BeautifulSoup**: HTML parsing for GDPR article extraction

## Installation

### Prerequisites

- Python 3.11 or higher
- HuggingFace API token (recommended for better rate limits)
- Optional: ChromaDB Cloud credentials (or use local ChromaDB)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agentic-rag-gdpr-noyb
   ```

2. **Install dependencies**
   
   Using uv:
   ```bash
   uv sync
   ```

3. **Configure environment variables**
   
   Copy the `env` file and update it with your credentials:
   ```bash
   cp env .env
   ```
   
   Required environment variables:
   - `HUGGINGFACE_API_TOKEN`: Your HuggingFace API token (get from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens))
   - `REASONING_MODEL_ID`: Model ID for reasoning (e.g., `moonshotai/Kimi-K2-Thinking`)
   - `TOOL_MODEL_ID`: Model ID for tool-calling (e.g., `meta-llama/Llama-3.2-3B-Instruct`)
   
   Optional:
   - `USE_HUGGINGFACE`: Set to `yes` or `no` (default: `yes`)
   - `CHROMA_API_KEY`: For ChromaDB Cloud (leave empty for local ChromaDB)
   - `CHROMA_COLLECTION_NAME`: Collection name for vector store (default: `gdpr_articles`)

4. **Ingest GDPR Articles**
   
   First, fetch GDPR articles from gdprhub.eu:
   ```bash
   python 01_get_knowledge.py
   ```
   
   This creates `data/gdpr_articles.json` with article data.

5. **Create Vector Database**
   
   For local ChromaDB:
   ```bash
   python 02_vector_ingestion.py
   ```
   
   For ChromaDB Cloud:
   ```bash
   python vectordb_ingestion.py
   ```

6. **Add NOYB Decision Cases** (if available as PDFs or JSON)
   
   If you have NOYB case documents in PDF format:
   ```bash
   python ingest_pdfs.py
   ```
   
   Or process JSON files with case data using the ingestion scripts.

## Usage

### Streamlit Web Interface (Recommended)

Launch the Streamlit interface:
```bash
streamlit run streamlit.py
```

Then open your browser to the URL shown (typically `http://localhost:8501`).

**Example Queries:**
- "What does GDPR say about data portability?"
- "Find historical cases related to data breach notifications"
- "What are the requirements for consent under Article 7?"
- "Show me NOYB decisions about cookie consent"

### Gradio Interface (Alternative)

Run the agent with Gradio UI:
```bash
python 03_smolagent_rag.py
```

### Direct Python Usage

You can also use the agent programmatically:
```python
from 03_smolagent_rag import primary_agent

response = primary_agent.run("What does Article 15 GDPR say about access rights?")
print(response)
```

## Project Structure

```
agentic-rag-gdpr-noyb/
├── data/                      # Data directory
│   ├── gdpr_articles.json    # Scraped GDPR articles
│   └── [NOYB case files]     # NOYB decision cases (PDFs/JSON)
├── chroma_db/                 # Local ChromaDB storage
├── 01_get_knowledge.py              # Script to scrape GDPR articles from gdprhub.eu
├── 02_vector_ingestion.py         # Script to create local vector database
├── 03_smolagent_rag.py        # Main agent implementation
├── streamlit.py               # Streamlit web interface
├── pyproject.toml             # Project configuration
└── README.md                  # This file
```

## How It Works

### Query Processing Flow

1. **User Query**: User asks a question via the Streamlit interface
2. **Agent Routing**: The primary agent (tool-calling model) analyzes the query
3. **Tool Selection**: Agent decides to use the `rag_with_reasoner` tool
4. **Semantic Search**: Query is embedded and matched against the vector database
5. **Context Retrieval**: Top-k most relevant documents are retrieved (k=5 by default)
6. **Reasoning**: The reasoning model processes the context and generates a structured answer
7. **Citation**: Response includes proper citations with article numbers and source URLs
8. **Display**: Formatted answer is shown to the user

### Response Format

The system provides structured responses with:
- **Direct Answer**: Clear, concise answer to the question
- **Relevant Articles/Cases**: List of relevant GDPR articles or NOYB cases
- **Citations**: Article numbers, titles, and source URLs
- **Summary**: Brief summary tying together the information
- **Additional Notes**: Limitations or related information

## Configuration

### Model Selection

The system supports two model providers:

1. **HuggingFace API** (default): Set `USE_HUGGINGFACE=yes` in `.env`
   - Requires `HUGGINGFACE_API_TOKEN`
   - Supports various models via HuggingFace Inference API

2. **Ollama** (local): Set `USE_HUGGINGFACE=no` in `.env`
   - Requires local Ollama server running on `localhost:11434`
   - Useful for privacy-sensitive deployments

### Vector Database Options

1. **Local ChromaDB** (default): No additional configuration needed
   - Data stored in `chroma_db/` directory
   - Suitable for development and small deployments

2. **ChromaDB Cloud**: Configure in `.env`
   - Requires `CHROMA_API_KEY`, `CHROMA_TENANT`, `CHROMA_DATABASE`
   - Better for production and scalability

## Examples

### Example 1: GDPR Article Query

**User**: "What are my rights regarding data portability?"

**System Response**:
```
**Direct Answer:**
Under GDPR, you have the right to data portability as outlined in Article 20...

**Relevant GDPR Articles:**
- **Article 20 GDPR - Right to data portability**
  - Key provisions: The data subject shall have the right to receive...
  - Citation: https://gdprhub.eu/index.php?title=Article_20_GDPR

**Summary:**
Article 20 provides the right to receive personal data in a structured...
```

### Example 2: Historical Decision Query

**User**: "Find cases where NOYB ruled on cookie consent violations"

**System Response**:
```
Based on NOYB's decision cases, here are relevant enforcement actions...

[Case summaries with dates, companies, and outcomes]

**Cited Sources:**
• Case XYZ-2023-001: Cookie Consent Violation - Company ABC
  Source: [URL to case]
```

## Troubleshooting

### Common Issues

1. **No results found**: Ensure the vector database has been created and populated
2. **Rate limit errors**: Get a HuggingFace API token for higher rate limits
3. **Connection errors**: Check your internet connection and API credentials
4. **Empty responses**: Verify that the data ingestion completed successfully

### Debug Mode

To see more detailed logging, you can modify the agent configuration in `03_smolagent_rag.py` to increase verbosity.

## Acknowledgments

- GDPR articles sourced from [gdprhub.eu](https://gdprhub.eu)
- NOYB decision cases from NOYB (None Of Your Business)
- Built with [smolagents](https://github.com/huggingface/smolagents), [LangChain](https://www.langchain.com/), and [ChromaDB](https://www.trychroma.com/)

## Support

For issues, questions, or contributions, please open an issue on the repository.
