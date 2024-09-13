import csv
from io import StringIO
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from fastapi import UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from constants import DATA_STORE, ADMIN_PASSWORD
from models import Question, DataStore, Difficulty
from database import create_question, create_questions_bulk, list_questions
from mongo_database import create_question as create_question_mongo, create_questions_bulk as create_questions_bulk_mongo, get_questions as get_questions_mongo

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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/_health")
def read_root():
    return {"status": "OK"}


@app.post("/token")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # Currently we only want to deal with an admin user
    if form_data.password == ADMIN_PASSWORD and form_data.username == "admin":
        return {"access_token": ADMIN_PASSWORD, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/questions")
def get_questions(limit: int | None = 20, offset: int | None = 0, difficulty: Difficulty | None = None):
    if DATA_STORE == DataStore.POSTGRES.value:
        difficulty = difficulty.value if difficulty is not None else None
        questions = list_questions(limit=limit, offset=offset, difficulty=difficulty)
    elif DATA_STORE == DataStore.MONGO.value:
        questions = get_questions_mongo(limit=limit, offset=offset)
        updated_questions = []
        for question in questions:
            updated_question = question.copy()
            updated_question['id'] = str(updated_question['_id'])
            del updated_question['_id']
            updated_questions.append(updated_question)
        questions = updated_questions
    else:
        raise Exception("Invalid data store")
    return questions


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    if token == ADMIN_PASSWORD:
        return "admin"
    else:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.post("/questions")
def post_question(user: Annotated[str, Depends(get_current_user)], question: Question):
    question_id = create_question(**question.dict())
    create_question_mongo(**question.dict())
    return {"question_id": question_id}


@app.post("/questions/bulk")
def post_bulk_questions(token: Annotated[str, Depends(get_current_user)], file: UploadFile):
    f = file.file
    contents = f.read()
    csv_data = contents.decode('utf-8')
    csv_file = StringIO(csv_data)
    # Read each line of the binary file as string
    reader = csv.DictReader(csv_file)
    questions = []
    for row in reader:
        answers = row['Answers']
        tags = row['Tags']
        answers = answers.split('\n')
        tags = tags.split(',')
        question = {'question': row['Question'], 'answers': [], 'difficulty': row['Difficulty'], 'kanda': row['Kanda'], 'tags': []}
        for answer in answers:
            if 'correct' in answer:
                answer = answer.removesuffix(' - correct')
                question['answers'].append({'answer': answer, 'is_correct': True})
            else:
                question['answers'].append({'answer': answer, 'is_correct': False})
        for tag in tags:
            tag = tag.strip()
            if tag:
                question['tags'].append(tag.strip())
        questions.append(question)
    create_questions_bulk(questions)
    create_questions_bulk_mongo(questions)
    print(questions)
    return {"status": "OK"}
