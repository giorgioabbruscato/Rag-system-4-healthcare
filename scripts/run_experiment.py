"""Run MLflow-tracked RAG evaluation experiments."""

from __future__ import annotations

import argparse
from pathlib import Path

import mlflow

from scripts.evaluate_rag import (
    evaluate_retrieval,
    load_evaluation_queries,
    save_evaluation_results,
)
from scripts.index_Qdrant import get_embedder, get_vectorstore
from src.config import settings
from src.logging_config import get_logger, setup_logging


def run_experiment(
    run_name: str = "baseline",
    tracking_uri: str = "file:./mlruns",
    experiment_name: str = "rag-healthcare",
    k: int | None = None,
    collection_name: str = "cases",
) -> Path:
    """Run evaluation and log params/metrics/artifacts to MLflow."""
    setup_logging(settings.log_level)
    logger = get_logger(__name__)

    k = k or settings.topk_cases

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=run_name):
        # Params
        mlflow.log_param("embedding_model", settings.embedding_model)
        mlflow.log_param("embedding_dim", settings.embedding_dim)
        mlflow.log_param("chunk_size", settings.chunk_size)
        mlflow.log_param("chunk_overlap", settings.chunk_overlap)
        mlflow.log_param("topk_cases", settings.topk_cases)
        mlflow.log_param("topk_guidelines", settings.topk_guidelines)
        mlflow.log_param("vector_name", settings.vector_name)
        mlflow.log_param("collection_name", collection_name)
        mlflow.log_param("k", k)

        logger.info("Loading evaluation queries")
        queries = load_evaluation_queries()

        logger.info("Initializing vectorstore and embedder")
        vectorstore = get_vectorstore()
        embedder = get_embedder()

        logger.info("Running evaluation", k=k, collection=collection_name)
        eval_results = evaluate_retrieval(
            queries=queries,
            vectorstore=vectorstore,
            embedder=embedder,
            k=k,
            collection_name=collection_name,
        )

        # Metrics
        aggregate = eval_results.get("aggregate", {})
        mlflow.log_metric(
            "mean_precision_at_k", aggregate.get("mean_precision_at_k", 0.0)
        )
        mlflow.log_metric("mean_recall_at_k", aggregate.get("mean_recall_at_k", 0.0))
        mlflow.log_metric("mean_mrr", aggregate.get("mean_mrr", 0.0))
        mlflow.log_metric("num_queries", aggregate.get("num_queries", 0))

        # Artifacts
        results_path = save_evaluation_results(eval_results)
        latest_path = Path("data/evaluations/eval_latest.json")
        if latest_path.exists():
            mlflow.log_artifact(str(latest_path))
        mlflow.log_artifact(str(results_path))

        logger.info(
            "MLflow run completed",
            run_name=run_name,
            run_id=mlflow.active_run().info.run_id,
        )

    return results_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MLflow-tracked RAG evaluation")
    parser.add_argument("--run-name", default="baseline", help="MLflow run name")
    parser.add_argument(
        "--tracking-uri",
        default="file:./mlruns",
        help="MLflow tracking URI (default: file:./mlruns)",
    )
    parser.add_argument(
        "--experiment-name",
        default="rag-healthcare",
        help="MLflow experiment name",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Top-k for evaluation (default: settings.topk_cases)",
    )
    parser.add_argument(
        "--collection-name",
        default="cases",
        help="Vectorstore collection to evaluate",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    run_experiment(
        run_name=args.run_name,
        tracking_uri=args.tracking_uri,
        experiment_name=args.experiment_name,
        k=args.k,
        collection_name=args.collection_name,
    )


if __name__ == "__main__":
    main()
