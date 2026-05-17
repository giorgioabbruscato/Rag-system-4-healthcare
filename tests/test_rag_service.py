import pytest

import api.services.rag_service as rs


class DummyHit:
    def __init__(self, id, text, metadata=None):
        self.id = id
        self.text = text
        self.metadata = metadata or {}


class DummyVectorstore:
    def __init__(self, hits_by_collection=None):
        self.hits_by_collection = hits_by_collection or {}

    def search(self, collection_name, query_vector, vector_name, k):
        return self.hits_by_collection.get(collection_name, [])


class DummyEmbedder:
    def encode(self, texts, normalize_embeddings=True):
        # return an object with tolist() -> list-of-lists to match production embedder
        class DummyArray:
            def __init__(self, data):
                self._data = data

            def tolist(self):
                return self._data

        return DummyArray([[0.0] for _ in texts])


def test_answer_question_empty_query(monkeypatch):
    dummy_vs = DummyVectorstore(hits_by_collection={"cases": []})
    monkeypatch.setattr(rs, "get_vectorstore", lambda: dummy_vs)
    monkeypatch.setattr(rs, "get_embedder", lambda: DummyEmbedder())

    out = rs.answer_question(question="", model="gpt-4o", rag_type="cases", session_id=None, evaluate=False)
    assert "Retrieved 0 sources" in out["answer"]
    assert out["sources"] == []


def test_answer_question_rag_types(monkeypatch):
    # Prepare hits for cases and guidelines
    case_hit = DummyHit(id="case1", text="case text", metadata={})
    guide_hit = DummyHit(id="g1", text="guide text", metadata={"source": "guideline1"})

    dummy_vs = DummyVectorstore(hits_by_collection={
        "cases": [case_hit],
        "guidelines": [guide_hit]
    })

    monkeypatch.setattr(rs, "get_vectorstore", lambda: dummy_vs)
    monkeypatch.setattr(rs, "get_embedder", lambda: DummyEmbedder())

    out = rs.answer_question(question="Q", model="m", rag_type="hybrid", session_id="s1", evaluate=False)
    # should include both types
    types = {s["type"] for s in out["sources"]}
    assert "case" in types and "guideline" in types


def test_analyze_current_case_without_multimodal(monkeypatch):
    monkeypatch.setattr(rs, "run_multimodal_rag", None)
    out = rs.analyze_current_case(report_text="test", frames_dir="/tmp/frames")
    assert out["ok"] is False
    assert "Multimodal pipeline unavailable" in out["error"]
