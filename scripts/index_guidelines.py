import os
import glob
from sentence_transformers import SentenceTransformer
from datapizza.core.vectorstore import VectorConfig
from datapizza.vectorstores.qdrant import QdrantVectorstore

from src.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GUIDELINES_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "data", "guidelines_txt")
)

# -----------------------------
# Models
# -----------------------------
EMB_MODEL = "all-MiniLM-L6-v2"
embedder_local = SentenceTransformer(EMB_MODEL)

# -----------------------------
# Chunking
# -----------------------------
def chunk_text(text, chunk_size=800, overlap=150):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

# -----------------------------
# SETUP: Qdrant Vectorstore
# -----------------------------
# you can use location=":memory:" for tests or:
# vectorstore = QdrantVectorstore(host="localhost", port=6333)
vectorstore = QdrantVectorstore(location=":memory:")

# config: embedding dimensions
vector_config = [
    VectorConfig(name="text_embeddings", dimensions=384)
    # 384 is the dimension of "all-MiniLM-L6-v2"
]

# create the "guidelines" collection (if it already exists, recreate it)
try:
    vectorstore.delete_collection("guidelines")
except Exception:
    pass

vectorstore.create_collection(
    collection_name="guidelines",
    vector_config=vector_config
)

# --- EMBEDDING (local) ---
# defines an adapter that takes text and generates embeddings
# using SentenceTransformers and then passes them to Qdrant
class LocalEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        # normalize_embeddings=True as in your Chroma script
        return embedder_local.encode(texts, normalize_embeddings=True).tolist()

local_embedder = LocalEmbedder()

# -----------------------------
# Load + index
# -----------------------------
documents = []
metadatas = []
ids = []

idx = 0

for path in glob.glob(os.path.join(GUIDELINES_DIR, "*.txt")):
    fname = os.path.basename(path)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        continue

    chunks = chunk_text(text)

    for j, chunk in enumerate(chunks):
        doc_id = f"guideline_{idx}"

        documents.append(chunk)
        metadatas.append({
            "source": fname,
            "chunk_id": j,
            "document_type": "guideline"
        })
        ids.append(doc_id)
        idx += 1

# --- GENERATE EMBEDDINGS (local) ---
logger.info(f"Generating embeddings for {len(documents)} chunks...")
embeddings = local_embedder.embed(documents)

# --- ADD TO QDRANT ---
logger.info("Adding documents to Qdrant...")
vectorstore.add(
    collection_name="guidelines",
    documents=documents,
    embeddings=embeddings,
    metadatas=metadatas,
    ids=ids,
    embedding_name="text_embeddings"
)

logger.info("Done.")

logger.info("Guidelines indexed successfully!")
logger.info("Files:", len(set(m["source"] for m in metadatas)))
logger.info("Chunks:", len(ids))
