import os
import uuid
from pathlib import Path
from fastapi import UploadFile

DATA_DIR = Path("data")
CURRENT_DICOM_DIR = DATA_DIR / "current" / "dicom"
CURRENT_FRAMES_DIR = DATA_DIR / "current" / "frames"

def _ensure_dirs():
    CURRENT_DICOM_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_FRAMES_DIR.mkdir(parents=True, exist_ok=True)

async def save_current_dicom_and_extract_frames(file: UploadFile):
    """
    1) salva il DICOM in data/current/dicom/<id>.dcm
    2) genera frame in data/current/frames/<id>/frame_*.png usando il tuo script/func
    """
    _ensure_dirs()
    file_id = str(uuid.uuid4())
    dicom_path = CURRENT_DICOM_DIR / f"{file_id}.dcm"

    content = await file.read()
    dicom_path.write_bytes(content)

    # --- QUI colleghi il tuo pezzo dicom_to_frames_current ---
    # Opzione A (consigliata): trasformi script in funzione importabile in src/
    # from src.dicom_to_frames import dicom_to_frames
    # out_dir = CURRENT_FRAMES_DIR / file_id
    # out_dir.mkdir(parents=True, exist_ok=True)
    # dicom_to_frames(str(dicom_path), str(out_dir))

    # Opzione B (rapida): esegui lo script come subprocess (meno elegante)
    # import subprocess
    # out_dir = CURRENT_FRAMES_DIR / file_id
    # out_dir.mkdir(parents=True, exist_ok=True)
    # subprocess.check_call(["python", "script/dicom_to_frames_current/main.py", "--in", str(dicom_path), "--out", str(out_dir)])

    out_dir = CURRENT_FRAMES_DIR / file_id
    out_dir.mkdir(parents=True, exist_ok=True)

    return {
        "file_id": file_id,
        "dicom_path": str(dicom_path),
        "frames_dir": str(out_dir),
        "note": "Frames extraction: collega qui dicom_to_frames_current"
    }

def list_current_files():
    _ensure_dirs()
    files = []
    for p in CURRENT_DICOM_DIR.glob("*.dcm"):
        files.append({"file_id": p.stem, "name": p.name, "path": str(p)})
    return files

def delete_current_file(file_id: str):
    _ensure_dirs()
    dicom_path = CURRENT_DICOM_DIR / f"{file_id}.dcm"
    frames_dir = CURRENT_FRAMES_DIR / file_id

    if dicom_path.exists():
        dicom_path.unlink()

    if frames_dir.exists() and frames_dir.is_dir():
        for child in frames_dir.glob("*"):
            child.unlink()
        frames_dir.rmdir()

    return {"ok": True, "deleted": file_id}
