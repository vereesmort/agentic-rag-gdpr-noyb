import time
import os
import json

import schedule
from dotenv import load_dotenv

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.schema import Document

load_dotenv()


def load_and_process_json(json_file_path: str):
    """Load JSON file and convert to LangChain documents"""
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for item in data:

        content = (
            f"Title: {item.get('title', '')}\n"
            f"ID: {item.get('id', '')}\n"
            f"Article Number: {item.get('article_number', '')}\n"
            f"Text: {item.get('text', '')}"
        )

        metadata = {
            "id": item.get("id", ""),
            "title": item.get("title", ""),
            "article_number": item.get("article_number", ""),
            "type": item.get("type", ""),
            "jurisdiction": item.get("jurisdiction", ""),
            "url": item.get("url", ""),
            "date": item.get("data", ""),
            "fine": item.get("fine", ""),
            "currency": item.get("currency", ""),
            "gdpr_articles": item.get("gdpr_articles", ""),
        }

        documents.append(Document(page_content=content, metadata=metadata))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks = text_splitter.split_documents(documents)
    return chunks


def create_or_update_vector_store(chunks, persist_directory: str):
    """Create or update a persisted Chroma vector store"""
    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
    )

    if os.path.exists(persist_directory):
        print(f"Loading existing vector store at {persist_directory}")
        vectordb = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

        try:
            ids_to_remove = [doc.metadata.get("id") for doc in chunks if doc.metadata.get("id")]
            ids_to_remove = [i for i in ids_to_remove if i]  # filter empties
            if ids_to_remove:
                vectordb.delete(ids=ids_to_remove)
        except Exception:
            # Fallback: ignore deletion if unsupported by the runtime Chroma adapter
            pass

        # Add new/updated chunks
        vectordb.add_documents(chunks)
    else:
        print("Creating new vector store...")
        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=persist_directory,
        )

    # Ensure persistence
    try:
        vectordb.persist()
    except Exception:
        # Some adapters persist automatically; ignore if not available
        pass

    return vectordb


def main():
    json_file_path = os.path.join(os.path.dirname(__file__), "data", "extracted_weekly.json")
    db_dir = os.path.join(os.path.dirname(__file__), "chroma_db")

    print(f"Loading and processing JSON file from {json_file_path}...")
    chunks = load_and_process_json(json_file_path)
    print(f"Created {len(chunks)} chunks from JSON file")

    print("Adding to vector store...")
    vectordb = create_or_update_vector_store(chunks, db_dir)
    print(f"Vector store at {db_dir} updated.")


schedule.every().monday.at("00:10").do(main)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)
