from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from fastapi.middleware.cors import CORSMiddleware

from api.services.doc_service import save_current_dicom_and_extract_frames, list_current_files, delete_current_file
from api.services.rag_service import answer_question, analyze_current_case

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str
    model: str
    rag_type: str
    evaluate: bool = False
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None
    evaluation: Optional[Any] = None

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    out = answer_question(
        question=req.question,
        model=req.model,
        rag_type=req.rag_type,
        session_id=req.session_id,
        evaluate=req.evaluate,
    )
    return ChatResponse(**out)

@app.post("/upload-doc")
async def upload_doc(
    file: UploadFile = File(...),
    model: str = Form(...),
    rag_type: str = Form(...),
    test_splitter_chunk: str = Form("default"),
    summarize_type: str = Form("none"),
):
    result = await save_current_dicom_and_extract_frames(file)
    return {"ok": True, **result}


@app.post("/analyze-case")
async def analyze_case(
    file: UploadFile = File(...),
    report_text: Optional[str] = Form(None)
):
    """
    Upload a DICOM, extract frames, and run multimodal RAG to generate a supportive answer.
    No chat required: returns a single analysis output.
    """
    result = await save_current_dicom_and_extract_frames(file)
    analysis = analyze_current_case(report_text=report_text, frames_dir=result.get("frames_dir"))
    return {"ok": True, **result, "analysis": analysis}

@app.get("/list-docs")
def list_docs(rag_type: str):
    # minimo: lista file caricati in current (o doc indicizzati)
    return list_current_files()

@app.post("/delete-doc")
def delete_doc(payload: Dict[str, Any]):
    file_id = payload.get("file_id")
    return delete_current_file(file_id)
