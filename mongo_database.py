import datetime
import pymongo
from pymongo import MongoClient

from constants import MONGODB_CONNECTION_STRING

mongo_connection = None


def get_mongo_connection(force=False):
    global mongo_connection
    if mongo_connection is None or force:
        mongo_connection = MongoClient(MONGODB_CONNECTION_STRING)
    return mongo_connection


def retry_with_new_connection(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pymongo.errors.ConnectionFailure:
            print("handling mongo connection exception")
            get_mongo_connection(force=True)
            return func(*args, **kwargs)
    return wrapper


@retry_with_new_connection
def create_question(question: str, kanda: str | None = None, difficulty: str | None = None, tags: list[str] = list(), answers: list[dict] = list()):
    connection = get_mongo_connection()
    db = connection.ramayanquiz
    collection = db.questions
    document = {
        "question": question,
        # kanda, tags etc. might be null. Or they could be populated
        # With this approach, we are not utilising the schemaless character of Mongo.
        # Instead kanda and tags fields would be set on the document with null value, thus still needing storage
        # To use Mongo schemaless nature, we should check if they are not null and then only set them on the document
        # But that makes our application logic unnecessarily nested.
        "kanda": kanda,
        "tags": tags,
        "difficulty": difficulty,
        # MongoDB is schemaless, thus there is no way to set a field/column which can be applied on all documents
        # at insertion. Hence, we have to explicitly create and send it from the application layer
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
        "answers": answers
    }
    # Compare this with database.create_question()
    # Only one query needed in a document database, while two queries are needed for two different tables.
    inserted_record = collection.insert_one(document)
    return inserted_record.inserted_id


@retry_with_new_connection
def create_questions_bulk(questions: list):
    inserted_ids = []
    connection = get_mongo_connection()
    db = connection.ramayanquiz
    collection = db.questions
    documents = []
    for question in questions:
        question_text = question['question']
        kanda = question.get('kanda')
        tags = question.get('tags', [])
        difficulty = question.get('difficulty')
        answers = question['answers']
        document = {
            "question": question_text,
            "kanda": kanda,
            "tags": tags,
            "difficulty": difficulty,
            # Will be stored as ISODate in Mongo
            # Mongo strips the timezone info from the passed date.
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow(),
            "answers": answers
        }
        documents.append(document)
    inserted_ids = collection.insert_many(documents).inserted_ids
    return inserted_ids


@retry_with_new_connection
def get_questions(limit=1, offset=0):
    """
    Compare this with list_questions() for postgres i.e database.list_questions.
    You would notice this function is much simpler compared to list_questions().
    1. No database join needed.
    2. No application grouping of question and answers needed.

    Relational databases have impedance mismatch while document database don't.
    """
    connection = get_mongo_connection()
    # Database
    db = connection.ramayanquiz
    # Collection
    collection = db.questions
    # pymongo can convert from Mongo types to Python native types.
    # Example: From Mongo ISODate to Python datetime
    documents = collection.find().skip(offset).limit(limit)
    return list(documents)
