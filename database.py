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
            cursor.execute(TABLE_ANSWER_CREATE)


@retry_with_new_connection
def _drop_tables():
    # Helper function to drop the tables. Be extremely cautious!
    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(TABLE_QUESTION_DROP)
            cursor.execute(TYPE_DIFFICULTY_DROP)
            cursor.execute(TABLE_ANSWER_DROP)


@retry_with_new_connection
def create_question(question: str, kanda: str | None = None, tags: list[str] | None = None, difficulty: str | None = None, answers: list[dict] = list()):
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


# Write a function to retrieve the questions
@retry_with_new_connection
def get_questions():
    connection = get_database_connection()
    rows = []
    columns = []
    # query = """
    # SELECT q.id as question_id, question, a.id as answer_id, answer, is_correct FROM questions q INNER JOIN answers a on q.id=a.question_id;
    # """
    query = """
    SELECT questions.id as id, question, answers.id as answer_id, answer, is_correct
    FROM (
        SELECT id, question
        FROM questions
        ORDER BY id
        LIMIT 20
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
    print(columns)
    if len(rows) == 0:
        return rows
    questions = []
    # questions.append()
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
    grouped_answers.append({'id': first_question['id'], 'question': first_question['question'], 'answers': [{'id': first_question['answer_id'], 'answer': first_question['answer'], 'is_correct': first_question['is_correct']}]})
    for index in range(1, len(questions)):
        question = questions[index]
        if question['id'] == first_question['id']:
            grouped_answers[-1]['answers'].append({'id': question['answer_id'], 'answer': question['answer'], 'is_correct': question['is_correct']})
        else:
            first_question = question
            grouped_answers.append({'id': first_question['id'], 'question': first_question['question'], 'answers': []})
            grouped_answers[-1]['answers'].append({'id': question['answer_id'], 'answer': question['answer'], 'is_correct': question['is_correct']})

    # return questions
    return grouped_answers
