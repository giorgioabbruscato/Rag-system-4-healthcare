"""
Embedding generation and vector database module.
Uses TF-IDF for embeddings and cosine similarity for retrieval.
"""

import os
import pickle
from typing import List, Tuple, Dict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class VectorDatabase:
    """
    Simple vector database using TF-IDF embeddings and cosine similarity.
    """
    
    def __init__(self):
        """
        Initialize the vector database.
        """
        self.vectorizer = TfidfVectorizer(
            max_features=1000,  # Reduced for memory efficiency
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.9
        )
        self.document_vectors = None
        self.documents = []
        self.metadata = []
    
    def build_index(self, documents: List[str], metadata: List[Dict] = None):
        """
        Build TF-IDF index from documents.
        
        Args:
            documents: List of document chunks
            metadata: Optional list of metadata dictionaries for each document
        """
        if not documents:
            raise ValueError("Cannot build index from empty document list")
        
        print(f"Building TF-IDF index for {len(documents)} documents...")
        
        # Fit vectorizer and transform documents
        self.document_vectors = self.vectorizer.fit_transform(documents)
        
        # Store documents and metadata
        self.documents = documents
        self.metadata = metadata if metadata else [{}] * len(documents)
        
        print(f"Index built successfully with {len(self.documents)} documents")
    
    def search(self, query: str, k: int = 5) -> List[Tuple[str, float, Dict]]:
        """
        Search for similar documents using cosine similarity.
        
        Args:
            query: Query text
            k: Number of results to return
            
        Returns:
            List of tuples (document, similarity_score, metadata)
        """
        if self.document_vectors is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        # Transform query
        query_vector = self.vectorizer.transform([query])
        
        # Calculate cosine similarities
        similarities = cosine_similarity(query_vector, self.document_vectors)[0]
        
        # Get top k indices
        top_indices = np.argsort(similarities)[::-1][:k]
        
        # Prepare results (note: higher similarity is better, unlike distance)
        results = []
        for idx in top_indices:
            if idx < len(self.documents):
                results.append((
                    self.documents[idx],
                    float(similarities[idx]),
                    self.metadata[idx]
                ))
        
        return results
    
    def save(self, path: str):
        """
        Save the index and documents to disk.
        
        Args:
            path: Directory path to save the index
        """
        os.makedirs(path, exist_ok=True)
        
        # Save vectorizer and vectors
        with open(os.path.join(path, 'index.pkl'), 'wb') as f:
            pickle.dump({
                'vectorizer': self.vectorizer,
                'document_vectors': self.document_vectors,
                'documents': self.documents,
                'metadata': self.metadata
            }, f)
        
        print(f"Index saved to {path}")
    
    def load(self, path: str):
        """
        Load the index and documents from disk.
        
        Args:
            path: Directory path to load the index from
            
        Raises:
            FileNotFoundError: If the index file doesn't exist
        """
        index_file = os.path.join(path, 'index.pkl')
        
        if not os.path.exists(index_file):
            raise FileNotFoundError(
                f"Index file not found at {index_file}. "
                "Please run the ingestion script first."
            )
        
        with open(index_file, 'rb') as f:
            data = pickle.load(f)
            self.vectorizer = data['vectorizer']
            self.document_vectors = data['document_vectors']
            self.documents = data['documents']
            self.metadata = data['metadata']
        
        print(f"Index loaded from {path}")
