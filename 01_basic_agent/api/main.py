from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import run_agent

app = FastAPI(title="Basic Agent API", version="1.0.0")


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    final_summary: str
    history: str


@app.get("/health")
def health():
    import os
    return {
        "status": "ok",
        "has_groq_key": bool(os.getenv("GROQ_API_KEY")),
        "llm_model": os.getenv("LLM_MODEL", "NOT SET"),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    result = run_agent(request.text)
    return AnalyzeResponse(
        final_summary=result["final_summary"],
        history=result["history"],
    )
