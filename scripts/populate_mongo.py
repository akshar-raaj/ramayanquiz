"""
This is a batch operation and needed the first time after MongoDB is setup.

We want to retrieve all the rows from PostgreSQL and populate it in MongoDB.
"""

import psycopg2
from pymongo import MongoClient

from database import list_questions
from mongo_database import create_questions_bulk


def populate():
    offset, limit = 0, 20
    while True:
        print(f"Fetching questions from {offset}")
        questions = list_questions(limit=limit, offset=offset)
        if len(questions) == 0:
            break
        create_questions_bulk(questions)
        offset += limit
