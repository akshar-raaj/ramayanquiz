from database import retry_with_new_connection
from database import get_database_connection


QUESTIONS_ADD_COLUMN_HINDI = """
    ALTER TABLE questions ADD IF NOT EXISTS question_hindi text;
"""

QUESTIONS_ADD_COLUMN_TELUGU = """
    ALTER TABLE questions ADD IF NOT EXISTS question_telugu text;
"""

ANSWERS_ADD_COLUMN_HINDI = """
    ALTER TABLE answers ADD IF NOT EXISTS answer_hindi text;
"""

ANSWERS_ADD_COLUMN_TELUGU = """
    ALTER TABLE answers ADD IF NOT EXISTS answer_telugu text;
"""


@retry_with_new_connection
def migrate():
    connection = get_database_connection()
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(QUESTIONS_ADD_COLUMN_HINDI)
            cursor.execute(ANSWERS_ADD_COLUMN_HINDI)
            cursor.execute(QUESTIONS_ADD_COLUMN_TELUGU)
            cursor.execute(ANSWERS_ADD_COLUMN_TELUGU)

migrate()