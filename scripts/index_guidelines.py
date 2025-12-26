import os
import glob
import chromadb
from sentence_transformers import SentenceTransformer

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GUIDELINES_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "data", "guidelines_txt")
)

CHROMA_DIR = os.path.abspath(
    os.path.join(BASE_DIR, "..", "data", "dataset_built", "chroma_db")
)

# -----------------------------
# Models
# -----------------------------
EMB_MODEL = "all-MiniLM-L6-v2"
embedder = SentenceTransformer(EMB_MODEL)

# -----------------------------
# Chunking (semplice e sicuro)
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
# Chroma setup
# -----------------------------
client = chromadb.PersistentClient(path=CHROMA_DIR)

# ricrea la collection (ok per MVP)
try:
    client.delete_collection("guidelines")
except Exception:
    pass

collection = client.create_collection(name="guidelines")

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
        documents.append(chunk)
        metadatas.append({
            "source": fname,
            "chunk_id": j,
            "document_type": "guideline"
        })
        ids.append(f"guideline_{idx}")
        idx += 1

# embeddings
embeddings = embedder.encode(
    documents,
    normalize_embeddings=True
).tolist()

collection.add(
    ids=ids,
    documents=documents,
    metadatas=metadatas,
    embeddings=embeddings
)

print("Guidelines indexed successfully!")
print("Files:", len(set(m["source"] for m in metadatas)))
print("Chunks:", len(ids))
print("Chroma path:", CHROMA_DIR)
