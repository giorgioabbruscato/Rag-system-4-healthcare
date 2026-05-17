"""
Pytest configuration and fixtures.
"""
import json
import os
import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def project_root():
    """Return project root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def data_dir(project_root):
    """Return data directory path."""
    return os.path.join(project_root, "data")


@pytest.fixture(scope="session")
def dataset_dir(data_dir):
    """Return dataset_built directory path."""
    return os.path.join(data_dir, "dataset_built")


@pytest.fixture(scope="session")
def evaluation_dir(data_dir):
    """Return evaluation directory path."""
    return os.path.join(data_dir, "evaluation")


@pytest.fixture
def mock_dicom_metadata():
    """Return mock DICOM metadata for testing."""
    return {
        "case_id": "test123abc",
        "anonymized": True,
        "diagnosis_label_raw": "Normal",
        "diagnosis_label_short": "normal",
        "diagnosis_label_pretty": "Normal",
        "diagnosis_group": "normal",
        "source_path": "Normal/test.dcm",
        "modality": "US",
        "view": "4CH",
        "stage": "Basale",
        "num_frames": 100,
        "fps": 25,
        "effective_duration": 4.0,
        "heart_rate": 70,
        "manufacturer": "Test Manufacturer",
        "model": "Test Model",
        "rows": 480,
        "columns": 640,
        "photometric": "YBR_FULL_422",
        "mean_intensity": 0.45,
        "motion_energy": 0.023,
        "motion_std": 0.012,
        "feature_frames_used": 64
    }


@pytest.fixture
def eval_queries():
    """Load evaluation queries from JSON for testing."""
    queries_path = Path(__file__).parent.parent / "data" / "evaluation" / "eval_queries.json"
    if not queries_path.exists():
        return []
    with open(queries_path) as f:
        return json.load(f)


@pytest.fixture
def sample_eval_query():
    """Return a single sample evaluation query for unit testing."""
    return {
        "query": "Normal echocardiogram findings",
        "expected_diagnosis_groups": ["normal"],
        "relevant_case_ids": ["case_001", "case_002"],
        "expected_keywords": ["normal", "preserved"]
    }


@pytest.fixture
def mock_vectorstore_hits():
    """Return mock vectorstore search hits for testing metric functions."""
    return [
        {
            "metadata": {"case_id": "case_001", "document_type": "case_card"}
        },
        {
            "metadata": {"case_id": "case_001", "document_type": "frame"}
        },
        {
            "metadata": {"case_id": "case_002", "document_type": "case_card"}
        },
        {
            "metadata": {"case_id": "case_003", "document_type": "case_card"}
        },
        {
            "metadata": {"case_id": "case_004", "document_type": "case_card"}
        },
    ]


# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "privacy: marks tests related to data privacy/anonymization"
    )
    config.addinivalue_line(
        "markers", "evaluation: marks tests related to RAG evaluation"
    )
