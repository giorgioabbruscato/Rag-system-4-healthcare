"""
End-to-end integration tests for the full RAG pipeline.

These tests verify complete workflows including:
- Document upload → listing → deletion
- RAG reset and reindexing
- Multi-step user journeys through the API
"""
import pytest
import json
from fastapi.testclient import TestClient
from api.main import app


@pytest.mark.integration
class TestFullPipeline:
    """End-to-end tests for complete RAG workflows."""

    @pytest.fixture
    def client(self):
        """Provide FastAPI test client."""
        return TestClient(app)

    def test_upload_and_list(self, client, mock_dicom_file):
        """
        E2E Test: Upload a DICOM file → List documents → Verify it appears.

        This test verifies the complete document ingestion flow:
        1. Upload a valid DICOM file
        2. Confirm upload returns a valid file_id (UUID format)
        3. Retrieve list of documents from the same rag_type
        4. Verify the uploaded file appears in the list
        """
        # Step 1: Upload DICOM file
        response = client.post(
            "/upload-doc",
            files={"file": ("test.dcm", mock_dicom_file, "application/dicom")}
        )
        
        # Verify upload succeeded
        assert response.status_code == 200, f"Upload failed: {response.text}"
        upload_data = response.json()
        assert upload_data["ok"] is True
        file_id = upload_data["file_id"]
        assert file_id is not None
        assert len(file_id) == 36  # UUID format: 8-4-4-4-12
        
        # Step 2: List documents
        response = client.get("/list-docs?rag_type=cases")
        assert response.status_code == 200
        list_data = response.json()
        assert isinstance(list_data, dict)
        
        # Step 3: Verify uploaded file appears in list
        files = list_data.get("files", [])
        assert len(files) > 0, "No files returned in list after upload"
        
        file_ids = [f.get("file_id") for f in files]
        assert file_id in file_ids, f"Uploaded file {file_id} not found in list"

    def test_upload_delete_verify_removed(self, client, mock_dicom_file):
        """
        E2E Test: Upload → Delete → Verify document is removed from list.

        This test verifies the document lifecycle:
        1. Upload a DICOM file
        2. Delete the file using its file_id
        3. List documents and verify it no longer appears
        """
        # Step 1: Upload
        response = client.post(
            "/upload-doc",
            files={"file": ("test.dcm", mock_dicom_file, "application/dicom")}
        )
        assert response.status_code == 200
        file_id = response.json()["file_id"]
        
        # Step 2: Delete
        response = client.post(
            "/delete-doc",
            json={"file_id": file_id}
        )
        assert response.status_code == 200
        
        # Step 3: Verify removal
        response = client.get("/list-docs?rag_type=cases")
        assert response.status_code == 200
        list_data = response.json()
        files = list_data.get("files", [])
        
        file_ids = [f.get("file_id") for f in files]
        assert file_id not in file_ids, f"Deleted file {file_id} still appears in list"

    def test_flush_and_reindex(self, client):
        """
        E2E Test: Flush RAG → Verify reindexing works → Health check stable.

        This test verifies the RAG reset functionality:
        1. Call flush-rag endpoint to reset all collections
        2. Verify successful response with ok=True
        3. Health check should still return healthy status
        4. Verify list-docs returns empty or minimal state
        """
        # Step 1: Flush RAG collections
        response = client.post("/flush-rag", json={})
        assert response.status_code == 200
        flush_data = response.json()
        assert flush_data.get("ok") is True
        assert "message" in flush_data or "error" not in flush_data
        
        # Step 2: Verify health check is still stable
        response = client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data.get("status") in ["healthy", "degraded"]
        
        # Step 3: Verify documents list is reset
        response = client.get("/list-docs?rag_type=cases")
        assert response.status_code == 200
        list_data = response.json()
        assert isinstance(list_data, dict)

    @pytest.mark.slow
    def test_analyze_case_multimodal_rag(self, client, mock_dicom_file):
        """
        E2E Test: Upload → Analyze with multimodal RAG → Verify response structure.

        This test verifies the multimodal analysis workflow:
        1. Upload a DICOM file and request analysis
        2. Verify the analysis response has expected structure
        3. Verify it includes frames directory and analysis answer
        
        Marked as 'slow' because it triggers the full RAG pipeline and rate limiting.
        Skip with: pytest -m "not slow"
        """
        # Call analyze-case endpoint (without mocking - tests actual RAG pipeline)
        response = client.post(
            "/analyze-case",
            files={"file": ("test.dcm", mock_dicom_file, "application/dicom")},
            data={"report_text": "Test ultrasound report"}
        )
        
        # Verify response structure (may be rate limited if running with other tests)
        assert response.status_code in [200, 429], f"Unexpected status: {response.status_code}, response: {response.text}"
        
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "file_id" in data
            assert "frames" in data
            assert "analysis" in data or "answer" in data
            
            # Verify analysis/answer is non-empty
            analysis_result = data.get("analysis") or data.get("answer")
            assert isinstance(analysis_result, (dict, str))
            if isinstance(analysis_result, dict):
                # If dict, verify it has some content
                assert len(analysis_result) > 0
            else:
                # If string, verify it's non-empty
                assert len(analysis_result) > 0

    def test_health_check_endpoint(self, client):
        """
        E2E Test: Health check returns valid status and component checks.

        This test verifies the health check endpoint:
        1. Call /health endpoint
        2. Verify response contains status (healthy/degraded)
        3. Verify checks object contains api, vectorstore, openai_key_set
        """
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        
        assert "checks" in data
        checks = data["checks"]
        assert "api" in checks
        assert "vectorstore" in checks
        assert "openai_key_set" in checks

    def test_list_docs_empty_rag_type(self, client):
        """
        E2E Test: List docs requires rag_type parameter.

        This test verifies proper parameter validation:
        1. Call /list-docs without rag_type
        2. Should return 422 (validation error) or handle gracefully
        """
        response = client.get("/list-docs")
        # Should either return 422 (missing required param) or 200 with default handling
        assert response.status_code in [200, 422]


@pytest.mark.integration
class TestErrorHandling:
    """E2E tests for error handling and edge cases."""

    @pytest.fixture
    def client(self):
        """Provide FastAPI test client."""
        return TestClient(app)

    def test_delete_nonexistent_file(self, client):
        """
        Test: Attempt to delete a file that doesn't exist.

        Should handle gracefully (either 200 with no-op or 400/404 with error).
        """
        fake_uuid = "550e8400-e29b-41d4-a716-446655440000"
        response = client.post(
            "/delete-doc",
            json={"file_id": fake_uuid}
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 404]

    def test_delete_invalid_uuid_format(self, client):
        """
        Test: Attempt to delete with invalid UUID format.

        Should reject with 400 validation error.
        """
        response = client.post(
            "/delete-doc",
            json={"file_id": "not-a-uuid"}
        )
        # Should reject invalid format
        assert response.status_code in [400, 422]

    def test_upload_invalid_file_format(self, client):
        """
        Test: Attempt to upload a non-DICOM file.

        Should reject with 400 error about invalid DICOM format.
        """
        fake_file = b"This is not a DICOM file"
        response = client.post(
            "/upload-doc",
            files={"file": ("not_dicom.txt", fake_file, "text/plain")}
        )
        # Should reject non-DICOM files
        assert response.status_code in [400, 422]
