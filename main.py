from fastapi import FastAPI
from pydantic import BaseModel
import time

from app.llm import ask_gemini

app = FastAPI(title="LLM Black Box")

class QuestionRequest(BaseModel):
    question: str

@app.post("/ask")
def ask(request: QuestionRequest):

    # Accepts a user question, sends it to Gemini LLM, and returns the answer along with latency.
    
    start_time = time.time()
    answer = ask_gemini(request.question)
    latency = time.time() - start_time

    return {
        "question": request.question,
        "answer": answer,
        "latency_seconds": round(latency, 3)
    }
