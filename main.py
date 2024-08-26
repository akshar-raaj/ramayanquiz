from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import Question
from database import create_question

app = FastAPI()

origins = [
    "http://localhost:8000",
    "http://ramayanquiz.com",
    "https://ramayanquiz.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/_health")
def read_root():
    return {"status": "OK"}


@app.get("/questions")
def get_questions():
    from database import get_questions
    return get_questions()


@app.post("/questions")
def post_question(question: Question):
    question_id = create_question(**question.dict())
    return {"question_id": question_id}