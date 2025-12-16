"""
Document processing module for extracting and cleaning text from various formats.
"""

import os
import re
from typing import List


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Extracted text content
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # For this minimal prototype, we handle .txt files
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    # Normalize multiple spaces to single space (but preserve newlines)
    lines = text.split('\n')
    cleaned_lines = [re.sub(r' +', ' ', line.strip()) for line in lines]
    
    # Rejoin with single newlines
    text = '\n'.join(cleaned_lines)
    
    # Normalize multiple newlines to double newlines (paragraph breaks)
    text = re.sub(r'\n\n+', '\n\n', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def split_into_chunks(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks for better context preservation.
    
    Args:
        text: Text to split
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    chunks = []
    # Split by double newline first to get paragraphs
    paragraphs = text.split('\n\n')
    
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If adding this paragraph exceeds chunk_size, save current chunk
        if len(current_chunk) + len(para) + 2 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Start new chunk with overlap from previous
            words = current_chunk.split()
            if len(words) > 10:
                overlap_text = ' '.join(words[-10:])
                current_chunk = overlap_text + "\n\n" + para
            else:
                current_chunk = para
        else:
            current_chunk = (current_chunk + "\n\n" + para) if current_chunk else para
    
    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def process_document(file_path: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Complete document processing pipeline: extract, clean, and chunk.
    
    Args:
        file_path: Path to the document
        chunk_size: Target size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of processed text chunks
    """
    text = extract_text_from_file(file_path)
    cleaned_text = clean_text(text)
    chunks = split_into_chunks(cleaned_text, chunk_size, overlap)
    return chunks
