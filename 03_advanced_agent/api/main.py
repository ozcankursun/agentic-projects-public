import csv
import io
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import PyPDF2
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from agent import start_workflow, update_workflow_and_resume

app = FastAPI(title="Advanced Agent API", version="1.0.0")

DATA_DIR = "/app/data"


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def _extract_text_from_bytes(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        reader = PyPDF2.PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".csv":
        text = content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        return "\n".join(", ".join(row) for row in reader)
    else:  # .txt and everything else
        return content.decode("utf-8", errors="replace")


def _extract_text_from_path(filepath: str) -> str:
    with open(filepath, "rb") as f:
        content = f.read()
    return _extract_text_from_bytes(Path(filepath).name, content)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ProcessStorageRequest(BaseModel):
    filenames: list[str]


class ApproveRequest(BaseModel):
    thread_id: str
    updated_soap: str


class WorkflowResponse(BaseModel):
    thread_id: str
    status: str
    soap_draft: str
    extractions: list[dict]


class ApproveResponse(BaseModel):
    status: str
    final_soap_note: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/files")
def list_files():
    data_path = Path(DATA_DIR)
    if not data_path.exists():
        return {"files": []}
    valid_extensions = {".pdf", ".txt", ".csv"}
    files = [
        f.name for f in data_path.iterdir()
        if f.is_file() and f.suffix.lower() in valid_extensions
    ]
    return {"files": sorted(files)}


@app.post("/upload", response_model=WorkflowResponse)
async def upload(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    parts = []
    for file in files:
        content = await file.read()
        text = _extract_text_from_bytes(file.filename or "upload.txt", content)
        parts.append(f"=== {file.filename} ===\n{text}")

    raw_text = "\n\n".join(parts)
    thread_id = str(uuid.uuid4())
    result = start_workflow(thread_id, raw_text)

    return WorkflowResponse(
        thread_id=thread_id,
        status="awaiting_approval",
        soap_draft=result["soap_draft"],
        extractions=result["extractions"],
    )


@app.post("/process-storage", response_model=WorkflowResponse)
def process_storage(request: ProcessStorageRequest):
    if not request.filenames:
        raise HTTPException(status_code=400, detail="No filenames provided.")

    parts = []
    for filename in request.filenames:
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        text = _extract_text_from_path(filepath)
        parts.append(f"=== {filename} ===\n{text}")

    raw_text = "\n\n".join(parts)
    thread_id = str(uuid.uuid4())
    result = start_workflow(thread_id, raw_text)

    return WorkflowResponse(
        thread_id=thread_id,
        status="awaiting_approval",
        soap_draft=result["soap_draft"],
        extractions=result["extractions"],
    )


@app.post("/approve", response_model=ApproveResponse)
def approve(request: ApproveRequest):
    if not request.thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required.")

    result = update_workflow_and_resume(request.thread_id, request.updated_soap)

    return ApproveResponse(
        status="completed",
        final_soap_note=result["final_soap_note"],
    )
