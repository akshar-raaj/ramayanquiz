from constants import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

import psycopg2


TABLE_QUESTION_CREATE = """
CREATE TABLE questions (
    id serial PRIMARY KEY,
    question text NOT NULL UNIQUE,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    kanda varchar(50),
    tags varchar(20) ARRAY,
    difficulty difficulty
)
"""

TYPE_DIFFICULTY_CREATE = """
CREATE TYPE difficulty AS ENUM ('easy', 'medium', 'hard')
"""


def _create_difficulty_enum():
    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    cursor = connection.cursor()

    cursor.execute(TYPE_DIFFICULTY_CREATE)

    connection.commit()
    connection.close()


def _create_table_question():
    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
    cursor = connection.cursor()

    cursor.execute(TABLE_QUESTION_CREATE)

    connection.commit()
    connection.close()


def create_tables():
    _create_difficulty_enum()
    _create_table_question()