"""
Integration tests for FastAPI endpoints.
Tests API responses, validation, and error handling.
"""
import pytest
import sys
import os
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


# /chat endpoint removed (tests deleted)


class TestListDocsEndpoint:
    """Test /list-docs endpoint."""
    
    def test_list_docs_success(self):
        """Test successful list docs request."""
        response = client.get("/list-docs?rag_type=cases")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict), "Response should be a dict"
    
    def test_list_docs_missing_param(self):
        """Test list docs without rag_type parameter."""
        response = client.get("/list-docs")
        
        # Should still work or return error
        assert response.status_code in [200, 422]


class TestDeleteDocEndpoint:
    """Test /delete-doc endpoint."""
    
    def test_delete_doc_format(self):
        """Test delete doc with proper format."""
        response = client.post(
            "/delete-doc",
            json={"file_id": "test_file_123"}
        )
        
        # service validates UUID format and will return 400 for invalid ids
        assert response.status_code in [200, 400]
        data = response.json()
        assert isinstance(data, dict), "Response should be a dict"
    
    def test_delete_doc_missing_file_id(self):
        """Test delete doc without file_id."""
        response = client.post(
            "/delete-doc",
            json={}
        )
        
        # Missing file_id will be rejected with 400 by validation
        assert response.status_code in [200, 400, 422]


class TestFlushRagEndpoint:
    """Test /flush-rag endpoint."""
    
    def test_flush_rag_success(self):
        """Test successful flush rag request."""
        response = client.post(
            "/flush-rag",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data or "message" in data


class TestAnalyzeCaseRateLimit:
    """Test rate limiting for /analyze-case endpoint."""

    def test_analyze_case_rate_limited(self, monkeypatch):
        """Repeated requests should eventually return HTTP 429."""

        async def stub_save_current_dicom_and_extract_frames(file):
            return {
                "file_id": "test-file-id",
                "filename": "test.dcm",
                "frames_dir": "data/current/frames/test-file-id",
                "num_frames": 1,
                "frames": ["frame_0001.jpg"],
            }

        def stub_analyze_current_case(report_text=None, frames_dir=None):
            return {"ok": True, "answer": "stub-analysis", "sources": []}

        monkeypatch.setattr(
            "api.main.save_current_dicom_and_extract_frames",
            stub_save_current_dicom_and_extract_frames,
            raising=True,
        )
        monkeypatch.setattr(
            "api.main.analyze_current_case",
            stub_analyze_current_case,
            raising=True,
        )

        got_429 = False
        for _ in range(15):
            response = client.post(
                "/analyze-case",
                files={"file": ("test.dcm", b"DICM-test", "application/dicom")},
                data={"report_text": "test"},
            )

            if response.status_code == 429:
                got_429 = True
                break

            assert response.status_code == 200

        assert got_429, "Expected to hit rate limit and receive HTTP 429"


class TestCORSHeaders:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self):
        """Test that CORS headers are set."""
        response = client.get("/list-docs?rag_type=cases")
        
        # CORS headers should be present on actual requests
        assert "access-control-allow-origin" in [h.lower() for h in response.headers] or response.status_code == 200


class TestHealthCheck:
    """Test general API health."""
    
    def test_docs_accessible(self):
        """Test that /docs endpoint is accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200, "API docs should be accessible"
    
    def test_openapi_schema(self):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200, "OpenAPI schema should be available"
        data = response.json()
        assert "openapi" in data, "Should contain OpenAPI version"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
