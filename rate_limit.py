"""
Rate Limiter should support the following functionality:
- x number of requests per interval

Window starts on the first request and stays till the end of the interval.

Once user has reached x number of requests, we need to start responding with status code 429
The unique identifier for the user can be the ip address.

We will implement it as a decorator, so that the path functions can be decorated with it.
"""

import redis

from constants import REDIS_HOST, REDIS_PORT


redis_connection = None


def get_redis_connection(force=False):
    global redis_connection
    if redis_connection is None or force is True:
        redis_connection = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    return redis_connection


class RateLimiter(object):

    INTERVAL = 60     # 1 minute
    QUOTA = 5         # Number of allowed requests

    def __init__(self, connection=None):
        if connection is None:
            connection = get_redis_connection()
        self.connection = connection

    def _first_request(self, identifier):
        self.connection.set(identifier, 1)
        self.connection.expire(identifier, RateLimiter.INTERVAL)

    def _increment(self, identifier):
        self.connection.incr(identifier)

    def check(self, identifier):
        """
        Check if this identifier is allowed to make the request or if it
        has consumed it's quota.

        The following things should happen:
        1. Check if this identifier has already been used. If not, add it to Redis, and allow the request.
        2. If this identifier exists, then check the current count. If it does not exceed the quota, then disallow the request.
        3. If this identifier exists, then check the current count. If it exceeds the quota, then disallow the request.
        """
        current_count = self.connection.get(identifier)
        if current_count is None:
            self._first_request(identifier)
            return True
        else:
            # Entry exists in the backing store, which means
            # this is not the first request.
            current_count = int(current_count)
            if current_count < RateLimiter.QUOTA:
                # Allow since current count is still less than the quota
                self._increment(identifier=identifier)
                return True
            else:
                # Disallow, quota for this window has been consumed.
                return False
