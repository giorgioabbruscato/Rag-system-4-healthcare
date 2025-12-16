#!/usr/bin/env python3
"""
Quick demonstration script for the RAG prototype.
Shows end-to-end functionality: ingestion and retrieval.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.document_processor import process_document
from src.vector_db import VectorDatabase


def main():
    print("=" * 70)
    print("RAG System for Healthcare - Quick Demo")
    print("=" * 70)
    
    # Check if index exists
    index_path = Path(__file__).parent.parent / 'index'
    
    if not index_path.exists():
        print("\n⚠️  Index not found. Please run: python scripts/ingest.py")
        return
    
    # Load the database
    print("\n📚 Loading vector database...")
    db = VectorDatabase()
    db.load(str(index_path))
    print(f"✓ Loaded {len(db.documents)} document chunks")
    
    # Demo queries
    demo_queries = [
        "What are the key medications for treating heart failure?",
        "How do you diagnose coronary artery disease?",
        "What is ejection fraction?"
    ]
    
    print("\n" + "=" * 70)
    print("Running Demo Queries")
    print("=" * 70)
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n🔍 Query {i}: {query}")
        print("-" * 70)
        
        results = db.search(query, k=2)
        
        for rank, (doc, score, metadata) in enumerate(results, 1):
            source = metadata.get('source', 'Unknown')
            chunk_num = metadata.get('chunk_id', 0) + 1
            total_chunks = metadata.get('total_chunks', 0)
            
            print(f"\n  [{rank}] {source} (Chunk {chunk_num}/{total_chunks})")
            print(f"      Similarity: {score:.3f}")
            preview = doc[:150].replace('\n', ' ')
            print(f"      Preview: {preview}...")
    
    print("\n" + "=" * 70)
    print("✓ Demo Complete!")
    print("=" * 70)
    print("\nThe RAG system successfully:")
    print("  • Indexed cardiology documents (guidelines & patient reports)")
    print("  • Split text into meaningful chunks with overlap")
    print("  • Created searchable vector embeddings (TF-IDF)")
    print("  • Retrieved relevant clinical information based on queries")
    print("\nNo generative component added - focus is on retrieval quality.")
    print("=" * 70)


if __name__ == '__main__':
    main()
