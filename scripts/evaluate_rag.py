"""RAG Evaluation Pipeline - Measures retrieval and generation quality.

This module provides evaluation metrics for the RAG system, focusing on
measuring how well the vector retrieval component returns clinically relevant
cases for a given query.

Metrics:
- Precision@K: Fraction of top-K retrieved docs that are relevant
- Recall@K: Fraction of all relevant docs that appear in top-K
- MRR (Mean Reciprocal Rank): Average reciprocal position of first relevant doc
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def precision_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    """Calculate Precision@K: fraction of top-K retrieved docs that are relevant.

    Args:
        retrieved_ids: List of retrieved document IDs (ordered by relevance)
        relevant_ids: Set of document IDs that are relevant to the query
        k: Cutoff position (e.g., 5 for Precision@5)

    Returns:
        Float between 0 and 1. Returns 0 if k=0.
    """
    if k <= 0:
        return 0.0
    retrieved_k = retrieved_ids[:k]
    relevant_count = len(set(retrieved_k) & relevant_ids)
    return relevant_count / k


def recall_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    """Calculate Recall@K: fraction of all relevant docs found in top-K.

    Args:
        retrieved_ids: List of retrieved document IDs (ordered by relevance)
        relevant_ids: Set of document IDs that are relevant to the query
        k: Cutoff position (e.g., 5 for Recall@5)

    Returns:
        Float between 0 and 1. Returns 0 if no relevant docs exist.
    """
    if len(relevant_ids) == 0:
        return 0.0
    retrieved_k = set(retrieved_ids[:k])
    relevant_count = len(retrieved_k & relevant_ids)
    return relevant_count / len(relevant_ids)


def mrr(retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
    """Calculate Mean Reciprocal Rank: reciprocal position of first relevant doc.

    Args:
        retrieved_ids: List of retrieved document IDs (ordered by relevance)
        relevant_ids: Set of document IDs that are relevant to the query

    Returns:
        Float between 0 and 1. Returns 0.0 if no relevant doc is found.
        Returns 1.0 if first doc is relevant, 0.5 if second doc is relevant, etc.
    """
    for i, doc_id in enumerate(retrieved_ids, 1):
        if doc_id in relevant_ids:
            return 1.0 / i
    return 0.0


def load_evaluation_queries(
    queries_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load evaluation queries from JSON file.

    Args:
        queries_path: Path to eval_queries.json. Defaults to
            data/evaluation/eval_queries.json

    Returns:
        List of query dicts with keys: query, expected_diagnosis_groups,
        relevant_case_ids, expected_keywords

    Raises:
        FileNotFoundError: If queries file does not exist
        json.JSONDecodeError: If queries file is not valid JSON
    """
    if queries_path is None:
        queries_path = Path(__file__).parent.parent / "data" / "evaluation" / "eval_queries.json"
    else:
        queries_path = Path(queries_path)

    if not queries_path.exists():
        raise FileNotFoundError(
            f"Evaluation queries file not found: {queries_path}. "
            "Run 'python scripts/build_dataset.py' first."
        )

    with open(queries_path) as f:
        queries = json.load(f)

    logger.info(f"Loaded {len(queries)} evaluation queries from {queries_path}")
    return queries


def extract_case_ids_from_hits(hits: List[Dict[str, Any]]) -> List[str]:
    """Extract case IDs from vectorstore search hits.

    Args:
        hits: List of hit objects from vectorstore.search(). Each hit should
            have a metadata dict with "case_id" field (for case_card documents)
            or "original_id" field.

    Returns:
        Ordered list of unique case IDs, deduplicating frame documents that
        belong to the same case.
    """
    case_ids = []
    seen = set()
    for hit in hits:
        metadata = hit.get("metadata", {}) if isinstance(hit, dict) else hit.metadata
        case_id = metadata.get("case_id") or metadata.get("original_id")
        if case_id and case_id not in seen:
            case_ids.append(case_id)
            seen.add(case_id)
    return case_ids


def evaluate_retrieval(
    queries: List[Dict[str, Any]],
    vectorstore: Any,
    embedder: Any,
    k: int = 5,
    collection_name: str = "cases",
) -> Dict[str, Any]:
    """Run evaluation on all queries and return aggregate metrics.

    Args:
        queries: List of query dicts from load_evaluation_queries()
        vectorstore: Qdrant vectorstore instance (must have .search() method)
        embedder: Sentence transformer embedder (must have .encode() method)
        k: Number of top documents to retrieve for evaluation
        collection_name: Name of the vectorstore collection to search

    Returns:
        Dict with keys:
        - per_query: List of results for each query
        - aggregate: Aggregated metrics across all queries
        - metadata: Info about the evaluation run
    """
    logger.info(f"Starting evaluation on {len(queries)} queries (k={k})")

    results = []
    for query_idx, q in enumerate(queries, 1):
        query_text = q["query"]
        relevant_ids = set(q.get("relevant_case_ids", []))

        logger.debug(f"  [{query_idx}/{len(queries)}] {query_text[:60]}...")

        # Encode query and retrieve similar cases
        try:
            query_emb = embedder.encode(
                [query_text], normalize_embeddings=True
            ).tolist()[0]
        except Exception as e:
            logger.error(f"Failed to encode query: {e}")
            continue

        try:
            hits = vectorstore.search(
                collection_name=collection_name,
                query_vector=query_emb,
                vector_name="text_embedding",
                k=k,
            )
        except Exception as e:
            logger.error(f"Failed to search vectorstore: {e}")
            continue

        # Extract unique case IDs from hits (dedup frames)
        retrieved_ids = extract_case_ids_from_hits(hits)

        # Compute metrics
        p_at_k = precision_at_k(retrieved_ids, relevant_ids, k)
        r_at_k = recall_at_k(retrieved_ids, relevant_ids, k)
        mrr_score = mrr(retrieved_ids, relevant_ids)

        results.append({
            "query": query_text,
            "expected_diagnosis_groups": q.get("expected_diagnosis_groups", []),
            "expected_keywords": q.get("expected_keywords", []),
            "num_relevant": len(relevant_ids),
            "num_retrieved": len(retrieved_ids),
            "precision_at_k": p_at_k,
            "recall_at_k": r_at_k,
            "mrr": mrr_score,
            "retrieved_case_ids": retrieved_ids,
        })

    # Aggregate metrics
    if results:
        def avg(key):
            return sum(r[key] for r in results) / len(results)

        aggregate = {
            "num_queries": len(results),
            "mean_precision_at_k": avg("precision_at_k"),
            "mean_recall_at_k": avg("recall_at_k"),
            "mean_mrr": avg("mrr"),
        }
    else:
        aggregate = {
            "num_queries": 0,
            "mean_precision_at_k": 0.0,
            "mean_recall_at_k": 0.0,
            "mean_mrr": 0.0,
        }

    logger.info(f"Evaluation complete. Mean Precision@{k}: {aggregate['mean_precision_at_k']:.3f}")
    logger.info(f"Mean Recall@{k}: {aggregate['mean_recall_at_k']:.3f}")
    logger.info(f"Mean MRR: {aggregate['mean_mrr']:.3f}")

    return {
        "per_query": results,
        "aggregate": aggregate,
        "metadata": {
            "k": k,
            "collection_name": collection_name,
            "timestamp": datetime.now().isoformat(),
            "embedding_model": getattr(embedder, "model_name", "unknown"),
        },
    }


def save_evaluation_results(
    results: Dict[str, Any],
    output_dir: Optional[str] = None,
) -> Path:
    """Save evaluation results to JSON file with timestamp.

    Args:
        results: Dict returned from evaluate_retrieval()
        output_dir: Output directory for results. Defaults to data/evaluations/

    Returns:
        Path to saved results file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "evaluations"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"eval_{timestamp}.json"

    with open(filename, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Evaluation results saved to {filename}")

    # Also save as 'latest.json' for convenience
    latest_file = output_dir / "eval_latest.json"
    with open(latest_file, "w") as f:
        json.dump(results, f, indent=2)

    return filename


def main():
    """Main entry point for evaluation pipeline.

    Usage:
        python scripts/evaluate_rag.py
    """
    # Import here to avoid hard dependency when script is imported as module
    try:
        from scripts.index_Qdrant import get_vectorstore
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        logger.error(
            f"Missing dependency: {e}. "
            "Install with: pip install -r requirements.txt"
        )
        return

    # Load queries
    queries = load_evaluation_queries()

    # Initialize vectorstore and embedder
    logger.info("Initializing vectorstore and embedder...")
    vectorstore = get_vectorstore()
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    # Run evaluation
    results = evaluate_retrieval(
        queries=queries,
        vectorstore=vectorstore,
        embedder=embedder,
        k=5,
    )

    # Save results
    save_evaluation_results(results)

    # Print summary
    print("\n" + "=" * 60)
    print("RAG EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Queries evaluated: {results['aggregate']['num_queries']}")
    print(f"Precision@5:      {results['aggregate']['mean_precision_at_k']:.3f}")
    print(f"Recall@5:         {results['aggregate']['mean_recall_at_k']:.3f}")
    print(f"MRR:              {results['aggregate']['mean_mrr']:.3f}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
