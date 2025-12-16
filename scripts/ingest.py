"""
Document ingestion pipeline for the RAG system.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.document_processor import process_document
from src.vector_db import VectorDatabase


def ingest_documents(data_dir: str, index_path: str = 'index'):
    """
    Ingest all documents from a directory into the vector database.
    
    Args:
        data_dir: Directory containing documents to ingest
        index_path: Path where the index will be saved
    """
    print("=" * 60)
    print("RAG System - Document Ingestion Pipeline")
    print("=" * 60)
    
    # Initialize vector database
    db = VectorDatabase()
    
    # Collect all documents
    all_chunks = []
    all_metadata = []
    
    # Process each file in the directory
    data_path = Path(data_dir)
    txt_files = list(data_path.glob('**/*.txt'))
    
    if not txt_files:
        print(f"No .txt files found in {data_dir}")
        return
    
    print(f"\nFound {len(txt_files)} document(s) to process:")
    for file_path in txt_files:
        print(f"  - {file_path.name}")
    
    print("\nProcessing documents...")
    for file_path in txt_files:
        print(f"\nProcessing: {file_path.name}")
        
        # Process document into chunks
        chunks = process_document(str(file_path), chunk_size=800, overlap=100)
        print(f"  Created {len(chunks)} chunks")
        
        # Add chunks and metadata
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadata.append({
                'source': file_path.name,
                'chunk_id': i,
                'total_chunks': len(chunks)
            })
    
    print(f"\n\nTotal chunks created: {len(all_chunks)}")
    
    # Build index
    print("\nBuilding vector index...")
    db.build_index(all_chunks, all_metadata)
    
    # Save index
    print(f"\nSaving index to {index_path}...")
    db.save(index_path)
    
    print("\n" + "=" * 60)
    print("Ingestion complete!")
    print("=" * 60)


if __name__ == '__main__':
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    data_dir = project_root / 'data' / 'cardiology'
    index_path = project_root / 'index'
    
    ingest_documents(str(data_dir), str(index_path))
