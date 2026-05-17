import asyncio
import uuid
import pytest
from types import SimpleNamespace

import api.services.doc_service as ds
from fastapi import HTTPException


class MockUploadFile:
    def __init__(self, content: bytes, filename: str = "test.dcm"):
        self._content = content
        self.filename = filename

    async def read(self):
        return self._content


@pytest.mark.asyncio
async def test_validate_dicom_upload_valid(tmp_path, monkeypatch):
    # Prepare small valid DICOM-like bytes (magic at 128..131)
    content = b"\x00" * 128 + b"DICM" + b"PAYLOAD"
    f = MockUploadFile(content)

    # call
    out = await ds.validate_dicom_upload(f)
    assert out.startswith(b"\x00")
    assert out[128:132] == b"DICM"


@pytest.mark.asyncio
async def test_validate_dicom_upload_too_large(monkeypatch):
    monkeypatch.setattr(ds, "MAX_UPLOAD_BYTES", 10)
    content = b"\x00" * 128 + b"DICM" + b"PAYLOAD"
    f = MockUploadFile(content)

    with pytest.raises(HTTPException) as exc:
        await ds.validate_dicom_upload(f)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_validate_dicom_upload_not_dicom():
    # Content too short / no magic bytes
    content = b"not_a_dicom"
    f = MockUploadFile(content)

    with pytest.raises(HTTPException) as exc:
        await ds.validate_dicom_upload(f)
    assert exc.value.status_code == 400


def test_list_current_files_empty(tmp_path, monkeypatch):
    # Redirect directories
    monkeypatch.setattr(ds, "CURRENT_DICOM_DIR", tmp_path / "dicom")
    monkeypatch.setattr(ds, "CURRENT_FRAMES_DIR", tmp_path / "frames")

    out = ds.list_current_files()
    assert out["count"] == 0


def test_delete_current_file_invalid_uuid():
    with pytest.raises(HTTPException):
        ds.delete_current_file("not-a-uuid")


def test_delete_current_file_nonexistent(tmp_path, monkeypatch):
    # Use a valid-looking uuid but file doesn't exist
    monkeypatch.setattr(ds, "CURRENT_DICOM_DIR", tmp_path / "dicom")
    monkeypatch.setattr(ds, "CURRENT_FRAMES_DIR", tmp_path / "frames")
    file_id = str(uuid.uuid4())

    res = ds.delete_current_file(file_id)
    assert res["ok"] is True
    assert res["deleted"] == file_id
