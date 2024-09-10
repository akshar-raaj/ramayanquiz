from constants import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

import psycopg2


TYPE_DIFFICULTY_CREATE = """
CREATE TYPE difficulty AS ENUM ('easy', 'medium', 'hard')
"""

TYPE_KANDA_CREATE = """
CREATE TYPE kanda AS ENUM ('Bala Kanda', 'Ayodhya Kanda', 'Aranya Kanda', 'Kishkinda Kanda', 'Sundara Kanda', 'Yuddha Kanda', 'Uttara Kanda')
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
def create_question(question: str, kanda: str | None = None, tags: list[str] = list(), difficulty: str | None = None, answers: list[dict] = list()):
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
            cursor.execute(
                "INSERT INTO questions (question, kanda, tags, difficulty) VALUES (%s, %s, %s, %s) RETURNING id",
                (question, kanda, tags, difficulty),
            )
            inserted_id = cursor.fetchone()[0]
            if len(answers) > 0:
                for answer in answers:
                    cursor.execute(
                        "INSERT INTO answers (question_id, answer, is_correct) VALUES (%s, %s, %s)",
                        (inserted_id, answer["answer"], answer.get("is_correct", False)),
                    )
    return inserted_id


@retry_with_new_connection
def create_questions_bulk(questions: list):
    """
    This is a bulk operation, either all question/answers would be inserted
    or no row would be inserted.
    """
    inserted_ids = []
    connection = get_database_connection()
    # We have created a context.
    # Hence transaction will be committed on successful execution of the block
    # or else it would be rolled back
    # *No need* to explicitly call connection.commit()
    with connection:
        with connection.cursor() as cursor:
            for question in questions:
                # Client should perform data validation and cleansing, and send appropriate data.
                question_text = question['question']
                kanda = question.get('kanda')
                tags = question.get('tags', [])
                difficulty = question.get('difficulty')
                answers = question.get('answers', [])
                cursor.execute(
                    "INSERT INTO questions (question, kanda, tags, difficulty) VALUES (%s, %s, %s, %s) RETURNING id",
                    (question_text, kanda, tags, difficulty),
                )
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
def get_questions(limit=20, offset=0):
    connection = get_database_connection()
    rows = []
    columns = []
    # We need to perform limit on the parent table and fetch all child rows for each parent rows
    # This cannot be achieved with a simple limit clause
    # To restrict and ensure correct number of parent rows we need to fetch on parent table in a subquery
    query = f"""
    SELECT questions.id as id, question, difficulty, kanda, tags, answers.id as answer_id, answer, is_correct
    FROM (
        SELECT id, question, difficulty, kanda, tags
        FROM questions
        ORDER BY id
        LIMIT {limit}
        OFFSET {offset}
    ) AS questions
    LEFT JOIN answers
    ON questions.id = answers.question_id
    ORDER BY questions.id, answers.id
    """
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
    grouped_answers.append({'id': first_question['id'], 'question': first_question['question'], 'difficulty': first_question['difficulty'], 'kanda': first_question['kanda'], 'tags': first_question['tags'], 'answers': [{'id': first_question['answer_id'], 'answer': first_question['answer'], 'is_correct': first_question['is_correct']}]})
    for index in range(1, len(questions)):
        question = questions[index]
        if question['id'] == first_question['id']:
            grouped_answers[-1]['answers'].append({'id': question['answer_id'], 'answer': question['answer'], 'is_correct': question['is_correct']})
        else:
            first_question = question
            grouped_answers.append({'id': first_question['id'], 'question': first_question['question'], 'difficulty': first_question['difficulty'], 'kanda': first_question['kanda'], 'tags': first_question['tags'], 'answers': []})
            grouped_answers[-1]['answers'].append({'id': question['answer_id'], 'answer': question['answer'], 'is_correct': question['is_correct']})

    return grouped_answers
