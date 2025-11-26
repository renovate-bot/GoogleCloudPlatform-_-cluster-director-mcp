#!/usr/bin/env python3

import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, SentenceTransformersTokenTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain_classic.chains import RetrievalQA
from langchain_classic.prompts import PromptTemplate

# ==============================================================================
# 🎯 CONFIGURATION
# ==============================================================================
# Model Names (must be pulled locally via 'ollama pull <model>')
#LLM_MODEL = "gemma3:270m"         # Smallest LLM for fast generation
LLM_MODEL = "gemma3:1b"
EMBEDDING_MODEL = "embeddinggemma"  # Embedding model for retrieval
VECTOR_DB_DIR = "./chroma_db"
DOCUMENT_PATH = "some_CV.pdf" 

# ==============================================================================
# ✍️ CUSTOM PROMPT TEMPLATE
# ==============================================================================
RAG_PROMPT_TEMPLATE = """
**SYSTEM INSTRUCTIONS:** You are an expert Q&A assistant named RAG-Gemma. Your primary function is to answer user questions truthfully and accurately based *only* on the provided context, which is text extracted from a document.

If the answer cannot be found in the context, clearly state: "I am unable to find the answer to this question in the provided document context." Do not use external knowledge.

**CONTEXT:**
---
{context}
---

**USER QUESTION:** {question}

**RESPONSE:** (Provide a clear, concise, and professional answer)
"""

# ==============================================================================
# 1️⃣ DATA INGESTION FUNCTION
# ==============================================================================
def ingest_data(document_path: str):
    """Loads, splits, embeds, and stores documents in ChromaDB."""
    print(f"--- 1. Ingesting Data from {document_path} ---")
    
    if not os.path.exists(document_path):
        print(f"Error: Document not found at '{document_path}'. Please replace the DOCUMENT_PATH.")
        return None, None

    # Load and split documents
    loader = PyPDFLoader(document_path)
    documents = loader.load()
    print(f"Loaded {len(documents)} pages.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
    )

    # Initialize the splitter with a custom Sentence Transformers model
    text_splitter = SentenceTransformersTokenTextSplitter(
        model_name="sentence-transformers/paraphrase-MiniLM-L6-v2",
        tokens_per_chunk=50,
        chunk_overlap=10
        )


    chunks = text_splitter.split_documents(documents)
    print(f"Split document into {len(chunks)} chunks.")

    # Create Ollama Embeddings using EmbeddingGemma
    print(f"Initializing Ollama embeddings using: {EMBEDDING_MODEL}")
    ollama_embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

    # Create and persist the Vector Store
    print(f"Creating ChromaDB Vector Store at {VECTOR_DB_DIR}...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=ollama_embeddings,
        persist_directory=VECTOR_DB_DIR
    )
    print("Ingestion complete. Database persisted.")
    return vectorstore, ollama_embeddings

# ==============================================================================
# QUERY CHAIN FUNCTION
# ==============================================================================
def run_query_chain(vectorstore: Chroma, llm_model: str):
    """Sets up and runs the RAG chain with a custom prompt."""
    print("\n--- 2. Initializing RAG Query Chain ---")

    # Initialize the local LLM (Gemma 3 270M)
    print(f"Initializing Ollama LLM using: {llm_model}")
    llm = Ollama(model=llm_model)

    # Create the Retriever (searches for 4 relevant chunks)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    # Create the Prompt Template object
    custom_prompt = PromptTemplate(
        template=RAG_PROMPT_TEMPLATE,
        input_variables=["context", "question"]
    )

    # Create the RAG Chain (RetrievalQA)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": custom_prompt},
        return_source_documents=True
    )
    
    return qa_chain

# ==============================================================================
# MAIN FUNCTION
# ==============================================================================
if __name__ == "__main__":
    
    # Check for existing DB to skip re-ingestion
    if os.path.exists(VECTOR_DB_DIR) and os.listdir(VECTOR_DB_DIR):
        print("Existing ChromaDB found. Loading from disk.")
        ollama_embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
        vectorstore = Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=ollama_embeddings)
    else:
        # Run ingestion pipeline
        vectorstore, ollama_embeddings = ingest_data(DOCUMENT_PATH)

    if vectorstore:
        # Run RAG Query Chain pipeline
        rag_chain = run_query_chain(vectorstore, LLM_MODEL)
        
        while True:
            try:
                print("-" * 50)
                user_query = input("Ask a question about the document (or type 'exit'):\n> ")
                if user_query.lower() == 'exit':
                    break
                
                print("\nThinking...")
                
                # Run the chain
                result = rag_chain.invoke({"query": user_query})

                # Print the final answer and sources
                print("\n RAG Answer:")
                print(result['result'].strip())
                
                print("\n Sources Used:")
                for i, doc in enumerate(result['source_documents']):
                    print(f"  - Document {i+1}: {doc.metadata.get('source', 'N/A')} (Page: {doc.metadata.get('page', 'N/A')})")
                    # Show a snippet for context
                    print(f"    Snippet: {doc.page_content[:150].replace('\n', ' ')}...\n") 
                    
            except Exception as e:
                print(f"\nAn error occurred: {e}")
                print("Make sure 'ollama serve' is running and the models are pulled.")
                break

    print("Application closed.")

    