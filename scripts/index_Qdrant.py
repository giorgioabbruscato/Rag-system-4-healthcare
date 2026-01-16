import os, json
from datapizza.clients.openai import OpenAIClient
from datapizza.core.vectorstore import VectorConfig
from datapizza.embedders.openai import OpenAIEmbedder
from datapizza.modules.splitters import NodeSplitter
from datapizza.pipeline import IngestionPipeline
from datapizza.vectorstores.qdrant import QdrantVectorstore
from datapizza.modules.parsers.docling import DoclingParser
from sentence_transformers import SentenceTransformer
# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data", "dataset_built")
JSONL_PATH = os.path.join(DATA_DIR, "documents.jsonl")

print("JSONL_PATH:", JSONL_PATH)

#instance vector store
vectorstore = QdrantVectorstore(location=":memory:")
vector_config = [
    VectorConfig(name="text_embedding", dimensions=1536)
]

vectorstore.create_collection(
    "cases",
    vector_config=vector_config
)

# -----------------------------
# Models
# -----------------------------
EMB_MODEL = "all-MiniLM-L6-v2"
embedder_local = SentenceTransformer(EMB_MODEL)

# definisce un “adapter” che prende il testo e genera embeddings
# usando SentenceTransformers e poi li passa a Qdrant
class LocalEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        # normalize_embeddings=True
        return embedder_local.encode(texts, normalize_embeddings=True).tolist()

local_embedder = LocalEmbedder()
# --- INGEST PIPELINE ---
pipeline = IngestionPipeline(
    modules=[
        DoclingParser(),
        NodeSplitter(max_char=1000),
        local_embedder
    ],
    vector_store=vectorstore,
    collection_name="cases"
)

# --- LOAD DOCUMENTS ---
docs = []
with open(JSONL_PATH, "r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        if obj["metadata"].get("document_type") != "case_card":
            continue
        docs.append(
            {
                "id": obj["metadata"]["case_id"],
                "text": obj["content"],
                "metadata": obj["metadata"],
            }
        )

# --- RUN INGESTION ---
pipeline.run(docs)

print(f"Indexed case_cards: {len(docs)}")
