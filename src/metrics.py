"""Prometheus metrics for RAG retrieval and DICOM uploads."""

import time
from contextlib import contextmanager
from typing import Generator

from prometheus_client import Counter, Histogram

rag_retrieval_latency = Histogram(
    "rag_retrieval_latency_seconds",
    "Time spent on RAG retrieval",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)
rag_documents_retrieved = Counter(
    "rag_documents_retrieved_total",
    "Total documents retrieved",
    ["collection"],
)
dicom_uploads = Counter(
    "dicom_uploads_total",
    "Total DICOM files uploaded",
)


def record_documents_retrieved(collection: str, count: int) -> None:
    if count > 0:
        rag_documents_retrieved.labels(collection=collection).inc(count)


@contextmanager
def observe_retrieval_latency() -> Generator[None, None, None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        rag_retrieval_latency.observe(time.perf_counter() - start)
