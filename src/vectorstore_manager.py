"""
Vectorstore Manager - Singleton per gestire Qdrant in-memory con indexing automatico.
"""
import os
import json
import glob
import uuid
from typing import Optional
from sentence_transformers import SentenceTransformer
from datapizza.core.vectorstore import VectorConfig
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.type.type import Chunk, DenseEmbedding

# -----------------------------
# Config
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATASET_DIR = os.path.join(DATA_DIR, "dataset_built")
GUIDELINES_DIR = os.path.join(DATA_DIR, "guidelines_txt")
JSONL_PATH = os.path.join(DATASET_DIR, "documents.jsonl")

EMB_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# -----------------------------
# Singleton Vectorstore
# -----------------------------
_vectorstore: Optional[QdrantVectorstore] = None
_embedder: Optional[SentenceTransformer] = None
_initialized = False


class LocalEmbedder:
    """Adapter per SentenceTransformer -> datapizza pipeline."""
    def __init__(self, model: SentenceTransformer):
        self.model = model
    
    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


def get_vectorstore() -> QdrantVectorstore:
    """Ritorna il vectorstore singleton, inizializzandolo se necessario."""
    global _vectorstore, _embedder, _initialized
    
    if _vectorstore is None:
        print("[VectorstoreManager] Initializing Qdrant in-memory...")
        _vectorstore = QdrantVectorstore(location=":memory:")
        _embedder = SentenceTransformer(EMB_MODEL)
    
    if not _initialized:
        print("[VectorstoreManager] Auto-indexing collections...")
        _ensure_collections_populated()
        _initialized = True
    
    return _vectorstore


def get_embedder() -> SentenceTransformer:
    """Ritorna il sentence transformer singleton."""
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMB_MODEL)
    return _embedder


def _ensure_collections_populated():
    """Controlla e popola le collection 'cases' e 'guidelines' se vuote."""
    global _vectorstore, _embedder
    
    cases_done = False
    guidelines_done = False
    
    # Collection 'cases'
    try:
        collections = _vectorstore.get_collections()
        # get_collections ritorna lista di tuple (name, config)
        collection_names = [c[0] if isinstance(c, tuple) else c for c in collections]
        if "cases" in collection_names:
            print("[VectorstoreManager] Collection 'cases' exists, checking if populated...")
            try:
                test = _vectorstore.search(
                    collection_name="cases",
                    query_vector=[0.0] * EMBEDDING_DIM,
                    vector_name="text_embedding",
                    k=1
                )
                if test:
                    print(f"[VectorstoreManager] Collection 'cases' already has data.")
                    cases_done = True
            except:
                pass
            if not cases_done:
                print("[VectorstoreManager] Collection 'cases' is empty, indexing...")
                _index_cases()
        else:
            raise ValueError("Not found")
    except Exception as e:
        print(f"[VectorstoreManager] Collection 'cases' not found, creating and indexing... ({e})")
        _create_and_index_cases()
    
    # Collection 'guidelines'
    try:
        collections = _vectorstore.get_collections()
        collection_names = [c[0] if isinstance(c, tuple) else c for c in collections]
        if "guidelines" in collection_names:
            print("[VectorstoreManager] Collection 'guidelines' exists, checking if populated...")
            try:
                test = _vectorstore.search(
                    collection_name="guidelines",
                    query_vector=[0.0] * EMBEDDING_DIM,
                    vector_name="text_embedding",
                    k=1
                )
                if test:
                    print(f"[VectorstoreManager] Collection 'guidelines' already has data.")
                    guidelines_done = True
            except:
                pass
            if not guidelines_done:
                print("[VectorstoreManager] Collection 'guidelines' is empty, indexing...")
                _index_guidelines()
        else:
            raise ValueError("Not found")
    except Exception as e:
        print(f"[VectorstoreManager] Collection 'guidelines' not found, creating and indexing... ({e})")
        _create_and_index_guidelines()


def _create_and_index_cases():
    """Crea collection 'cases' e indicizza i documenti."""
    global _vectorstore
    
    vector_config = [
        VectorConfig(name="text_embedding", dimensions=EMBEDDING_DIM)
    ]
    
    try:
        _vectorstore.delete_collection("cases")
    except:
        pass
    
    _vectorstore.create_collection("cases", vector_config=vector_config)
    _index_cases()


def _index_cases():
    """Indicizza case_cards da documents.jsonl."""
    global _vectorstore, _embedder
    
    if not os.path.exists(JSONL_PATH):
        print(f"[VectorstoreManager] WARNING: {JSONL_PATH} not found. Skipping cases indexing.")
        return
    
    print(f"[VectorstoreManager] Loading cases from {JSONL_PATH}...")
    
    docs_text = []
    docs_ids = []
    docs_metadata = []
    
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj["metadata"].get("document_type") != "case_card":
                continue
            
            case_id = obj["metadata"]["case_id"]
            # Genera UUID deterministico dal case_id
            doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"case_{case_id}"))
            docs_ids.append(doc_uuid)
            docs_text.append(obj["content"])
            # Salva il case_id originale nei metadata
            metadata = obj["metadata"].copy()
            metadata["original_id"] = case_id
            docs_metadata.append(metadata)
    
    if not docs_text:
        print("[VectorstoreManager] No case_cards found in JSONL.")
        return
    
    print(f"[VectorstoreManager] Embedding {len(docs_text)} cases...")
    embeddings = _embedder.encode(docs_text, normalize_embeddings=True).tolist()
    
    print(f"[VectorstoreManager] Adding cases to Qdrant...")
    chunks = []
    for i in range(len(docs_ids)):
        emb = DenseEmbedding(name="text_embedding", vector=embeddings[i])
        chunks.append(
            Chunk(
                id=docs_ids[i],
                text=docs_text[i],
                embeddings=[emb],
                metadata=docs_metadata[i]
            )
        )
    _vectorstore.add(chunk=chunks, collection_name="cases")
    
    print(f"[VectorstoreManager] ✓ Indexed {len(docs_ids)} cases.")


def _create_and_index_guidelines():
    """Crea collection 'guidelines' e indicizza le guidelines."""
    global _vectorstore
    
    vector_config = [
        VectorConfig(name="text_embedding", dimensions=EMBEDDING_DIM)
    ]
    
    try:
        _vectorstore.delete_collection("guidelines")
    except:
        pass
    
    _vectorstore.create_collection("guidelines", vector_config=vector_config)
    _index_guidelines()


def _index_guidelines():
    """Indicizza guidelines da file .txt."""
    global _vectorstore, _embedder
    
    if not os.path.isdir(GUIDELINES_DIR):
        print(f"[VectorstoreManager] WARNING: {GUIDELINES_DIR} not found. Skipping guidelines indexing.")
        return
    
    print(f"[VectorstoreManager] Loading guidelines from {GUIDELINES_DIR}...")
    
    def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150):
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks
    
    docs_text = []
    docs_ids = []
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
            # Genera UUID deterministico
            doc_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"guideline_{idx}"))
            docs_ids.append(doc_uuid)
            docs_text.append(chunk)
            docs_metadata.append({
                "source": fname,
                "chunk_id": j,
                "document_type": "guideline",
                "original_id": f"guideline_{idx}"
            })
            idx += 1
    
    if not docs_text:
        print("[VectorstoreManager] No guidelines found.")
        return
    
    print(f"[VectorstoreManager] Embedding {len(docs_text)} guideline chunks...")
    embeddings = _embedder.encode(docs_text, normalize_embeddings=True).tolist()
    
    print(f"[VectorstoreManager] Adding guidelines to Qdrant...")
    chunks = []
    for i in range(len(docs_ids)):
        emb = DenseEmbedding(name="text_embedding", vector=embeddings[i])
        chunks.append(
            Chunk(
                id=docs_ids[i],
                text=docs_text[i],
                embeddings=[emb],
                metadata=docs_metadata[i]
            )
        )
    _vectorstore.add(chunk=chunks, collection_name="guidelines")
    
    print(f"[VectorstoreManager] ✓ Indexed {len(docs_ids)} guideline chunks from {len(set(m['source'] for m in docs_metadata))} files.")


def reset_collections():
    """Elimina e ricrea tutte le collection (per testing)."""
    global _vectorstore, _initialized
    
    if _vectorstore is None:
        return
    
    print("[VectorstoreManager] Resetting all collections...")
    
    try:
        _vectorstore.delete_collection("cases")
    except:
        pass
    
    try:
        _vectorstore.delete_collection("guidelines")
    except:
        pass
    
    _initialized = False
    _ensure_collections_populated()
    
    print("[VectorstoreManager] ✓ Collections reset complete.")


# -----------------------------
# CLI per test manuale
# -----------------------------
if __name__ == "__main__":
    print("=== Vectorstore Manager Test ===")
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
        vector_name="text_embedding",
        k=3
    )
    
    print(f"Found {len(results)} results:")
    for i, hit in enumerate(results, 1):
        # hit è un Chunk, non ha .score direttamente
        case_id = hit.metadata.get("original_id", hit.id)
        label = hit.metadata.get("diagnosis_label_pretty", "Unknown")
        print(f"  {i}. {case_id} - {label}")
        print(f"     {hit.text[:100]}...")
