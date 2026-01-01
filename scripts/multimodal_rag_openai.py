"""
multimodal_rag_openai.py

True multimodal RAG for cardiology (text + images + video sampled as frames):
- Input: report text + optional current exam frames folder (sampled frames)
- Retrieval: similar cases (Chroma "cases") + guidelines (Chroma "guidelines", optional)
- Reasoning: GPT-4o (vision + text) using retrieved context + images
- Output: suggested diagnosis + differential + evidence + missing info + sources

Assumptions:
- Chroma DB at: data/dataset_built/chroma_db
- cases collection exists
- guidelines collection exists (optional)
- frames stored at: data/dataset_built/images/<case_id>/frame_*.png
- embeddings: all-MiniLM-L6-v2 (SentenceTransformers)

Requirements:
pip install openai python-dotenv chromadb sentence-transformers pillow numpy

Env:
OPENAI_API_KEY in your environment or .env
"""

import os
import base64
from typing import List, Dict, Any, Optional, Tuple

import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# ----------------------------
# Config
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "dataset_built"))
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")

EMB_MODEL = "all-MiniLM-L6-v2"
embedder = SentenceTransformer(EMB_MODEL)

TOPK_CASES = 5
TOPK_GUIDES = 4

FRAMES_PER_SIMILAR_CASE = 3
MAX_QUERY_FRAMES = 12
MAX_SIMILAR_FRAMES_TOTAL = 12

MODEL_VISION = "gpt-4o"

client = OpenAI()

# ----------------------------
# Helpers
# ----------------------------
def image_to_data_url(path: str) -> str:
    """Encode local image as data URL for OpenAI image input."""
    with open(path, "rb") as f:
        b = f.read()
    b64 = base64.b64encode(b).decode("utf-8")
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{b64}"

def uniform_sample(items: List[str], n: int) -> List[str]:
    if n <= 0:
        return []
    if len(items) <= n:
        return items
    import numpy as np
    idxs = np.linspace(0, len(items) - 1, n, dtype=int)
    return [items[i] for i in idxs]

def list_frames_in_folder(folder: Optional[str]) -> List[str]:
    if not folder or not os.path.isdir(folder):
        return []
    exts = (".png", ".jpg", ".jpeg")
    return sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(exts)
    )

def pick_frames_for_case(case_id: str, n: int) -> List[str]:
    case_dir = os.path.join(DATA_DIR, "images", case_id)
    frames = list_frames_in_folder(case_dir)
    return uniform_sample(frames, n)

def retrieve_by_text(collection, query_text: str, k: int) -> Dict[str, Any]:
    q_emb = embedder.encode([query_text], normalize_embeddings=True).tolist()
    return collection.query(
        query_embeddings=q_emb,
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )

def knn_vote_labels(
    case_metas: List[Dict[str, Any]],
    case_dists: List[float],
    topn: int = 3
) -> List[Tuple[str, float]]:
    scores: Dict[str, float] = {}
    for meta, dist in zip(case_metas, case_dists):
        lab = meta.get("diagnosis_label_raw", "unknown")
        w = 1.0 / (1.0 + float(dist))
        scores[lab] = scores.get(lab, 0.0) + w
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:topn]

def get_collection_safe(chroma: chromadb.PersistentClient, name: str):
    try:
        return chroma.get_collection(name)
    except Exception:
        return None

# ----------------------------
# Prompting
# ----------------------------
SYSTEM_PROMPT = """You are a cardiology clinical decision support assistant.

Goal:
- Suggest a PROBABLE DIAGNOSIS (not definitive) and a DIFFERENTIAL (2 alternatives)
based ONLY on:
1) the provided clinical report text,
2) the provided visual evidence (sampled frames),
3) retrieved similar cases,
4) retrieved guideline chunks (if provided).

Rules:
- Do NOT invent measurements, findings, or patient details.
- If evidence is insufficient, state it explicitly and list what is missing.
- Provide confidence: low / medium / high, with a short justification.
- Separate evidence from text vs evidence from images.
- For each key claim, cite either a CASE (case_id) or a GUIDELINE (source+chunk).
- Always include a Sources section:
  - list case_id(s) used
  - list guideline sources/chunks if present

Output format:
1) Suggested diagnosis (confidence)
2) Differential (2 alternatives) + why
3) Evidence (bullets)
   - From report/retrieved context
   - From images/frames
4) Missing info / recommended next checks
5) Sources
"""

def build_user_payload(
    report_text: str,
    knn_candidates: List[Tuple[str, float]],
    cases_res: Dict[str, Any],
    guides_res: Optional[Dict[str, Any]],
) -> str:
    diag_lines = "\n".join([f"- {lab}: score={sc:.3f}" for lab, sc in knn_candidates])

    case_ids = cases_res["ids"][0]
    case_metas = cases_res["metadatas"][0]
    case_docs = cases_res["documents"][0]
    case_dists = cases_res["distances"][0]

    cases_block = ""
    for i, cid in enumerate(case_ids):
        meta = case_metas[i]
        cases_block += (
            f"\n[CASE {cid} | label={meta.get('diagnosis_label_raw', '?')} | dist={case_dists[i]:.4f}]\n"
            f"{case_docs[i]}\n"
        )

    if guides_res is None:
        guides_block = "(no guidelines retrieved)"
    else:
        guides_block = ""
        g_ids = guides_res["ids"][0]
        g_docs = guides_res["documents"][0]
        g_metas = guides_res["metadatas"][0]
        g_dists = guides_res["distances"][0]

        for i in range(len(g_ids)):
            meta = g_metas[i]
            src = meta.get("source", "unknown")
            # support both chunk_id and chunk
            chunk = meta.get("chunk_id", meta.get("chunk", "?"))
            guides_block += (
                f"\n[GUIDELINE {src} chunk={chunk} dist={g_dists[i]:.4f}]\n"
                f"{g_docs[i]}\n"
            )

    return f"""CLINICAL REPORT:
{report_text}

KNN DIAGNOSIS CANDIDATES (from similar retrieved cases):
{diag_lines}

RETRIEVED SIMILAR CASES:
{cases_block}

RETRIEVED GUIDELINES:
{guides_block}
"""

# ----------------------------
# Main pipeline
# ----------------------------
def run_multimodal_rag(
    report_text: str,
    query_frames_folder: Optional[str] = None,
    query_frame_paths: Optional[List[str]] = None,
) -> str:
    chroma = chromadb.PersistentClient(path=CHROMA_DIR)
    cases_col = chroma.get_collection("cases")
    guides_col = get_collection_safe(chroma, "guidelines")

    # 1) Retrieve similar cases from report text
    cases_res = retrieve_by_text(cases_col, report_text, TOPK_CASES)

    # 2) Retrieve guidelines (optional)
    guides_res = None
    if guides_col is not None:
        guides_res = retrieve_by_text(guides_col, report_text, TOPK_GUIDES)

    # 3) kNN vote over retrieved labels
    knn_candidates = knn_vote_labels(
        cases_res["metadatas"][0],
        cases_res["distances"][0],
        topn=3
    )

    # 4) Current exam frames (query) - user-provided
    if query_frame_paths is None:
        query_frame_paths = list_frames_in_folder(query_frames_folder)
    query_frame_paths = uniform_sample(query_frame_paths, MAX_QUERY_FRAMES)

    # 5) Supporting frames from similar cases
    case_ids = cases_res["ids"][0]
    similar_frames: List[str] = []
    for cid in case_ids:
        similar_frames.extend(pick_frames_for_case(cid, FRAMES_PER_SIMILAR_CASE))
    similar_frames = uniform_sample(similar_frames, MAX_SIMILAR_FRAMES_TOTAL)

    # 6) Build user text context
    user_text = build_user_payload(report_text, knn_candidates, cases_res, guides_res)

    # 7) Build multimodal content: text + images
    content: List[Dict[str, Any]] = [{"type": "input_text", "text": user_text}]

    # Add current exam frames first
    for p in query_frame_paths:
        content.append({"type": "input_image", "image_url": image_to_data_url(p)})

    # Add similar-case frames
    for p in similar_frames:
        content.append({"type": "input_image", "image_url": image_to_data_url(p)})

    # 8) Call OpenAI
    resp = client.responses.create(
        model=MODEL_VISION,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        max_output_tokens=900,
    )
    return resp.output_text

# ----------------------------
# CLI
# ----------------------------
if __name__ == "__main__":
    print("Paste the clinical report (finish with an empty line):")
    lines = []
    while True:
        line = input()
        if not line.strip():
            break
        lines.append(line)
    report = "\n".join(lines).strip()
    if not report:
        raise SystemExit("No report text provided.")

    frames_folder = input("Optional: folder containing CURRENT exam frames (press Enter to skip): ").strip()
    frames_folder = frames_folder if frames_folder else None

    output = run_multimodal_rag(report_text=report, query_frames_folder=frames_folder)
    print("\n--- MODEL OUTPUT ---\n")
    print(output)
