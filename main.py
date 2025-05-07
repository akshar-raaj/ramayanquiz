import csv
import json
import asyncio
import logging
from io import StringIO
from typing import Annotated

from psycopg2.errors import UniqueViolation

from fastapi import FastAPI, Depends, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from fastapi import UploadFile, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from websockets.exceptions import ConnectionClosedError
from starlette.websockets import WebSocketState

from constants import DATA_STORE, ADMIN_PASSWORD
from models import Question, DataStore, Difficulty, StatusResponse, QuestionResponse, TokenResponse
from database import create_question, create_questions_bulk, list_questions, most_recent_question_id, recent_questions_count, fetch_question, fetch_question_answers
from database import health as db_health
from mongo_database import health as mongo_health
from mongo_database import create_question as create_question_mongo, create_questions_bulk as create_questions_bulk_mongo, list_questions as list_questions_mongo
from queueing import publish
from queueing import health as rabbitmq_health
from redis_store import health as redis_health
from rate_limit import RateLimiter
from redis_store import get_redis_connection


logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s')

logger.info("Bootstrapping")

app = FastAPI()

# Server should respond with 'access-control-allow-origin' header for only these origins.
# As the server wouldn't respond with this header for other origins,
# hence browser will block those origins from making the request
origins = [
    "http://localhost:8000",
    "http://ramayanquiz.com",
    "https://ramayanquiz.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# OAuth2 scheme, password flow, using a Bearer token
# tokenUrl declares the endpoint that clients should use to get the token
# It doesn't automatically create the endpoint/path function though.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.get("/_health")
def _health(request: Request) -> StatusResponse:
    client_ip = request.headers.get("x-forwarded-for")
    is_rate_limited = False
    if client_ip is not None:
        rate_limiter = RateLimiter()
        is_rate_limited = not rate_limiter.check(identifier=client_ip)
    if is_rate_limited is True:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    logger.info("Health check")
    try:
        db_health()
    except Exception:
        # Severity error keeps the log shorter. It still signifies that an error/exception has ocurred
        # without emitting the traceback
        logger.error("PostgreSQL is down!")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="PostgreSQL is down")
    try:
        mongo_health()
    except Exception:
        logger.error("MongoDB is down")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="MongoDB is down")
    try:
        rabbitmq_health()
    except Exception:
        logger.error("RabbitMQ is down")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="RabbitMQ is down")
    try:
        redis_health()
    except Exception:
        logger.error("Redis is down")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Redis is down")
    # TODO: Add a health check for Elasticsearch
    logger.info("Health check passed")
    return StatusResponse(status="Up")


# This is the login endpoint
# Client must send `username` and `password` in the request as form data, no JSON here
# The OAuth2 spec enforces that the field names should be `username` and `password`
@app.post("/token")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    """
    This API endpoint expects an application/x-www-form-urlencoded request instead of application/json

    curl -v -X POST --data "username=akshar" --data "password=boom" http://localhost:8000/token
    """
    # Currently we only want to deal with an admin user
    if form_data.password == ADMIN_PASSWORD and form_data.username == "admin":
        return {"access_token": ADMIN_PASSWORD, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@app.get("/questions")
def get_questions(request: Request, limit: int | None = 20, offset: int | None = 0, difficulty: Difficulty | None = None) -> list[QuestionResponse]:
    """
    This API warrants caching for the following reasons:
    - It's frequently used.
    - Data doesn't change often. Thus, no issue around stale data.
    - It has expensive operation, i.e database calls which are I/O bound. Hence, these calls should be avoided

    It can be scoped with limit, offset and difficulty. As it doesn't differ based on user, hence no user scope needed.
    """
    client_ip = request.headers.get("x-forwarded-for")
    is_rate_limited = False
    if client_ip is not None:
        rate_limiter = RateLimiter()
        is_rate_limited = not rate_limiter.check(identifier=client_ip)
    if is_rate_limited is True:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")

    cache_key = f"{offset}-{limit}"
    if difficulty is not None:
        cache_key = f"{cache_key}-{difficulty.value}"
    if DATA_STORE == DataStore.POSTGRES.value:
        logger.info("Listing questions from Postgres Store")
        # Attempt reading from the cache.
        # If not in cache, then make database call and then set in cache as well.
        # Cache-aside strategy
        redis_connection = get_redis_connection()
        logger.info(f"Cache key: {cache_key}")
        questions = redis_connection.get(cache_key)
        # Found in cache
        if questions is not None:
            logger.info("Found question in cache")
            questions = json.loads(questions)
        # Not found in cache
        else:
            logger.info("Did not find in cache. Getting from the database")
            difficulty = difficulty.value if difficulty is not None else None
            questions = list_questions(limit=limit, offset=offset, difficulty=difficulty)
            redis_connection.set(cache_key, json.dumps(questions))
            redis_connection.expire(cache_key, 60)
    elif DATA_STORE == DataStore.MONGO.value:
        logger.info("Listing questions from Mongo Store")
        questions = list_questions_mongo(limit=limit, offset=offset)
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


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
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
    """
    An example curl request:
    curl -H "Authorization: Bearer abc\!123" -H "Content-Type: application/json" -X POST --data '{"question": "Who was Sita?", "answers": [{"answer": "God"}]}' http://localhost:8000/questions
    """
    logger.info("Creating question")
    try:
        question_id = create_question(**question.dict())
    except UniqueViolation:
        # This demonstrates how some exceptions don't need to be treated as an exception
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question already exists")
    except Exception as e:
        # There ca be different type of exceptions like UniqueViolation etc.
        # The Pydantic model can be written in a way to avoid Null violations, type violations etc.
        # But still, if the underlying create_question() changes, it can raise any exception.
        # The API should always fail gracefully. Hence, log it and return a proper error
        logger.exception("Exception while creating question %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error ocrurred")
    if question_id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An error ocurred")
    # TODO: The data is already captured till this point
    # Asynchronously insert it into Mongo, either using Airflow scheduler or put it on the Rabbitmq queue
    logger.info("Created question %s", question_id)
    logger.info("Inserting question %s into Mongo", question_id)
    create_question_mongo(**question.dict())
    logger.info("Publishing question %s to queue", question_id)
    publish('post_process', 'post_process', args=[question_id], queue_name='process-question')
    question_dict = fetch_question(question_id)
    answers = fetch_question_answers(question_id=question_id)
    question_dict['answers'] = answers
    return question_dict


@app.post("/questions/bulk")
def post_bulk_questions(token: Annotated[str, Depends(get_current_user)], file: UploadFile):
    """
    curl -H "Authorization: Bearer abc\!123" -F file=@"questions.csv" http://localhost:8000/questions/bulk
    """
    # Validate file type, ensure it's csv
    # Read file in a memory efficient way
    # Validate the columns of the csv
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
