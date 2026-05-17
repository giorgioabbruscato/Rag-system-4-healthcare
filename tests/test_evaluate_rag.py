"""Tests for RAG evaluation pipeline."""

import json
import pytest
from pathlib import Path
from scripts.evaluate_rag import (
    precision_at_k,
    recall_at_k,
    mrr,
    load_evaluation_queries,
    extract_case_ids_from_hits,
    evaluate_retrieval,
    save_evaluation_results,
)


@pytest.mark.evaluation
class TestMetricFunctions:
    """Test individual metric calculation functions."""

    def test_precision_at_k_all_relevant(self):
        """Precision@5 should be 1.0 when all retrieved docs are relevant."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = {"doc1", "doc2", "doc3", "doc4", "doc5"}
        assert precision_at_k(retrieved, relevant, k=5) == 1.0

    def test_precision_at_k_half_relevant(self):
        """Precision@5 should be 0.6 when 3 out of 5 are relevant."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = {"doc1", "doc2", "doc3"}
        assert precision_at_k(retrieved, relevant, k=5) == 0.6

    def test_precision_at_k_none_relevant(self):
        """Precision@5 should be 0.0 when no retrieved docs are relevant."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = {"doc6", "doc7"}
        assert precision_at_k(retrieved, relevant, k=5) == 0.0

    def test_precision_at_k_zero_k(self):
        """Precision@0 should always be 0.0."""
        retrieved = ["doc1", "doc2"]
        relevant = {"doc1"}
        assert precision_at_k(retrieved, relevant, k=0) == 0.0

    def test_precision_at_k_cutoff(self):
        """Precision@3 should only consider first 3 docs."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = {"doc3", "doc4", "doc5"}  # All relevant but in positions 3,4,5
        # Only doc3 is in top-3, so precision = 1/3 ≈ 0.333
        assert abs(precision_at_k(retrieved, relevant, k=3) - 1/3) < 0.01

    def test_recall_at_k_all_relevant(self):
        """Recall@5 should be 1.0 when all relevant docs are retrieved."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = {"doc1", "doc2", "doc3"}
        assert recall_at_k(retrieved, relevant, k=5) == 1.0

    def test_recall_at_k_partial_relevant(self):
        """Recall@5 should be 0.5 when 1 out of 2 relevant docs is retrieved."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = {"doc1", "doc6"}
        assert recall_at_k(retrieved, relevant, k=5) == 0.5

    def test_recall_at_k_none_relevant(self):
        """Recall@5 should be 0.0 when no relevant docs are retrieved."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = {"doc6", "doc7"}
        assert recall_at_k(retrieved, relevant, k=5) == 0.0

    def test_recall_at_k_empty_relevant(self):
        """Recall@5 should be 0.0 when there are no relevant docs."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = set()
        assert recall_at_k(retrieved, relevant, k=5) == 0.0

    def test_mrr_first_doc_relevant(self):
        """MRR should be 1.0 when first doc is relevant."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = {"doc1"}
        assert mrr(retrieved, relevant) == 1.0

    def test_mrr_second_doc_relevant(self):
        """MRR should be 0.5 when second doc is first relevant."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = {"doc2"}
        assert mrr(retrieved, relevant) == 0.5

    def test_mrr_third_doc_relevant(self):
        """MRR should be 1/3 when third doc is first relevant."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = {"doc3"}
        assert abs(mrr(retrieved, relevant) - 1/3) < 0.01

    def test_mrr_no_relevant(self):
        """MRR should be 0.0 when no relevant doc is found."""
        retrieved = ["doc1", "doc2", "doc3"]
        relevant = {"doc4", "doc5"}
        assert mrr(retrieved, relevant) == 0.0

    def test_mrr_multiple_relevant_uses_first(self):
        """MRR should use reciprocal of first relevant position."""
        retrieved = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        relevant = {"doc2", "doc4"}  # doc2 is at position 2
        assert mrr(retrieved, relevant) == 0.5


@pytest.mark.evaluation
class TestExtractCaseIds:
    """Test extraction of case IDs from vectorstore hits."""

    def test_extract_case_ids_deduplicates_frames(self, mock_vectorstore_hits):
        """Should deduplicate frames belonging to the same case."""
        case_ids = extract_case_ids_from_hits(mock_vectorstore_hits)
        # case_001 appears twice (case_card + frame), should be deduplicated
        assert case_ids == ["case_001", "case_002", "case_003", "case_004"]

    def test_extract_case_ids_empty_hits(self):
        """Should return empty list for empty hits."""
        case_ids = extract_case_ids_from_hits([])
        assert case_ids == []

    def test_extract_case_ids_preserves_order(self):
        """Should preserve order of first appearance."""
        hits = [
            {"metadata": {"case_id": "case_c"}},
            {"metadata": {"case_id": "case_a"}},
            {"metadata": {"case_id": "case_b"}},
        ]
        case_ids = extract_case_ids_from_hits(hits)
        assert case_ids == ["case_c", "case_a", "case_b"]

    def test_extract_case_ids_missing_metadata(self):
        """Should handle hits with missing metadata gracefully."""
        hits = [
            {"metadata": {"case_id": "case_001"}},
            {},  # Missing metadata
            {"metadata": {}},  # Missing case_id
            {"metadata": {"case_id": "case_002"}},
        ]
        case_ids = extract_case_ids_from_hits(hits)
        assert case_ids == ["case_001", "case_002"]


@pytest.mark.evaluation
class TestLoadEvaluationQueries:
    """Test loading evaluation queries from JSON."""

    def test_load_evaluation_queries_default_path(self):
        """Should load queries from default path."""
        queries = load_evaluation_queries()
        assert isinstance(queries, list)
        assert len(queries) > 0
        # Check structure of first query
        assert "query" in queries[0]
        assert "expected_diagnosis_groups" in queries[0]
        assert "relevant_case_ids" in queries[0]

    def test_load_evaluation_queries_custom_path(self, tmp_path):
        """Should load queries from custom path."""
        # Create a temporary queries file
        queries_file = tmp_path / "test_queries.json"
        test_queries = [
            {
                "query": "Test query",
                "expected_diagnosis_groups": ["test"],
                "relevant_case_ids": ["case_001"],
                "expected_keywords": ["test"]
            }
        ]
        with open(queries_file, "w") as f:
            json.dump(test_queries, f)

        queries = load_evaluation_queries(str(queries_file))
        assert len(queries) == 1
        assert queries[0]["query"] == "Test query"

    def test_load_evaluation_queries_missing_file(self, tmp_path):
        """Should raise FileNotFoundError for missing queries file."""
        missing_file = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            load_evaluation_queries(str(missing_file))

    def test_load_evaluation_queries_invalid_json(self, tmp_path):
        """Should raise JSONDecodeError for invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json }")
        with pytest.raises(json.JSONDecodeError):
            load_evaluation_queries(str(invalid_file))


@pytest.mark.evaluation
class TestSaveEvaluationResults:
    """Test saving evaluation results to file."""

    def test_save_evaluation_results_creates_file(self, tmp_path):
        """Should create timestamped JSON file."""
        results = {
            "per_query": [],
            "aggregate": {
                "num_queries": 0,
                "mean_precision_at_k": 0.0,
                "mean_recall_at_k": 0.0,
                "mean_mrr": 0.0,
            },
            "metadata": {
                "k": 5,
                "timestamp": "2024-01-01T00:00:00"
            }
        }
        
        output_file = save_evaluation_results(results, str(tmp_path))
        assert output_file.exists()
        assert "eval_" in output_file.name
        assert output_file.suffix == ".json"

    def test_save_evaluation_results_creates_latest_symlink(self, tmp_path):
        """Should create eval_latest.json for convenience."""
        results = {
            "per_query": [],
            "aggregate": {
                "num_queries": 0,
                "mean_precision_at_k": 0.5,
                "mean_recall_at_k": 0.5,
                "mean_mrr": 0.5,
            },
            "metadata": {}
        }
        
        save_evaluation_results(results, str(tmp_path))
        
        latest_file = tmp_path / "eval_latest.json"
        assert latest_file.exists()
        
        with open(latest_file) as f:
            loaded = json.load(f)
        assert loaded["aggregate"]["mean_precision_at_k"] == 0.5

    def test_save_evaluation_results_valid_json(self, tmp_path):
        """Should save valid JSON that can be reloaded."""
        results = {
            "per_query": [
                {
                    "query": "Test query",
                    "precision_at_k": 0.8,
                    "recall_at_k": 0.6,
                    "mrr": 0.5,
                }
            ],
            "aggregate": {
                "num_queries": 1,
                "mean_precision_at_k": 0.8,
                "mean_recall_at_k": 0.6,
                "mean_mrr": 0.5,
            },
            "metadata": {"k": 5}
        }
        
        output_file = save_evaluation_results(results, str(tmp_path))
        
        with open(output_file) as f:
            loaded = json.load(f)
        assert loaded == results


@pytest.mark.evaluation
@pytest.mark.slow
class TestEvaluateRetrievalIntegration:
    """Integration tests for the full evaluation pipeline.
    
    These tests require a vectorstore and embedder to be initialized,
    so they're marked as slow.
    """

    @pytest.mark.skip(reason="Requires initialized vectorstore")
    def test_evaluate_retrieval_returns_correct_structure(self):
        """Should return dict with per_query, aggregate, and metadata keys."""
        # This test is skipped by default as it requires full setup
        pass

    @pytest.mark.skip(reason="Requires initialized vectorstore")
    def test_evaluate_retrieval_computes_metrics(self):
        """Should compute all required metrics for each query."""
        pass
