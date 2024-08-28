import csv
from io import StringIO
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import File, UploadFile

from typing import Annotated

from models import Question
from database import create_question, create_questions_bulk

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


@app.post("/questions/bulk")
def post_bulk_questions(file: UploadFile):
    f = file.file
    contents = f.read()
    csv_data = contents.decode('utf-8')
    csv_file = StringIO(csv_data)
    # Read each line of the binary file as string
    reader = csv.DictReader(csv_file)
    questions = []
    for row in reader:
        answers = row['Answers']
        answers = answers.split('\n')
        question = {'question': row['Question'], 'answers': [], 'difficulty': row['Difficulty']}
        for answer in answers:
            if 'correct' in answer:
                answer = answer.removesuffix(' - correct')
                question['answers'].append({'answer': answer, 'is_correct': True})
            else:
                question['answers'].append({'answer': answer, 'is_correct': False})
        questions.append(question)
    create_questions_bulk(questions)
    print(questions)
    return {"status": "OK"}