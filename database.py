from constants import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

import psycopg2
from psycopg2.errors import UniqueViolation


TYPE_DIFFICULTY_CREATE = """
CREATE TYPE difficulty AS ENUM ('easy', 'medium', 'hard')
"""

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

connection = None


def get_database_connection(force: bool = False):
    """
    Creates a database connection if needed and keeps it cached on a global variable.
    We don't want to create a database connection, each time this function gets invoked.
    """
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
        except psycopg2.InterfaceError:
            print("handling interface error")
            get_database_connection(force=True)
            return func(*args, **kwargs)
    return wrapper


@retry_with_new_connection
def _create_tables():
    # Helper function to create the tables.
    # https://www.psycopg.org/docs/connection.html
    # Context doesn't close the connection, hence we are certain
    # that different functions using connection with context managers
    # aren't closing the connection.
    # A context wraps a transaction:
    # if the context exits with success the transaction is committed, if it exits with an exception the transaction is rolled back
    with get_database_connection() as connection:
        # Context closes the cursor, hence we don't need to worry about closing it
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
def create_question(question: str, kanda: str | None = None, tags: list[str] | None = None, difficulty: str | None = None, answers: list[dict] | None = None) -> int:
    tags = tags or []
    answers = answers or []
    inserted_id = None
    connection = get_database_connection()
    # We have created a context.
    # Hence transaction will be committed on successful execution of the block
    # or else it would be rolled back
    # No need to explicitly call connection.commit()
    with connection:
        with connection.cursor() as cursor:
            # Both database execute() commands are part of a single transaction.
            # It would be rolled back automatically by the context manager in case of any exception
            # We considered adding an exception handler in following lines.
            # There could be exceptions because of constraint violation etc.
            # However, we want the client to be mature and send clean data to this function
            # The client should have exception handler while invoking this function.
            try:
                cursor.execute(
                    "INSERT INTO questions (question, kanda, tags, difficulty) VALUES (%s, %s, %s, %s) RETURNING id",
                    (question, kanda, tags, difficulty),
                )
            except UniqueViolation:
                print(f"Unique constraint violation while creating question {question}")
                return inserted_id
            inserted_id = cursor.fetchone()[0]
            if len(answers) > 0:
                answers_tuples = [(inserted_id, answer["answer"], answer.get("is_correct", False)) for answer in answers]
                statement = "INSERT INTO answers (question_id, answer, is_correct) VALUES (%s, %s, %s)"
                cursor.executemany(statement, answers_tuples)
    return inserted_id


@retry_with_new_connection
def fetch_question(question_id: int) -> dict[str, str | int]:
    result = None
    columns = None
    connection = get_database_connection()
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
def update_column_value(table_name: str, _id: int, column_name: str, column_value) -> bool:
    is_completed = False
    connection = get_database_connection()
    with connection:
        with connection.cursor() as cursor:
            statement = f'UPDATE {table_name} SET {column_name}=%s where id=%s'
            cursor.execute(statement, (column_value, _id,))
            is_completed = True
    return is_completed


@retry_with_new_connection
def create_questions_bulk(questions: list[dict[str, str | list | dict]]) -> list[int]:
    """
    This is a bulk operation.
    It handles unique violation error, in case a question violates unique constraint, that question would
    be skipped, while the other questions would be processed.
    """
    inserted_ids = []
    connection = get_database_connection()
    for question in questions:
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
                    continue
                inserted_id = cursor.fetchone()[0]
                inserted_ids.append(inserted_id)
                if len(answers) > 0:
                    for answer in answers:
                        cursor.execute(
                            "INSERT INTO answers (question_id, answer, is_correct) VALUES (%s, %s, %s)",
                            (inserted_id, answer["answer"], answer.get("is_correct", False)),
                        )
    return inserted_ids


# Write a function to retrieve the questions
@retry_with_new_connection
def list_questions(limit: int = 20, offset: int = 0, difficulty: str = None):
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
    SELECT questions.id as id, question, difficulty, kanda, tags, answers.id as answer_id, answer, is_correct,
           question_hindi, question_telugu, answer_hindi, answer_telugu
    FROM questions
    LEFT JOIN answers
    ON questions.id = answers.question_id
    WHERE questions.id in ({subquery})
    ORDER BY questions.id, answers.id
    """
    print(query)
    with connection:
        with connection.cursor() as cursor:
            # id is the primary key, hence has an index
            # We are ordering on an indexed field
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]
    # Let's apply two pointers just for fun
    # instead of using zip
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
    # Group the answers for same question
    grouped_answers = []
    first_question = questions[0]
    grouped_answers.append({'id': first_question['id'], 'question': first_question['question'], 'difficulty': first_question['difficulty'], 'kanda': first_question['kanda'], 'tags': first_question['tags'], 'answers': [{'id': first_question['answer_id'], 'answer': first_question['answer'], 'is_correct': first_question['is_correct'], 'answer_hindi': first_question['answer_hindi'], 'answer_telugu': first_question['answer_telugu']}],
                            'question_telugu': first_question['question_telugu'], 'question_hindi': first_question['question_hindi']})
    for index in range(1, len(questions)):
        question = questions[index]
        if question['id'] == first_question['id']:
            grouped_answers[-1]['answers'].append({'id': question['answer_id'], 'answer': question['answer'], 'is_correct': question['is_correct'], 'answer_hindi': question['answer_hindi'], 'answer_telugu': question['answer_telugu']})
        else:
            first_question = question
            grouped_answers.append({'id': first_question['id'], 'question': first_question['question'], 'difficulty': first_question['difficulty'], 'kanda': first_question['kanda'], 'tags': first_question['tags'], 'answers': [],
                                    'question_telugu': first_question['question_telugu'], 'question_hindi': first_question['question_hindi']})
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
