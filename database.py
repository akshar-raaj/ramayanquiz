"""
This module creates services/helpers to interact with PostgreSQL database.

The functions shouldn't make any assumptions about the application layer
classes and objects. It should deal with raw SQL statements.
However, seeing the module allows user to understand the application data model.

Had we been using ORM, it would deal with ORM statements.
"""

from typing import List, Tuple, Any

from constants import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from models import Difficulty, Kanda

import psycopg2
from psycopg2.errors import UniqueViolation, OperationalError


# User defined type
TYPE_DIFFICULTY_CREATE = """
CREATE TYPE difficulty AS ENUM ('easy', 'medium', 'hard')
"""

# User defined type
TYPE_KANDA_CREATE = """
CREATE TYPE kanda AS ENUM ('Bala Kanda', 'Ayodhya Kanda', 'Aranya Kanda', 'Kishkinda Kanda', 'Sundara Kanda', 'Lanka Kanda', 'Uttara Kanda')
"""

# Data type 'serial' is equivalent to defining an 'integer' with a 'sequence'.
# 'Primary Key' is equivalent to defining a 'NOT NULL' and 'UNIQUE' constraint.
# However, there can be only one Primary Key.
# 'timestamp' type doesn't store tzinfo in the database.
TABLE_QUESTION_CREATE = """
CREATE TABLE questions (
    id serial PRIMARY KEY,
    question text NOT NULL UNIQUE,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    kanda kanda,
    tags varchar(20) ARRAY,
    difficulty difficulty
)
"""

# We have deliberately not used UNIQUE on answer column.
# Different questions can have same answers.
# However we can keep a unique on question_id and answer.
TABLE_ANSWER_CREATE = """
CREATE TABLE answers (
    id serial PRIMARY KEY,
    question_id integer NOT NULL REFERENCES questions(id),
    answer text NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    modified_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_correct boolean DEFAULT false
)
"""


TABLE_QUESTION_DROP = """
DROP TABLE IF EXISTS questions;
"""

TABLE_ANSWER_DROP = """
DROP TABLE IF EXISTS answers;
"""

TYPE_DIFFICULTY_DROP = """
DROP TYPE difficulty
"""

TYPE_KANDA_DROP = """
DROP TYPE kanda
"""

# Global variables pollute the namespace and there is a possibility to overwrite them.
# Hence, we should avoid using global variables.
# Refactor the code to use a class with singleton
connection = None


def get_database_connection(force: bool = False):
    """
    Creates a database connection if needed and keeps it cached on a global variable.
    We don't want to create a database connection, each time this function gets invoked.

    We possibly want to reuse the connection throughout the lifecycle of the application
    unless the server closes the connection, in which case we will use `force` and recreate the connection.

    `connection` maintains a session with the database.
    The database operations like query execution and result fetching are controlled by a cursor.
    """
    global connection
    if connection is None or force:
        try:
            connection = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                application_name='core',
                connect_timeout=5
            )
        except OperationalError as e:
            # TODO: Add logger.error
            # Though this logger is not required, clients should perform their own logging.
            print(f"Exception while creating PostgreSQL connection {e}")
            raise e
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
        except psycopg2.InterfaceError:
            print("handling interface error and recreating the connection")
            get_database_connection(force=True)
            return func(*args, **kwargs)
    return wrapper


# Healthcheck for database
@retry_with_new_connection
def health() -> List[Tuple[int]]:
    with get_database_connection() as connection:
        # A cursor is needed to execute queries and deal with the result set.
        # It encapsulates things like fetch, fetchall, fetchmany etc.
        # We are creating a client-side cursor and not a server-side cursor.
        # Server-side cursor can be more memory efficient at the expense of more round trips i.e. more latency.
        # Client-side servers fetch all rows in a single round trip. Hence is network efficient but can be memory inefficient.
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            return cursor.fetchall()


@retry_with_new_connection
def _create_tables():
    # Helper function to create the tables.
    # https://www.psycopg.org/docs/connection.html
    # Context doesn't close the connection, hence we are certain
    # that different functions using connection with context managers
    # aren't closing the connection.
    # A context wraps a transaction:
    # if the context exits with success the transaction is committed, if it exits with an exception the transaction is rolled back
    # Hence, we don't have to deal with explicit connection.commit() and connection.rollback()
    # It's taken care of automatically because of the context manager.
    with get_database_connection() as connection:
        # Context closes the cursor, hence we don't need to worry about closing it
        # Although it's a client side cursor, and hence can be GCed and don't need to be explicitly closed
        # for efficient memory and resource handling, still for completeness keep it in the context manager
        # so that cursor.close() gets called automatically on exit of context.
        with connection.cursor() as cursor:
            cursor.execute(TYPE_DIFFICULTY_CREATE)
            cursor.execute(TYPE_KANDA_CREATE)
            cursor.execute(TABLE_QUESTION_CREATE)
            cursor.execute(TABLE_ANSWER_CREATE)


@retry_with_new_connection
def _drop_tables():
    # Helper function to drop the tables. Be extremely cautious!
    # Context doesn't close the connection, thus connection will still be usable.
    # Context will ensure that everything is wrapped in a transaction and committed at once
    # only if there is no exception
    with get_database_connection() as connection:
        # Context closes the cursor, hence we don't need to worry about closing it
        with connection.cursor() as cursor:
            cursor.execute(TABLE_ANSWER_DROP)
            cursor.execute(TABLE_QUESTION_DROP)
            cursor.execute(TYPE_DIFFICULTY_DROP)
            cursor.execute(TYPE_KANDA_DROP)


@retry_with_new_connection
def create_question(question: str, kanda: Kanda | None = None, tags: list[str] | None = None, difficulty: Difficulty | None = None, answers: list[dict] | None = None) -> int:
    tags = tags or []
    answers = answers or []
    kanda = kanda and kanda.value
    difficulty = difficulty and difficulty.value
    inserted_id = None
    connection = get_database_connection()
    # Context will take care of commiting or rolling back the transaction
    # No need to explicitly call connection.commit()
    with connection:
        # Again, context closes the cursor
        # We close the cursor for efficient memory and resource handling
        with connection.cursor() as cursor:
            # Both database execute() commands are part of a single transaction.
            # It would be rolled back automatically by the context manager in case of any exception
            try:
                cursor.execute(
                    "INSERT INTO questions (question, kanda, tags, difficulty) VALUES (%s, %s, %s, %s) RETURNING id",
                    (question, kanda, tags, difficulty),
                )
            # Should we reraise this exception or silently digest it.
            except UniqueViolation as e:
                print(f"Unique constraint violation while creating question {question}")
                raise e
            # There can be other exceptions too like NotNullViolation but we don't want to catch, log and re-raise everything.
            # Instead such exceptions would just be raised and clients of this helper should catch such exceptions.
            inserted_id = cursor.fetchone()[0]
            if len(answers) > 0:
                answers_tuples = [(inserted_id, answer["answer"], answer.get("is_correct", False)) for answer in answers]
                statement = "INSERT INTO answers (question_id, answer, is_correct) VALUES (%s, %s, %s)"
                cursor.executemany(statement, answers_tuples)
    return inserted_id


@retry_with_new_connection
def fetch_question(question_id: int) -> dict[str, str | int]:
    """
    Might raise InvalidTextRepresentation, but not handling it here.
    In case client sends an invalid input that would happen and clients should deal with it then.
    """
    result = None
    columns = None
    connection = get_database_connection()
    # No inserts happening here, hence no need for a commit or rollback.
    # Thus, ideally no need for connection context.
    # However for consistency with other functions, we use connection context
    # Also defensive programming.
    with connection:
        with connection.cursor() as cursor:
            statement = "SELECT id, question from questions WHERE id=%s"
            cursor.execute(statement, (question_id,))
            result = cursor.fetchone()
            columns = [col.name for col in cursor.description]
    if result is None:
        return {}
    row = {k: v for k, v in zip(columns, result)}
    return row


@retry_with_new_connection
def fetch_question_answers(question_id: int) -> list[dict[str, str | int]]:
    rows = []
    columns = None
    connection = get_database_connection()
    with connection:
        with connection.cursor() as cursor:
            statement = "SELECT a.id, a.answer from answers a WHERE a.question_id=%s"
            cursor.execute(statement, (question_id,))
            rows = cursor.fetchall()
            columns = [col.name for col in cursor.description]
    if rows == []:
        return []
    result = []
    for row in rows:
        result.append({k: v for k, v in zip(columns, row)})
    return result


@retry_with_new_connection
def create_questions_bulk(questions: list[dict[str, str | list | dict]]) -> list[int]:
    """
    This is a bulk operation.
    It handles unique violation error, in case a question violates unique constraint, that question would
    be skipped, while the other questions would be processed.
    """
    inserted_ids = []
    skipped_rows = []
    connection = get_database_connection()
    # We need to create every question in a separate transaction
    # because we want partial success.
    # If we use a single transaction, any unique constraint violation will cause entire one transaction
    # to rollback, thereby not allowing any row to be created.
    for index, question in enumerate(questions):
        with connection:
            with connection.cursor() as cursor:
                # Client should perform data validation and cleansing, and send appropriate data.
                question_text = question['question']
                kanda = question.get('kanda')
                tags = question.get('tags', [])
                difficulty = question.get('difficulty')
                answers = question.get('answers', [])
                try:
                    cursor.execute(
                        "INSERT INTO questions (question, kanda, tags, difficulty) VALUES (%s, %s, %s, %s) RETURNING id",
                        (question_text, kanda, tags, difficulty),
                    )
                except UniqueViolation:
                    print(f"Unique constraint violation while creating question {question_text}")
                    skipped_rows.append(index + 1)
                    continue
                inserted_id = cursor.fetchone()[0]
                inserted_ids.append(inserted_id)
                if len(answers) > 0:
                    for answer in answers:
                        cursor.execute(
                            "INSERT INTO answers (question_id, answer, is_correct) VALUES (%s, %s, %s)",
                            (inserted_id, answer["answer"], answer.get("is_correct", False)),
                        )
    return inserted_ids, skipped_rows


@retry_with_new_connection
def list_questions(limit: int = 20, offset: int = 0, difficulty: str | None = None) -> list[dict[str, Any]]:
    connection = get_database_connection()
    rows = []
    columns = []
    # We need to perform limit on the parent table and fetch all child rows for each parent rows
    # This cannot be achieved with a simple limit clause
    # To restrict and ensure correct number of parent rows we need to fetch on parent table in a subquery
    subquery = """
        SELECT id
        FROM questions
    """
    if difficulty is not None:
        subquery += f" WHERE difficulty = '{difficulty}'"
    subquery += f" ORDER BY id LIMIT {limit} OFFSET {offset}"
    query = f"""
    SELECT questions.id as id, question, difficulty, kanda, tags, information, answers.id as answer_id, answer, is_correct,
           question_hindi, question_telugu, answer_hindi, answer_telugu
    FROM questions
    LEFT JOIN answers
    ON questions.id = answers.question_id
    WHERE questions.id in ({subquery})
    ORDER BY questions.id, answers.id
    """
    with connection:
        with connection.cursor() as cursor:
            # id is the primary key, hence has an index
            # We are ordering on an indexed field
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]
    if len(rows) == 0:
        return rows
    questions = []
    # Apply labels and covert to a list of dict
    for row in rows:
        row_dict = {}
        value_index = 0
        column_index = 0
        while column_index < len(columns) and value_index < len(row):
            row_dict[columns[column_index]] = row[value_index]
            value_index += 1
            column_index += 1
        questions.append(row_dict)
    # Let's apply two pointers just for fun
    # instead of using zip
    # Group the answers for same question
    grouped_answers = []
    first_question = questions[0]
    grouped_answers.append({'id': first_question['id'], 'question': first_question['question'], 'difficulty': first_question['difficulty'], 'kanda': first_question['kanda'], 'tags': first_question['tags'],
                            'question_telugu': first_question['question_telugu'], 'question_hindi': first_question['question_hindi'], 'information': first_question['information'],
                            'answers': [{'id': first_question['answer_id'], 'answer': first_question['answer'], 'is_correct': first_question['is_correct'], 'answer_hindi': first_question['answer_hindi'], 'answer_telugu': first_question['answer_telugu']}]})
    for index in range(1, len(questions)):
        question = questions[index]
        if question['id'] == first_question['id']:
            grouped_answers[-1]['answers'].append({'id': question['answer_id'], 'answer': question['answer'], 'is_correct': question['is_correct'], 'answer_hindi': question['answer_hindi'], 'answer_telugu': question['answer_telugu']})
        else:
            first_question = question
            grouped_answers.append({'id': first_question['id'], 'question': first_question['question'], 'difficulty': first_question['difficulty'], 'kanda': first_question['kanda'], 'tags': first_question['tags'],
                                    'question_telugu': first_question['question_telugu'], 'question_hindi': first_question['question_hindi'], 'information': first_question['information'],
                                    'answers': []})
            grouped_answers[-1]['answers'].append({'id': question['answer_id'], 'answer': question['answer'], 'is_correct': question['is_correct'], 'answer_hindi': question['answer_hindi'], 'answer_telugu': question['answer_telugu']})

    return grouped_answers


@retry_with_new_connection
def recent_questions_count(last_question_id: int):
    connection = get_database_connection()
    rows = []
    query = f"""
    SELECT count(questions.id)
    FROM questions
    WHERE questions.id > {last_question_id}
    """
    with connection:
        with connection.cursor() as cursor:
            # id is the primary key, hence has an index
            # We are ordering on an indexed field
            cursor.execute(query)
            rows = cursor.fetchall()
    return rows[0][0]


@retry_with_new_connection
def most_recent_question_id():
    connection = get_database_connection()
    rows = []
    query = """
    SELECT id
    FROM questions
    ORDER BY id DESC
    LIMIT 1
    """
    with connection:
        with connection.cursor() as cursor:
            # id is the primary key, hence has an index
            # We are ordering on an indexed field
            cursor.execute(query)
            rows = cursor.fetchall()
    return rows[0][0]
