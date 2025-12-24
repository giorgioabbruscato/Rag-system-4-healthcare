import os, json
import chromadb
from sentence_transformers import SentenceTransformer


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "dataset_built"))
JSONL_PATH = os.path.join(DATA_DIR, "documents.jsonl")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")

print("JSONL_PATH:", JSONL_PATH)
print("CHROMA_DIR:", CHROMA_DIR)

model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=CHROMA_DIR)

# clean build: create collection every time (MVP)
try:
    client.delete_collection("cases")
except Exception:
    pass

col = client.create_collection("cases")

docs, metas, ids = [], [], []

with open(JSONL_PATH, "r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        if obj["metadata"].get("document_type") != "case_card":
            continue
        docs.append(obj["content"])
        metas.append(obj["metadata"])
        ids.append(obj["metadata"]["case_id"])

emb = model.encode(docs, normalize_embeddings=True).tolist()

col.add(ids=ids, documents=docs, metadatas=metas, embeddings=emb)

print("Indexed case_cards:", len(ids))
