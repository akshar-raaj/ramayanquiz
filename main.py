import csv
from io import StringIO
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi import UploadFile

from constants import DATA_STORE
from models import Question, DataStore
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


@app.get("/_health")
def read_root():
    return {"status": "OK"}


@app.get("/questions")
def get_questions(limit: int | None = 20, offset: int | None = 0):
    if DATA_STORE == DataStore.POSTGRES.value:
        questions = list_questions(limit=limit, offset=offset)
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


@app.post("/questions")
def post_question(question: Question):
    question_id = create_question(**question.dict())
    create_question_mongo(**question.dict())
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
