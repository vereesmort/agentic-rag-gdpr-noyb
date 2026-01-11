from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from dotenv import load_dotenv
import os
import shutil
import json

load_dotenv()

def load_and_process_json(json_file_path: str):
    """Load JSON file and convert to LangChain documents."""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    documents = []
    for item in data:
        # Combine title, id, and text for better context
        content = f"Title: {item.get('title', '')}\n"
        content += f"ID: {item.get('id', '')}\n"
        content += f"Article Number: {item.get('article_number', '')}\n"
        content += f"Text: {item.get('text', '')}"
        
        # Create metadata from JSON fields
        metadata = {
            'id': item.get('id', ''),
            'title': item.get('title', ''),
            'article_number': item.get('article_number', ''),
            'type': item.get('type', ''),
            'url': item.get('url', '')
        }
        
        documents.append(Document(page_content=content, metadata=metadata))
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.split_documents(documents)
    return chunks

def create_vector_store(chunks, persist_directory: str):
    """Create and persist Chroma vector store."""
    # Clear existing vector store if it exists
    if os.path.exists(persist_directory):
        print(f"Clearing existing vector store at {persist_directory}")
        shutil.rmtree(persist_directory)
    
    # Initialize HuggingFace embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={'device': 'cpu'}
    )
    
    # Create and persist Chroma vector store
    print("Creating new vector store...")
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    return vectordb

def main():
    # Define paths
    json_file_path = os.path.join(os.path.dirname(__file__), "data", "gdpr_articles.json")
    db_dir = os.path.join(os.path.dirname(__file__), "chroma_db")
    
    # Process JSON file
    print(f"Loading and processing JSON file from {json_file_path}...")
    chunks = load_and_process_json(json_file_path)
    print(f"Created {len(chunks)} chunks from JSON file")
    
    # Create vector store
    print("Creating vector store...")
    vectordb = create_vector_store(chunks, db_dir)
    print(f"Vector store created and persisted at {db_dir}")

if __name__ == "__main__":
    main()
