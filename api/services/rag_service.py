from typing import Any, Dict, Optional
from scripts.index_Qdrant import get_vectorstore, get_embedder

from src.logging_config import get_logger
from src.metrics import observe_retrieval_latency, record_documents_retrieved

logger = get_logger(__name__)

# Import multimodal pipeline
try:
    from scripts.multimodal_rag_openai import run_multimodal_rag
except Exception as e:
    run_multimodal_rag = None
    logger.warning("Multimodal pipeline unavailable", error=str(e))


def answer_question(
    question: str,
    model: str,
    rag_type: str,
    session_id: Optional[str],
    evaluate: bool
) -> Dict[str, Any]:
    """
    Handle the RAG query using the auto-indexed vectorstore.
    
    - rag_type: "cases", "guidelines", "hybrid", "multimodal"
    - model: OpenAI model name (e.g., "gpt-4o")
    - evaluate: if True, compute metrics with ragas (optional)
    """
    
    vectorstore = get_vectorstore()
    embedder = get_embedder()
    
    # Embed query
    query_emb = embedder.encode([question], normalize_embeddings=True).tolist()[0]
    
    sources = []
    retrieved_context = ""
    
    # Retrieval based on rag_type
    if rag_type in ["cases", "hybrid", "multimodal"]:
        try:
            with observe_retrieval_latency():
                hits = vectorstore.search(
                    collection_name="cases",
                    query_vector=query_emb,
                    vector_name="text_embedding",
                    k=5
                )
            record_documents_retrieved("cases", len(hits))
            for hit in hits:
                sources.append({
                    "type": "case",
                    "id": hit.id,
                    "score": 0.0,  # score not available in Chunk objects from datapizza
                    "snippet": hit.text[:200] + "...",
                    "metadata": hit.metadata
                })
                retrieved_context += f"\n[CASE {hit.id}]\n{hit.text}\n"
        except Exception as e:
            logger.exception("Error retrieving cases", error=str(e))

    if rag_type in ["guidelines", "hybrid", "multimodal"]:
        try:
            with observe_retrieval_latency():
                hits = vectorstore.search(
                    collection_name="guidelines",
                    query_vector=query_emb,
                    vector_name="text_embedding",
                    k=4
                )
            record_documents_retrieved("guidelines", len(hits))
            for hit in hits:
                sources.append({
                    "type": "guideline",
                    "id": hit.id,
                    "score": 0.0,  # score not available in Chunk objects from datapizza
                    "snippet": hit.text[:200] + "...",
                    "metadata": hit.metadata
                })
                retrieved_context += f"\n[GUIDELINE {hit.metadata.get('source', '?')}]\n{hit.text}\n"
        except Exception as e:
            logger.exception("Error retrieving guidelines", error=str(e))
    
    # Build answer (you can integrate OpenAI or another LLM here)
    # Simple stub for now
    if rag_type == "multimodal":
        # TODO: call run_multimodal_rag with frames from the current case
        answer = f"[Multimodal RAG stub]\nQuery: {question}\n\nRetrieved {len(sources)} sources.\n\n{retrieved_context[:500]}..."
    else:
        answer = f"[RAG stub - {rag_type}]\nQuery: {question}\n\nRetrieved {len(sources)} sources.\n\n{retrieved_context[:500]}..."
    
    evaluation_obj = None
    if evaluate:
        evaluation_obj = {"message": "Evaluation stub (integrate ragas here)"}
    
    return {
        "answer": answer,
        "sources": sources,
        "session_id": session_id or "session-auto",
        "evaluation": evaluation_obj,
    }


def analyze_current_case(
    report_text: Optional[str],
    frames_dir: Optional[str]
) -> Dict[str, Any]:
    """
    Run multimodal RAG using provided frames directory and a report_text.
    If report_text is None, use a generic clinical analysis instruction.
    Requires OPENAI_API_KEY set for vision model.
    """
    default_report = (
        "Analyze this echocardiography case. Provide probable diagnosis, "
        "differential, confidence, and cite evidence from images and retrieved cases/guidelines."
    )
    text = report_text.strip() if report_text else default_report

    if run_multimodal_rag is None:
        return {
            "ok": False,
            "error": "Multimodal pipeline unavailable. Ensure OpenAI SDK installed and OPENAI_API_KEY set.",
        }

    try:
        output_text = run_multimodal_rag(report_text=text, query_frames_folder=frames_dir)
    except Exception as e:
        logger.exception("Multimodal RAG failed", error=str(e))
        return {"ok": False, "error": f"Multimodal RAG failed: {e}"}

    return {
        "ok": True,
        "answer": output_text,
        "frames_dir": frames_dir,
    }
