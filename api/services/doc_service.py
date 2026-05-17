import re
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from scripts.dicom_to_frames_current import extract_frames
from src.config import settings
from src.logging_config import get_logger
from src.metrics import dicom_uploads

logger = get_logger(__name__)

DATA_DIR = Path("data")
CURRENT_DICOM_DIR = DATA_DIR / "current" / "dicom"
CURRENT_FRAMES_DIR = DATA_DIR / "current" / "frames"

MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024
UUID_PATTERN = re.compile(r"^[a-f0-9\-]{36}$")


def _ensure_dirs():
    CURRENT_DICOM_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_FRAMES_DIR.mkdir(parents=True, exist_ok=True)


def import_all_rawdata_dicoms():
    """
    Copy all .dcm files from data/raw_data (recursively) to data/current/dicom/
    Skip files that already exist with the same name.
    """
    rawdata_root = Path("data/raw_data")
    _ensure_dirs()
    count = 0
    for p in rawdata_root.rglob("*.dcm"):
        dest = CURRENT_DICOM_DIR / p.name
        if not dest.exists():
            shutil.copy2(p, dest)
            count += 1
    return {"imported": count, "from": str(rawdata_root), "to": str(CURRENT_DICOM_DIR)}


async def validate_dicom_upload(file: UploadFile) -> bytes:
    """
    Validates the uploaded file is a valid DICOM file and within size limits.
    """
    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max: {settings.max_upload_size_mb}MB",
        )

    # Verify it's a valid DICOM file (magic bytes)
    if len(content) < 132 or not content[128:132] == b"DICM":
        raise HTTPException(status_code=400, detail="Invalid DICOM file format")

    return content


async def save_current_dicom_and_extract_frames(file: UploadFile):
    """
    1) validate and save the DICOM in data/current/dicom/<id>.dcm
    2) generate frames in data/current/frames/<id>/frame_*.png using your script/function
    """
    _ensure_dirs()

    content = await validate_dicom_upload(file)

    file_id = str(uuid.uuid4())
    dicom_path = CURRENT_DICOM_DIR / f"{file_id}.dcm"

    dicom_path.write_bytes(content)

    # Extract frames from the newly uploaded DICOM
    out_dir = CURRENT_FRAMES_DIR / file_id
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        frames = extract_frames(str(dicom_path), str(out_dir), n_frames=12)
    except Exception as e:
        logger.exception("Frame extraction failed", error=str(e), file_id=file_id)
        # If extraction fails, still return the base paths
        frames = []

    dicom_uploads.inc()

    return {
        "file_id": file_id,
        "dicom_path": str(dicom_path),
        "frames_dir": str(out_dir),
        "frames": frames,
        "note": "Frames extracted via scripts/dicom_to_frames_current.extract_frames",
    }


def list_current_files():
    _ensure_dirs()
    files = []
    for p in CURRENT_DICOM_DIR.glob("*.dcm"):
        files.append({"file_id": p.stem, "name": p.name, "path": str(p)})
    return {"files": files, "count": len(files)}


def delete_current_file(file_id: str = None):
    _ensure_dirs()
    if not file_id or not UUID_PATTERN.match(file_id):
        raise HTTPException(status_code=400, detail="Invalid file_id format")

    dicom_path = CURRENT_DICOM_DIR / f"{file_id}.dcm"
    frames_dir = CURRENT_FRAMES_DIR / file_id

    if dicom_path.exists():
        dicom_path.unlink()

    if frames_dir.exists() and frames_dir.is_dir():
        for child in frames_dir.glob("*"):
            child.unlink()
        frames_dir.rmdir()

    return {"ok": True, "deleted": file_id}
