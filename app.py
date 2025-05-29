from fastapi import FastAPI
from pydantic import BaseModel
from lanchain_helper import get_similar_answer_from_documents
import os
import uvicorn

app = FastAPI()

class QueryRequest(BaseModel):
    question: str

@app.post("/ask")
def ask_question(request: QueryRequest):
    question = request.question
    print(f"🔍 Received question: {question}")
    response, _ = get_similar_answer_from_documents(question)
    return {"question": question, "response": response}

# This block ensures that uvicorn binds to the correct port on Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
