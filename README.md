# RAG System for Healthcare

A minimal Retrieval-Augmented Generation (RAG) prototype focused on retrieval quality for cardiology documents. This system extracts, processes, and indexes medical documents to enable efficient semantic search of clinical information.

## Overview

This project implements a retrieval-focused RAG system designed for healthcare documentation, specifically targeting cardiology guidelines and patient reports. The system:

- Extracts and cleans text from cardiology documents
- Splits documents into meaningful chunks with overlap for context preservation
- Converts text chunks into vector embeddings using TF-IDF
- Indexes embeddings using cosine similarity for fast semantic search
- Verifies retrieval quality through automated test queries

## Project Structure

```
Rag-system-4-healthcare/
├── data/
│   └── cardiology/          # Sample cardiology documents
│       ├── heart_failure_guidelines.txt
│       ├── patient_report_1.txt
│       └── patient_report_2.txt
├── src/
│   ├── __init__.py
│   ├── document_processor.py  # Text extraction, cleaning, and chunking
│   └── vector_db.py           # Embedding generation and vector database
├── scripts/
│   ├── ingest.py              # Document ingestion pipeline
│   ├── verify_retrieval.py    # Retrieval quality verification
│   └── demo.py                # Quick demonstration script
├── requirements.txt           # Python dependencies
└── README.md
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/giorgioabbruscato/Rag-system-4-healthcare.git
cd Rag-system-4-healthcare
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Ingest Documents

Process and index the cardiology documents:

```bash
python scripts/ingest.py
```

This will:
- Extract text from all `.txt` files in `data/cardiology/`
- Clean and split text into chunks (800 characters with 100 character overlap)
- Generate TF-IDF embeddings
- Build a searchable index
- Save the index to the `index/` directory

### 2. Verify Retrieval Quality

Test the retrieval system with sample clinical queries:

```bash
python scripts/verify_retrieval.py
```

This will:
- Load the vector index
- Run 8 predefined clinical queries
- Display the top 3 most relevant document chunks for each query
- Show similarity scores (higher score = better match)

Sample queries include:
- "What are the recommended medications for heart failure with reduced ejection fraction?"
- "What are the diagnostic criteria for heart failure?"
- "How is coronary artery disease diagnosed?"
- And more...

The script also offers an optional interactive search mode where you can enter custom queries.

## Technical Details

### Document Processing

- **Text Extraction**: Reads text files and preserves structure
- **Cleaning**: Normalizes whitespace while preserving paragraph breaks
- **Chunking**: Splits documents at paragraph boundaries with configurable chunk size (default: 800 characters) and overlap (default: 100 characters)

### Embeddings

- **Method**: TF-IDF (Term Frequency-Inverse Document Frequency)
  - Sparse vector representation
  - No external model downloads required
  - Fast and efficient for text similarity
  - Uses bi-gram features for better context capture

### Vector Database

- **Similarity Metric**: Cosine similarity
- **Persistence**: Index and documents saved to disk for reuse
- **Retrieval**: Returns top-k most similar documents with similarity scores

## Sample Documents

The system includes three cardiology documents:

1. **Heart Failure Guidelines**: ACC/AHA guidelines covering classification, diagnosis, and management of heart failure
2. **Patient Report 1**: Case of new-onset heart failure with reduced ejection fraction
3. **Patient Report 2**: Case of stable angina with coronary artery disease requiring intervention

## Extending the System

To add more documents:

1. Place `.txt` files in `data/cardiology/`
2. Re-run the ingestion script: `python scripts/ingest.py`

To customize chunking:

```python
# In src/document_processor.py
chunks = split_into_chunks(text, chunk_size=1000, overlap=100)
```

To customize TF-IDF parameters:

```python
# In src/vector_db.py
self.vectorizer = TfidfVectorizer(
    max_features=10000,  # Increase vocabulary size
    ngram_range=(1, 3),  # Use trigrams
    min_df=2             # Minimum document frequency
)
```

## Dependencies

- `scikit-learn`: TF-IDF vectorization and cosine similarity
- `numpy`: Numerical operations

## Future Enhancements

This is a minimal prototype focused on retrieval quality. Potential enhancements:

- [ ] Add generative component (LLM integration)
- [ ] Support for PDF and DOCX document formats
- [ ] Advanced chunking strategies (semantic splitting)
- [ ] Metadata filtering and hybrid search
- [ ] Web interface for queries
- [ ] Evaluation metrics for retrieval quality
- [ ] Support for more medical specialties

## License

See LICENSE file for details.