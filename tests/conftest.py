"""
Pytest configuration and fixtures.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path
from io import BytesIO
import pydicom
from pydicom.dataset import FileDataset, Dataset
from datetime import datetime


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


@pytest.fixture
def mock_dicom_file():
    """
    Generate a minimal valid DICOM file for testing.
    Returns a BytesIO object containing a valid DICOM file with:
    - Magic bytes (DICM at position 128)
    - Minimal required tags (NumberOfFrames, SamplesPerPixel, PhotometricInterpretation)
    - Single grayscale frame with pixel data
    """
    # Create file meta information
    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7.4'  # US Video Storage
    file_meta.MediaStorageSOPInstanceUID = '1.2.3.4.5.6.7.8.9'
    file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

    # Create the FileDataset instance
    ds = FileDataset(
        "test_dicom_file",
        dataset={},
        file_meta=file_meta,
        preamble=b"\0" * 128
    )

    # Set required DICOM attributes for a valid US image
    ds.PatientName = "Test^Patient"
    ds.PatientID = "123456"
    ds.StudyDate = datetime.now().strftime("%Y%m%d")
    ds.ContentDate = datetime.now().strftime("%Y%m%d")
    ds.StudyTime = datetime.now().strftime("%H%M%S")
    ds.ContentTime = datetime.now().strftime("%H%M%S")
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.Modality = "US"
    ds.SeriesDescription = "Test US"
    ds.SeriesInstanceUID = "1.2.3.4.5"
    ds.StudyInstanceUID = "1.2.3.4"
    ds.SOPInstanceUID = "1.2.3.4.5.6.7.8.9"
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.7.4'

    # Add image-specific attributes
    ds.NumberOfFrames = 1
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.Rows = 480
    ds.Columns = 640
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0  # 0 for unsigned, 1 for signed

    # Create minimal pixel data (grayscale image)
    import numpy as np
    pixel_array = np.zeros((480, 640), dtype=np.uint8)
    pixel_array[100:380, 150:550] = 128  # Add some content in the middle
    ds.PixelData = pixel_array.tobytes()

    # Save to BytesIO
    output = BytesIO()
    ds.save_as(output, write_like_original=False)
    output.seek(0)
    return output


@pytest.fixture
def tmp_data_dir(tmp_path):
    """
    Create a temporary data directory for integration tests.
    This prevents tests from polluting the production data directory.
    """
    current_dir = tmp_path / "current"
    current_dir.mkdir()
    (current_dir / "dicom").mkdir()
    (current_dir / "frames").mkdir()
    return tmp_path


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
