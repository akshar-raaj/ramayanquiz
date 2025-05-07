import redis

from constants import REDIS_HOST, REDIS_PORT


redis_connection = None


def get_redis_connection(force=False):
    """
    Python Redis client tries to restablish the connection in case the connection has been lost.
    Connection could be lost because of the server closing the connection. This could happen because of
    idle timeout, max connections reached etc.
    As Python client tries to reestablish the connection, we don't need to worry about it, as in PostgreSQL.
    """
    global redis_connection
    if redis_connection is None or force is True:
        redis_connection = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    return redis_connection


def health():
    redis_connection = get_redis_connection()
    return redis_connection.ping()
