from typing import Dict, Any, Optional

def answer_question(question: str, model: str, rag_type: str, session_id: Optional[str], evaluate: bool) -> Dict[str, Any]:
    """
    Qui devi SOLO fare da colla:
    - se rag_type == "cases": retrieval su Chroma cases + call LLM
    - se rag_type == "guidelines": retrieval su guidelines + call LLM
    - se rag_type == "hybrid": entrambi
    - se hai immagini del caso corrente: includi frames in input
    """

    # --- ESEMPIO STUB ---
    # In pratica qui chiamerai:
    # - query_retrieval per ottenere topk chunks + metadati (sources)
    # - multimodal_rag_openai per costruire prompt e chiamare il modello (vision + text)

    answer = f"(stub) {rag_type} -> {question}"
    sources = [{"source": "chroma", "id": "xxx", "score": 0.12, "snippet": "..."}]

    evaluation_obj = None
    if evaluate:
        evaluation_obj = {"message": "Valutazione stub (collega ragas qui)"}

    # session_id: se la gestisci lato backend (memoria), qui puoi crearla o mantenerla
    return {
        "answer": answer,
        "sources": sources,
        "session_id": session_id or "session-1",
        "evaluation": evaluation_obj,
    }
