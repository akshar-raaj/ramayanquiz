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

TABLE_QUESTION_DROP = """
DROP TABLE IF EXISTS questions;
"""

TYPE_DIFFICULTY_CREATE = """
CREATE TYPE difficulty AS ENUM ('easy', 'medium', 'hard')
"""

TYPE_DIFFICULTY_DROP = """
DROP TYPE difficulty
"""

connection = None


def get_database_connection(force=False):
    global connection
    if connection is None or force:
        connection = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
    return connection


def retry_with_new_connection(func):
    def wrapper(*args, **kwargs):
        try:
            # For idle connections, the connection might be closed by the server
            # In such cases, executing the query will raise psycopg2.OperationError.
            # OperationError is handled by psycopg2. But connection.closed is set True then.
            # Running the query again will raise psycopg2.InterfaceError
            # which we are handling here
            return func(*args, **kwargs)
        except psycopg2.InterfaceError as e:
            print("handling interface error")
            get_database_connection(force=True)
            return func(*args, **kwargs)
    return wrapper


@retry_with_new_connection
def _create_tables():
    # Helper function to create the tables.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(TYPE_DIFFICULTY_CREATE)
            cursor.execute(TABLE_QUESTION_CREATE)


@retry_with_new_connection
def _drop_tables():
    # Helper function to drop the tables. Be extremely cautious!
    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(TABLE_QUESTION_DROP)
            cursor.execute(TYPE_DIFFICULTY_DROP) 



@retry_with_new_connection
def create_question(question_text: str, kanda: str | None = None, tags: list[str] | None = None, difficulty: str | None = None):
    inserted_id = None
    connection = get_database_connection()
    # We have created a context.
    # Hence transaction will be committed on successful execution of the block
    # or else it would be rolled back
    # No need to explicitly call connection.commit()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO questions (question, kanda, tags, difficulty) VALUES (%s, %s, %s, %s) RETURNING id",
                (question_text, kanda, tags, difficulty),
            )
            inserted_id = cursor.fetchone()[0]
    return inserted_id


# Write a function to retrieve the questions
@retry_with_new_connection
def get_questions():
    connection = get_database_connection()
    with connection:
        with connection.cursor() as cursor:
            # id is the primary key, hence has an index
            # We are ordering on an indexed field
            cursor.execute("SELECT question, tags, difficulty, kanda FROM questions order by id desc")
            return cursor.fetchall()
    return []
