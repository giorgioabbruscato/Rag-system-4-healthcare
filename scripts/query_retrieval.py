import os
import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "dataset_built"))
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=CHROMA_DIR)
col = client.get_collection("cases")

print("Ready. Empty query to exit.")

while True:
    q = input("\nQuery: ").strip()
    if not q:
        break

    q_emb = model.encode([q], normalize_embeddings=True).tolist()
    res = col.query(
        query_embeddings=q_emb,
        n_results=5,
        include=["documents", "metadatas", "distances"]
    )

    for i in range(len(res["ids"][0])):
        cid = res["ids"][0][i]
        meta = res["metadatas"][0][i]
        dist = res["distances"][0][i]
        print(f"\n#{i+1} case_id={cid}  label={meta.get('diagnosis_label_raw')}  dist={dist:.4f}")
        print(res["documents"][0][i])
