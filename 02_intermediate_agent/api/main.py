from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent import run_agent

app = FastAPI(title="Intermediate Agent API", version="1.0.0")


class AnalyzeRequest(BaseModel):
    text: str
    top_k: int = Field(default=5, ge=1, le=20)


class SpecialistAssessment(BaseModel):
    role: str
    key: str
    assessment: str


class AnalyzeResponse(BaseModel):
    assessments: list[SpecialistAssessment]
    final_summary: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    result = run_agent(request.text, top_k=request.top_k)
    return AnalyzeResponse(
        assessments=[SpecialistAssessment(**a) for a in result["assessments"]],
        final_summary=result["final_summary"],
    )
