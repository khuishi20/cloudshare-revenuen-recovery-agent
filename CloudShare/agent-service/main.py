from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import DiagnoseRequest, DiagnoseResponse
from diagnosis import diagnose

app = FastAPI(
    title="Revenue Recovery Agent",
    description="Diagnoses failed-payment root cause and recommends a bounded recovery action.",
    version="0.1.0",
)

# Allow the Spring Boot backend and the local React dev server to call this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this before you actually ship anywhere
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/diagnose", response_model=DiagnoseResponse)
def diagnose_one(req: DiagnoseRequest):
    return diagnose(req)


@app.post("/diagnose-batch", response_model=List[DiagnoseResponse])
def diagnose_batch(reqs: List[DiagnoseRequest]):
    return [diagnose(r) for r in reqs]
