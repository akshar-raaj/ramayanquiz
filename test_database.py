from unittest.mock import Mock, patch, MagicMock
from psycopg2 import InterfaceError
from psycopg2.errors import OperationalError


from database import get_database_connection, retry_with_new_connection, _create_tables, _drop_tables, health, create_question, fetch_question, fetch_question_answers, recent_questions_count
from constants import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


@patch('database.psycopg2')
def test_get_database_connection(mocked_psycopg2):
    mocked_connection = Mock()
    mocked_psycopg2.connect.return_value = mocked_connection
    get_database_connection()
    assert mocked_psycopg2.connect.called
    mocked_psycopg2.connect.assert_called_with(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    assert mocked_psycopg2.connect.call_count == 1

    # Check that the connection gets reused and every call to get_database_connection
    # does not invoke psycopg2.connect
    # Assert that the second call to get_database_connection
    # does not call psycopg2.connect
    _ = get_database_connection()
    assert mocked_psycopg2.connect.call_count == 1

    # Assert that the second call to get_database_connection
    # does invokes psycopg2.connect if force is used
    _ = get_database_connection(force=True)
    assert mocked_psycopg2.connect.call_count == 2


@patch('database.get_database_connection')
def test_retry_with_new_connection(mocked_get_connection):
    # Simulates a mock function that uses connection to make a db query
    dummy_function = Mock()
    mocked_return_value = Mock()
    # In the first invocation, it will raise an InterfaceError
    # In the second invocation, it will return mocked_return_value
    dummy_function.side_effect = [InterfaceError, mocked_return_value]
    # Mimic decorating dummy function
    wrapper = retry_with_new_connection(dummy_function)
    return_value = wrapper()
    assert mocked_get_connection.called is True
    mocked_get_connection.assert_called_with(force=True)
    assert return_value == mocked_return_value
    assert dummy_function.call_count == 2


@patch('database.get_database_connection')
def test_create_tables(mocked_get_connection):
    # Need MagicMock instead of Mock because connection is used as a context manager
    # and hence need a __enter__ dunder method.
    mocked_connection = MagicMock()

    # Mocking the context manager methods
    mocked_connection.__enter__.return_value = mocked_connection
    mocked_connection.__exit__.return_value = None

    mocked_get_connection.return_value = mocked_connection
    mocked_cursor = MagicMock()
    # Mocking the context manager methods
    mocked_cursor.__enter__.return_value = mocked_cursor
    mocked_cursor.__exit__.return_value = None

    mocked_connection.cursor.return_value = mocked_cursor
    _create_tables()
    assert mocked_get_connection.called
    assert mocked_connection.cursor.called
    assert mocked_cursor.execute.call_count == 4


@patch('database.get_database_connection')
def test_drop_tables(mocked_get_connection):
    # Need MagicMock instead of Mock because connection is used as a context manager
    # and hence need a __enter__ dunder method.
    mocked_connection = MagicMock()
    # Mocking the context manager methods
    mocked_connection.__enter__.return_value = mocked_connection
    mocked_connection.__exit__.return_value = None

    mocked_get_connection.return_value = mocked_connection
    mocked_cursor = MagicMock()
    # Mocking the context manager methods
    mocked_cursor.__enter__.return_value = mocked_cursor
    mocked_cursor.__exit__.return_value = None
    mocked_connection.cursor.return_value = mocked_cursor
    _drop_tables()
    assert mocked_get_connection.called
    assert mocked_connection.cursor.called
    assert mocked_cursor.execute.call_count == 4


@patch("database.get_database_connection")
def test_health(mocked_get_connection):
    mocked_connection = MagicMock()
    mocked_get_connection.return_value = mocked_connection
    # Mocking the context manager methods
    mocked_connection.__enter__.return_value = mocked_connection
    mocked_connection.__exit__.return_value = None

    mocked_cursor = MagicMock()
    mocked_cursor.__enter__.return_value = mocked_cursor
    mocked_cursor.__exit__.return_value = None
    mocked_connection.cursor.return_value = mocked_cursor

    health()

    assert mocked_cursor.execute.called
    assert mocked_cursor.fetchall.called


@patch("database.get_database_connection")
def test_create_question(mocked_get_connection):
    mocked_connection = MagicMock()
    mocked_get_connection.return_value = mocked_connection
    # Mocking the context manager methods
    mocked_connection.__enter__.return_value = mocked_connection
    mocked_connection.__exit__.return_value = None

    mocked_cursor = MagicMock()
    mocked_cursor.__enter__.return_value = mocked_cursor
    mocked_cursor.__exit__.return_value = None
    mocked_connection.cursor.return_value = mocked_cursor

    create_question("Who was Lord Rama's father?", "Balakanda", ["Rama", "Ayodhya"],
                    answers=[{"answer": "King Dasrath", "is_correct": True}, {"answer": "Lord Janaka", "is_correct": False}])

    # One db call to create the question.
    assert mocked_cursor.execute.call_count == 1
    # One executemany call for create the answers
    assert mocked_cursor.executemany.call_count == 1
    assert mocked_cursor.fetchone.called


@patch("database.get_database_connection")
def test_fetch_question(mocked_get_connection):
    mocked_connection = MagicMock()
    mocked_get_connection.return_value = mocked_connection
    # Mocking the context manager methods
    mocked_connection.__enter__.return_value = mocked_connection
    mocked_connection.__exit__.return_value = None

    mocked_cursor = MagicMock()
    mocked_cursor.__enter__.return_value = mocked_cursor
    mocked_cursor.__exit__.return_value = None
    mocked_connection.cursor.return_value = mocked_cursor

    fetch_question(question_id=1)

    assert mocked_cursor.execute.call_count == 1
    assert mocked_cursor.fetchone.call_count == 1


@patch("database.get_database_connection")
def test_fetch_question_answers(mocked_get_connection):
    mocked_connection = MagicMock()
    mocked_get_connection.return_value = mocked_connection
    # Mocking the context manager methods
    mocked_connection.__enter__.return_value = mocked_connection
    mocked_connection.__exit__.return_value = None

    mocked_cursor = MagicMock()
    mocked_cursor.__enter__.return_value = mocked_cursor
    mocked_cursor.__exit__.return_value = None
    mocked_connection.cursor.return_value = mocked_cursor

    fetch_question_answers(question_id=1)

    assert mocked_cursor.execute.call_count == 1
    assert mocked_cursor.fetchall.call_count == 1


@patch("database.get_database_connection")
def test_recent_questions_count(mocked_get_connection):
    mocked_connection = MagicMock()
    mocked_get_connection.return_value = mocked_connection
    # Mocking the context manager methods
    mocked_connection.__enter__.return_value = mocked_connection
    mocked_connection.__exit__.return_value = None

    mocked_cursor = MagicMock()
    mocked_cursor.__enter__.return_value = mocked_cursor
    mocked_cursor.__exit__.return_value = None
    mocked_connection.cursor.return_value = mocked_cursor

    recent_questions_count(last_question_id=1)

    assert mocked_cursor.execute.call_count == 1
    assert mocked_cursor.fetchall.call_count == 1
