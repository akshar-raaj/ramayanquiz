from unittest.mock import Mock, patch


from database import get_database_connection
from constants import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


@patch('database.psycopg2')
def test_get_database_connection(mocked_psycopg2):
    mocked_connection = Mock()
    mocked_psycopg2.connect.return_value = mocked_connection
    connection = get_database_connection()
    assert mocked_psycopg2.connect.called
    mocked_psycopg2.connect.assert_called_with(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    assert connection is mocked_connection
    assert mocked_psycopg2.connect.call_count == 1

    # Assert that the second call to get_database_connection
    # does not call psycopg2.connect
    _ = get_database_connection()
    assert mocked_psycopg2.connect.call_count == 1

    # Assert that the second call to get_database_connection
    # does invokes psycopg2.connect if force is used
    _ = get_database_connection(force=True)
    assert mocked_psycopg2.connect.call_count == 2
