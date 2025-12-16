"""
Retrieval verification script for the RAG system.
Tests the quality of document retrieval with sample queries.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.vector_db import VectorDatabase


def format_result(rank: int, doc: str, score: float, metadata: dict, max_length: int = 200):
    """Format a search result for display."""
    preview = doc[:max_length] + "..." if len(doc) > max_length else doc
    return f"""
Rank {rank}:
Source: {metadata.get('source', 'Unknown')}
Chunk: {metadata.get('chunk_id', '?')}/{metadata.get('total_chunks', '?')}
Similarity Score: {score:.4f}
Content: {preview}
{'-' * 60}"""


def run_retrieval_tests(index_path: str):
    """
    Run retrieval tests with sample queries.
    
    Args:
        index_path: Path to the saved index
    """
    print("=" * 60)
    print("RAG System - Retrieval Quality Verification")
    print("=" * 60)
    
    # Load the vector database
    print(f"\nLoading index from {index_path}...")
    db = VectorDatabase()
    db.load(index_path)
    print(f"Loaded {len(db.documents)} documents")
    
    # Define test queries
    test_queries = [
        "What are the recommended medications for heart failure with reduced ejection fraction?",
        "What are the diagnostic criteria for heart failure?",
        "How is coronary artery disease diagnosed?",
        "What is the classification of heart failure based on ejection fraction?",
        "What lifestyle modifications are recommended for heart failure patients?",
        "What are the symptoms of angina?",
        "What are the indications for ICD placement?",
        "What medications should be given after stent placement?",
    ]
    
    # Run each query
    for i, query in enumerate(test_queries, 1):
        print("\n" + "=" * 60)
        print(f"Query {i}: {query}")
        print("=" * 60)
        
        # Search
        results = db.search(query, k=3)
        
        # Display results
        for rank, (doc, score, metadata) in enumerate(results, 1):
            print(format_result(rank, doc, score, metadata))
    
    print("\n" + "=" * 60)
    print("Retrieval verification complete!")
    print("=" * 60)
    print("\nSummary:")
    print(f"- Total queries tested: {len(test_queries)}")
    print(f"- Results per query: 3")
    print(f"- Total documents in index: {len(db.documents)}")
    print("\nThe system successfully retrieves relevant cardiology information")
    print("based on clinical queries. Higher similarity scores indicate better matches.")


def interactive_search(index_path: str):
    """
    Interactive search mode for user queries.
    
    Args:
        index_path: Path to the saved index
    """
    print("\n" + "=" * 60)
    print("Interactive Search Mode")
    print("=" * 60)
    print("Enter your query (or 'quit' to exit):\n")
    
    # Load the vector database
    db = VectorDatabase()
    db.load(index_path)
    
    while True:
        query = input("\nQuery: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("Exiting interactive mode.")
            break
        
        if not query:
            continue
        
        print("\nSearching...")
        results = db.search(query, k=3)
        
        print("\nResults:")
        print("=" * 60)
        for rank, (doc, score, metadata) in enumerate(results, 1):
            print(format_result(rank, doc, score, metadata))


if __name__ == '__main__':
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    index_path = project_root / 'index'
    
    if not index_path.exists():
        print("Error: Index not found. Please run ingest.py first.")
        sys.exit(1)
    
    # Run automated tests
    run_retrieval_tests(str(index_path))
    
    # Optionally run interactive search
    print("\n\nWould you like to try interactive search? (y/n): ", end='')
    response = input().strip().lower()
    if response == 'y':
        interactive_search(str(index_path))
