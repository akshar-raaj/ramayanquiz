"""
This module creates services/helpers to interact with MongoDB.

The functions shouldn't make any assumptions about the application layer classes and objects.
It should deal with Mongosh like statements.

Unlike database.py, this module doesn't have any create table or create type statements. That's precisely because
MongoDB is schemaless and we do not need to create a schema in advance.
"""
import datetime
import pymongo
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, BulkWriteError

from constants import MONGODB_CONNECTION_STRING

mongo_connection = None


def get_mongo_connection(force=False):
    global mongo_connection
    if mongo_connection is None or force:
        # MongoClient doesn't raise an exception even if the connection string is invalid.
        # No exception handling can be perfomed here.
        mongo_connection = MongoClient(MONGODB_CONNECTION_STRING, serverSelectionTimeoutMS=5000)
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


def _create_tables():
    """
    This is to keep consistency with database._create_tables.
    Ideally it should be named _create_collections.
    Although, with Mongo we don't need to create a collection before inserting documents.
    However, it comes handy if we want document schema validation, or probably to create a unique
    index on the collection.
    """
    connection = get_mongo_connection()
    db = connection.ramayanquiz
    db.create_collection('questions')
    db.questions.create_index('question', unique=True)


def _drop_tables():
    """
    This is to keep consistency with database._drop_tables.
    Ideally it should be called _drop_collections.
    We want a clean database.
    Hence, all the collections should be removed.
    """
    connection = get_mongo_connection()
    db = connection.ramayanquiz
    db.questions.drop()


@retry_with_new_connection
def create_question(question: str, kanda: str | None = None, difficulty: str | None = None, tags: list[str] | None = None, answers: list[dict] | None = None):
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
        # Commenting them to utilise the Mongo schemaless nature
        # "kanda": kanda,
        # "tags": tags,
        # "difficulty": difficulty,
        # MongoDB is schemaless, thus there is no way to set a field/column which can be applied on all documents
        # at insertion. Hence, we have to explicitly create and send it from the application layer
        "created_at": datetime.datetime.utcnow(),
        "updated_at": datetime.datetime.utcnow(),
        # "answers": answers
    }
    if kanda:
        document["kanda"] = kanda
    if tags:
        document["tags"] = tags
    if difficulty:
        document["difficulty"] = difficulty
    if answers:
        document["answers"] = answers
    # Compare this with database.create_question()
    # Only one query needed in a document database, while two queries are needed for two different tables.
    try:
        inserted_record = collection.insert_one(document)
    except DuplicateKeyError:
        print(f"Unique constraint violation while creating question {question}")
        return None
    return inserted_record.inserted_id


@retry_with_new_connection
def create_questions_bulk(questions: list[dict[str, str | list]]):
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
        answers = question.get('answers', [])
        document = {
            "question": question_text,
            # Will be stored as ISODate in Mongo
            # Mongo strips the timezone info from the passed date.
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow(),
        }
        if kanda:
            document["kanda"] = kanda
        if tags:
            document["tags"] = tags
        if difficulty:
            document["difficulty"] = difficulty
        if answers:
            document["answers"] = answers
        documents.append(document)
    try:
        inserted_ids = collection.insert_many(documents).inserted_ids
    except BulkWriteError:
        print("Error in bulk writing")
        return None
    return inserted_ids


@retry_with_new_connection
def list_questions(limit: int = 20, offset: int = 0, difficulty: str | None = None):
    """
    Compare this with list_questions() for postgres i.e database.list_questions.
    You would notice this function is much simpler compared to list_questions().
    1. No database join needed. Thus database query is simpler.
    2. No application grouping of question and answers needed.
       Thus application layer is potentially simpler during retrieval.

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
    if difficulty is not None:
        documents = collection.find({'difficulty': difficulty}).skip(offset).limit(limit)
    # Be warned that if a document doesn't have some fields, then this result too wouldn't
    # have such fields. Example 'tags' could be missing on a document.
    return list(documents)
