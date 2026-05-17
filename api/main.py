import os
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from prometheus_fastapi_instrumentator import Instrumentator
from src.config import settings
# Load environment variables from .env file
load_dotenv()

from api.services.doc_service import save_current_dicom_and_extract_frames, list_current_files, delete_current_file
from api.services.rag_service import answer_question, analyze_current_case

from scripts.index_Qdrant import reset_collections, get_vectorstore

from src.logging_config import get_logger
logger = get_logger(__name__)

app = FastAPI()
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
      CORSMiddleware,
      allow_origins=settings.allowed_origins,
      allow_credentials=True,
      allow_methods=["GET", "POST", "DELETE"],
      allow_headers=["*"],
  )

Instrumentator().instrument(app).expose(app)

# The legacy `/chat` endpoint and related models removed (deprecated).


@app.post("/upload-doc")
async def upload_doc(
    file: UploadFile = File(...),
):
    """
    POST /upload-doc
    Uploads a DICOM file, extracts frames, and stores the document for further analysis.
    Request: multipart form with a DICOM file.
    Response: ok, plus metadata about the uploaded file and extracted frames.
    """
    try:
        result = await save_current_dicom_and_extract_frames(file)
        return {"ok": True, **result}
    except HTTPException as e:
        logger.warning("Failed to upload file", filename=file.filename, error=e.detail)
        raise e
    except Exception as e:
        logger.exception("An unexpected error occurred during file upload", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")



@app.post("/analyze-case")
@limiter.limit(settings.analyze_case_rate_limit)
async def analyze_case(
    request: Request,
    file: UploadFile = File(...),
    report_text: Optional[str] = Form(None)
):
    """
    POST /analyze-case
    Uploads a DICOM file and optional report text, extracts frames, and runs a multimodal RAG analysis to generate a clinical answer.
    Request: multipart form with a DICOM file and optional report_text.
    Response: ok, metadata about the file and frames, and analysis result.
    """
    try:
        result = await save_current_dicom_and_extract_frames(file)
        analysis = analyze_current_case(report_text=report_text, frames_dir=result.get("frames_dir"))
        return {"ok": True, **result, "analysis": analysis}
    except HTTPException as e:
        logger.warning("Failed to analyze case", filename=file.filename, error=e.detail)
        raise e
    except Exception as e:
        logger.exception("An unexpected error occurred during case analysis", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")



@app.get("/list-docs")
def list_docs(rag_type: str):
    """
    GET /list-docs
    Lists all currently uploaded or indexed documents in the system.
    Query parameter: rag_type (type of documents to list)
    Response: list of documents.
    """
    return list_current_files()


@app.get("/health")
def health_check():
    """
    GET /health
    Returns health status of the API and core dependencies.
    """
    checks = {
        "api": "healthy",
        "vectorstore": "unknown",
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY")),
    }

    try:
        vectorstore = get_vectorstore()
        checks["vectorstore"] = "healthy" if vectorstore else "unhealthy"
    except Exception as e:
        checks["vectorstore"] = "unhealthy"
        logger.warning("Vectorstore health check failed", error=str(e))

    status = "healthy" if all(v != "unhealthy" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}



@app.post("/delete-doc")
def delete_doc(payload: Dict[str, Any]):
    """
    POST /delete-doc
    Deletes a document from the current storage.
    Request body: file_id (identifier of the file to delete)
    Response: result of the deletion operation.
    """
    file_id = payload.get("file_id")
    try:
        return delete_current_file(file_id)
    except HTTPException as e:
        logger.warning("Failed to delete file", file_id=file_id, error=e.detail)
        raise e
    except Exception as e:
        logger.exception("An unexpected error occurred during file deletion", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")



@app.post("/flush-rag")
def flush_rag():
    """
    POST /flush-rag
    Resets the RAG system by clearing and re-initializing all collections (soft reset).
    Request body: empty or any JSON object.
    Response: ok, message or error.
    """
    try:
        reset_collections()
        return {"ok": True, "message": "RAG collections reset."}
    except Exception as e:
        logger.exception("Failed to reset RAG collections", error=str(e))
        return {"ok": False, "error": str(e)}, 500
