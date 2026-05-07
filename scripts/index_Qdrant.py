"""
Vectorstore Manager - Singleton with datapizza pipeline for in-memory Qdrant.
"""
import os
import json
import glob
import uuid
from typing import Optional
from datapizza.core.vectorstore import VectorConfig
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.type.type import Chunk, DenseEmbedding
from sentence_transformers import SentenceTransformer

from src.config import settings
from src.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# --- PATHS ---
JSONL_PATH = os.path.join(settings.dataset_dir, "documents.jsonl")
GUIDELINES_DIR = settings.guidelines_dir

# -----------------------------
# Singleton Vectorstore
# -----------------------------
_vectorstore: Optional[QdrantVectorstore] = None
_embedder: Optional[SentenceTransformer] = None
_initialized = False


class LocalEmbedder:
    """Adapter for SentenceTransformer -> embeddings."""
    def __init__(self, model: SentenceTransformer):
        self.model = model
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


def get_vectorstore() -> QdrantVectorstore:
    """Return the singleton vectorstore, initializing it if needed."""
    global _vectorstore, _embedder, _initialized
    
    if _vectorstore is None:
        logger.info("Initializing Qdrant in-memory...")
        _vectorstore = QdrantVectorstore(location=":memory:")
        _embedder = SentenceTransformer(settings.embedding_model)
    
    if not _initialized:
        logger.info("Auto-indexing collections...")
        _ensure_collections_populated()
        _initialized = True
    
    return _vectorstore


def get_embedder() -> SentenceTransformer:
    """Return the singleton sentence transformer."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def _ensure_collections_populated():
    """Check and populate 'cases' and 'guidelines' collections if empty."""
    global _vectorstore, _embedder
    
    # 'cases' collection
    try:
        collections = _vectorstore.get_collections()
        collection_names = [c[0] if isinstance(c, tuple) else c for c in collections]
        if "cases" in collection_names:
            logger.info("[IndexQdrant] Collection 'cases' exists, checking if populated...")
            try:
                test = _vectorstore.search(
                    collection_name="cases",
                    query_vector=[0.0] * EMBEDDING_DIM,
                    vector_name="text_embedding",
                    k=1
                )
                if test:
                    logger.info("[IndexQdrant] Collection 'cases' already has data.")
                    return
            except Exception as e:
                logger.warning("Failed to check if 'cases' is populated", error=str(e))
    except Exception as e:
        logger.warning("Failed to get collections", error=str(e))
    
    logger.info("Creating and indexing collections...")
    _create_and_index_all()


def _create_and_index_all():
    """Create and index all collections."""
    global _vectorstore, _embedder
    
    # Create 'cases' collection
    vector_config = [VectorConfig(name=settings.vector_name, dimensions=settings.embedding_dim)]
    
    try:
        _vectorstore.delete_collection("cases")
    except Exception as e:
        logger.warning("Collection 'cases' could not be deleted or does not exist", error=str(e))
    
    _vectorstore.create_collection("cases", vector_config=vector_config)
    
    # Index cases and frames
    _index_cases()
    
    # Create 'guidelines' collection
    try:
        _vectorstore.delete_collection("guidelines")
    except Exception as e:
        logger.warning("Collection 'guidelines' could not be deleted or does not exist", error=str(e))
    
    _vectorstore.create_collection("guidelines", vector_config=vector_config)
    _index_guidelines()


def _index_cases():
    """Index cases and frames from documents.jsonl."""
    global _vectorstore, _embedder
    
    if not os.path.exists(JSONL_PATH):
        logger.warning(f"{JSONL_PATH} not found. Skipping cases indexing.")
        return
    
    logger.info(f"Loading documents from {JSONL_PATH}...")
    
    # Load all documents (case_card + frame)
    docs_text = []
    docs_metadata = []
    
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            doc_type = obj["metadata"].get("document_type")
            # Index both case_card and frame
            if doc_type not in ["case_card", "frame"]:
                continue
            docs_text.append(obj["content"])
            docs_metadata.append(obj["metadata"])
    
    if not docs_text:
        logger.warning("No documents found.")
        return
    
    logger.info(f"Embedding {len(docs_text)} documents...")
    
    # Generate embeddings using LocalEmbedder
    local_embedder = LocalEmbedder(_embedder)
    embeddings = local_embedder.embed(docs_text)
    
    # Add to Qdrant
    logger.info(f"Adding documents to Qdrant...")
    chunks = []
    for i in range(len(docs_text)):
        case_id = docs_metadata[i].get("case_id", f"unknown_{i}")
        doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"case_{case_id}_{i}"))
        emb = DenseEmbedding(name=settings.vector_name, vector=embeddings[i])
        
        metadata = docs_metadata[i].copy()
        metadata["original_id"] = case_id
        
        chunks.append(
            Chunk(
                id=doc_uuid,
                text=docs_text[i],
                embeddings=[emb],
                metadata=metadata
            )
        )
    
    _vectorstore.add(chunk=chunks, collection_name="cases")
    
    # Count indexed document types
    doc_types = {}
    for m in docs_metadata:
        dt = m.get("document_type", "unknown")
        doc_types[dt] = doc_types.get(dt, 0) + 1
    
    types_str = ", ".join([f"{v} {k}s" for k, v in doc_types.items()])
    logger.info(f"✓ Indexed {len(docs_text)} documents ({types_str}).")


def _index_guidelines():
    """Index guidelines from .txt files."""
    global _vectorstore, _embedder
    
    if not os.path.isdir(GUIDELINES_DIR):
        logger.warning(f"{GUIDELINES_DIR} not found. Skipping guidelines indexing.")
        return
    
    logger.info(f"Loading guidelines from {GUIDELINES_DIR}...")
    
    def chunk_text(text: str, chunk_size: int = settings.chunk_size, overlap: int = settings.chunk_overlap):
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks
    
    docs_text = []
    docs_metadata = []
    idx = 0
    
    for path in glob.glob(os.path.join(GUIDELINES_DIR, "*.txt")):
        fname = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        
        if not text:
            continue
        
        chunks = chunk_text(text)
        for j, chunk in enumerate(chunks):
            docs_text.append(chunk)
            docs_metadata.append({
                "source": fname,
                "chunk_id": j,
                "document_type": "guideline",
                "original_id": f"guideline_{idx}"
            })
            idx += 1
    
    if not docs_text:
        print("[IndexQdrant] No guidelines found.")
        return
    
    print(f"[IndexQdrant] Embedding {len(docs_text)} guideline chunks...")
    
    # Generate embeddings
    local_embedder = LocalEmbedder(_embedder)
    embeddings = local_embedder.embed(docs_text)
    
    # Add to Qdrant
    print(f"[IndexQdrant] Adding guidelines to Qdrant...")
    chunks = []
    for i in range(len(docs_text)):
        doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"guideline_{i}"))
        emb = DenseEmbedding(name=settings.vector_name, vector=embeddings[i])
        chunks.append(
            Chunk(
                id=doc_uuid,
                text=docs_text[i],
                embeddings=[emb],
                metadata=docs_metadata[i]
            )
        )
    
    _vectorstore.add(chunk=chunks, collection_name="guidelines")
    print(f"[IndexQdrant] ✓ Indexed {len(docs_text)} guideline chunks from {len(set(m['source'] for m in docs_metadata))} files.")


def reset_collections():
    """Delete and recreate all collections (for testing/soft reset)."""
    global _vectorstore, _initialized
    
    if _vectorstore is None:
        return
    
    logger.info("[IndexQdrant] Resetting all collections...")
    
    try:
        _vectorstore.delete_collection("cases")
    except Exception as e:
        logger.warning("Failed to delete 'cases' during reset", error=str(e))
    
    try:
        _vectorstore.delete_collection("guidelines")
    except Exception as e:
        logger.warning("Failed to delete 'guidelines' during reset", error=str(e))
    
    _initialized = False
    _ensure_collections_populated()
    
    print("[IndexQdrant] ✓ Collections reset complete.")


# -----------------------------
# CLI for manual testing
# -----------------------------
if __name__ == "__main__":
    print("=== Index Qdrant - Pipeline Test ===")
    print(f"JSONL_PATH: {JSONL_PATH}")
    
    vs = get_vectorstore()
    print("\n✓ Vectorstore ready and populated!")
    
    # Test search
    emb = get_embedder()
    test_query = "dilated cardiomyopathy with reduced ejection fraction"
    test_emb = emb.encode([test_query], normalize_embeddings=True).tolist()[0]
    
    print(f"\nTest search: '{test_query}'")
    results = vs.search(
        collection_name="cases",
        query_vector=test_emb,
        vector_name=settings.vector_name,
        k=3
    )
    
    print(f"Found {len(results)} results:")
    for i, hit in enumerate(results, 1):
        case_id = hit.metadata.get("original_id", hit.id)
        label = hit.metadata.get("diagnosis_label_pretty", "Unknown")
        doc_type = hit.metadata.get("document_type", "unknown")
        print(f"  {i}. {case_id} ({doc_type}) - {label}")
        print(f"     {hit.text[:100]}...")
