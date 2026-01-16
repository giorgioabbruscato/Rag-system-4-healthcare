from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from fastapi.middleware.cors import CORSMiddleware

from api.services.doc_service import save_current_dicom_and_extract_frames, list_current_files, delete_current_file
from api.services.rag_service import answer_question

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust in prod. ok in local enviroment
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
    # nel tuo caso: "il caso nuovo è sempre un DICOM"
    result = await save_current_dicom_and_extract_frames(file)
    return {"ok": True, **result}

@app.get("/list-docs")
def list_docs(rag_type: str):
    # minimo: lista file caricati in current (o doc indicizzati)
    return list_current_files()

@app.post("/delete-doc")
def delete_doc(payload: Dict[str, Any]):
    file_id = payload.get("file_id")
    return delete_current_file(file_id)

@app.post("/flush-rag")
def flush_rag(payload: Dict[str, Any]):
    # minimo: svuota la cartella current/frames o azzera memoria sessioni
    # (qui puoi implementare soft reset)
    return {"ok": True, "message": "Reset stub (implementa pulizia current + memoria sessioni)"}
