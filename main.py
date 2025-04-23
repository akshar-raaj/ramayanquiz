import csv
import asyncio
import logging
from io import StringIO
from typing import Annotated

from psycopg2.errors import UniqueViolation

from fastapi import FastAPI, Depends, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from fastapi import UploadFile, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from websockets.exceptions import ConnectionClosedError
from starlette.websockets import WebSocketState

from constants import DATA_STORE, ADMIN_PASSWORD
from models import Question, DataStore, Difficulty, StatusResponse, QuestionResponse
from database import create_question, create_questions_bulk, list_questions, most_recent_question_id, recent_questions_count, fetch_question, fetch_question_answers
from database import health as db_health
from mongo_database import create_question as create_question_mongo, create_questions_bulk as create_questions_bulk_mongo, list_questions as get_questions_mongo
from queueing import publish


logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)

logger.info("Bootstrapping")

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

# OAuth2 scheme, password flow, using a Bearer token
# tokenUrl declares the endpoint that clients should use to get the token
# It doesn't automatically create the endpoint/path function though.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/_health")
def _health() -> StatusResponse:
    logger.info("Health check")
    try:
        db_health()
    except Exception:
        # Severity error keeps the log shorter. It still signifies that an error/exception has ocurred
        # without emitting the traceback
        logger.error("Database is down!")
        return StatusResponse(status="Database down")
    logger.info("Health check passed")
    return StatusResponse(status="Up")


# This is the login endpoint
# Client must send `username` and `password` in the request as form data, no JSON here
# The OAuth2 spec enforces that the field names should be `username` and `password`
@app.post("/token")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    # Currently we only want to deal with an admin user
    if form_data.password == ADMIN_PASSWORD and form_data.username == "admin":
        return {"access_token": ADMIN_PASSWORD, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@app.get("/questions")
def get_questions(limit: int | None = 20, offset: int | None = 0, difficulty: Difficulty | None = None) -> list[QuestionResponse]:
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
    """
    FastAPI will check the request `Authorization` header and see
    if it has a Bearer plus some token.
    This would happen because oauth2_schema has been declared as a dependency in this
    path function.
    """
    if token == ADMIN_PASSWORD:
        return "admin"
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@app.post("/questions", status_code=status.HTTP_201_CREATED)
def post_question(user: Annotated[str, Depends(get_current_user)], question: Question) -> QuestionResponse:
    try:
        question_id = create_question(**question.dict())
    except UniqueViolation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question already exists")
    except Exception:
        # There ca be different type of exceptions like UniqueViolation etc.
        # The Pydantic model can be written in a way to avoid Null violations, type violations etc.
        # But still, if the underlying create_question() changes, it can raise any exception.
        # The API should always fail gracefully. Hence, log it and return a proper error
        # TODO: Log this exception
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error ocrurred")
    if question_id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error ocurred")
    # TODO: The data is already captured till this point
    # Asynchronously insert it into Mongo, either using Airflow scheduler or put it on the Rabbitmq queue
    create_question_mongo(**question.dict())
    publish('post_process', 'post_process', args=[question_id], queue_name='process-question')
    question_dict = fetch_question(question_id)
    answers = fetch_question_answers(question_id=question_id)
    question_dict['answers'] = answers
    return question_dict


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
    inserted_ids, skipped_rows = create_questions_bulk(questions)
    # TODO: Send an email to admin notifying about inserted_ids and skipped_rows
    mongo_inserted_ids, mongo_skipped_rows = create_questions_bulk_mongo(questions)
    for inserted_id in inserted_ids:
        publish('post_process', 'post_process', args=[inserted_id], queue_name='process-question')
    return {"status": "OK"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    recent_question_id = most_recent_question_id()
    print(f"Most recent question id {recent_question_id}")
    while True:
        if websocket.client_state != WebSocketState.CONNECTED:
            print("Websocket connection closed")
            break
        print("Checking recent questions")
        recent_questions = recent_questions_count(recent_question_id)
        if recent_questions > 0:
            print(f"{recent_questions} new questions found")
            try:
                await websocket.send_text(f"{recent_questions} new questions added!")
            # This would probably raise starlette.websockets.WebSocketDisconnect
            except ConnectionClosedError:
                print("Websocket connection closed")
                break
            recent_question_id = most_recent_question_id()
        else:
            print("No recent questions found")
            pass
        await asyncio.sleep(5)
