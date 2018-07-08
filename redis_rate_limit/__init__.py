#!/usr/bin/env python
#  -*- coding: utf-8 -*-
from hashlib import sha1
from distutils.version import StrictVersion
from redis.exceptions import NoScriptError
from redis import Redis, ConnectionPool

__version__ = "0.0.1"

# Adapted from http://redis.io/commands/incr#pattern-rate-limiter-2
INCREMENT_SCRIPT = b"""
    local current
    current = tonumber(redis.call("incrby", KEYS[1], ARGV[2]))
    if current == tonumber(ARGV[2]) then
        redis.call("expire", KEYS[1], ARGV[1])
    end
    return current
"""
INCREMENT_SCRIPT_HASH = sha1(INCREMENT_SCRIPT).hexdigest()

REDIS_POOL = ConnectionPool(host='127.0.0.1', port=6379, db=0)


class RedisVersionNotSupported(Exception):
    """
    Rate Limit depends on Redis’ commands EVALSHA and EVAL which are
    only available since the version 2.6.0 of the database.
    """
    pass


class TooManyRequests(Exception):
    """
    Occurs when the maximum number of requests is reached for a given resource
    of an specific user.
    """
    pass

class InitialValueTooHigh(Exception):
    """
    Happens when we try to increment the rate limiter far beyond
    the actual limit.

    e.g. when the rate limit is 5 requests per second, and we increment
    the counter by 20.
    """
    pass


class RateLimit(object):
    """
    This class offers an abstraction of a Rate Limit algorithm implemented on
    top of Redis >= 2.6.0.
    """
    def __init__(self, resource, client, max_requests, expire=None, redis_pool=REDIS_POOL):
        """
        Class initialization method checks if the Rate Limit algorithm is
        actually supported by the installed Redis version and sets some
        useful properties.

        If Rate Limit is not supported, it raises an Exception.

        :param resource: resource identifier string (i.e. ‘user_pictures’)
        :param client: client identifier string (i.e. ‘192.168.0.10’)
        :param max_requests: integer (i.e. ‘10’)
        :param expire: seconds to wait before resetting counters (i.e. ‘60’)
        :param redis_pool: instance of redis.ConnectionPool.
               Default: ConnectionPool(host='127.0.0.1', port=6379, db=0)
        """
        self._redis = Redis(connection_pool=redis_pool)
        if not self._is_rate_limit_supported():
            raise RedisVersionNotSupported()

        self._rate_limit_key = "rate_limit:{0}_{1}".format(resource, client)
        self._max_requests = max_requests
        self._expire = expire or 1

    def __enter__(self):
        self.increment_usage()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_usage(self):
        """
        Returns actual resource usage by client. Note that it could be greater
        than the maximum number of requests set.

        :return: integer: current usage
        """
        return int(self._redis.get(self._rate_limit_key) or 0)

    def get_wait_time(self):
        """
        Returns estimated optimal wait time for subsequent requests.
        If limit has already been reached, return wait time until it gets reset.

        :return: float: wait time in seconds
        """
        ttl = self._redis.pttl(self._rate_limit_key)
        # If the key wasn't set or its TTL can't be found, then
        # default to the key expiration time as the TTL
        ttl = ttl / 1000.0 if ttl else float(self._expire)
        usage = self.get_usage()
        # If we exceeded the rate limit
        if self.has_been_reached():
            # return expire * (self.get_usage() / self._max_requests)
            # time_elapsed is how much time since the TTL was set on the key
            time_elapsed = self._expire - ttl
            # This the percentage of total allowable requests
            # that have been executed since the key was created.
            usage_ratio = usage / self._max_requests
            # This is the number of seconds that the client should wait
            # before trying again, assuming that no time elapsed
            # between making the key and achieving this usage ratio.
            seconds_per_usage = self._expire * usage_ratio
            # We subtract time elapsed in this bucket to account for
            # the requests that "belong" in the current bucket.
            # If usage_ratio > 1, then we have requests that should belong
            # in the next bucket, and the client should pay a time penalty
            # for its aggressive requesting.
            wait_duration = seconds_per_usage - time_elapsed
            return wait_duration
        # If we haven't incremented the counter at all.
        elif usage == 0:
            # We say that no wait time is needed if the key has not been
            # incremented since it was created.
            # People will only need to wait *after* the first usage.
            return 0
        # If we have made requests, but not yet hit the rate limit.
        else:
            # This returns the approximate amount of time-per-request
            # left in the TTL, based on how many requests have been
            # made already.
            return ttl / (self._max_requests - usage)

    def has_been_reached(self):
        """
        Checks if Rate Limit has been reached.

        :return: bool: True if limit has been reached or False otherwise
        """
        return self.get_usage() >= self._max_requests

    def increment_usage(self, increment_by=1):
        """
        Calls a LUA script that should increment the resource usage by client.

        If the resource limit overflows the maximum number of requests, this
        method raises an Exception.

        :param increment_by: The count to increment the rate limiter by.
        This is typically 1, but higher or lower values are provided
        for more flexible rate-limiting schemes.

        :return: integer: current usage
        """
        if increment_by > self._max_requests:
            raise InitialValueTooHigh(
                f"Value to increment by {increment_by} is greater than "
                f"the maximum of {self._max_requests}"
            )
        try:
            current_usage = self._redis.evalsha(
                INCREMENT_SCRIPT_HASH, 1, self._rate_limit_key, self._expire, increment_by)
        except NoScriptError:
            current_usage = self._redis.eval(
                INCREMENT_SCRIPT, 1, self._rate_limit_key, self._expire, increment_by)

        if int(current_usage) > self._max_requests:
            raise TooManyRequests(
                f"{current_usage} is over the maximum of {self._max_requests}"
            )

        return current_usage

    def _is_rate_limit_supported(self):
        """
        Checks if Rate Limit is supported which can basically be found by
        looking at Redis database version that should be 2.6.0 or greater.

        :return: bool
        """
        redis_version = self._redis.info()['redis_version']
        is_supported = StrictVersion(redis_version) >= StrictVersion('2.6.0')
        return bool(is_supported)

    def _reset(self):
        """
        Deletes all keys that start with ‘rate_limit:’.
        """
        matching_keys = self._redis.scan_iter(match='{0}*'.format('rate_limit:*'))
        for rate_limit_key in matching_keys:
            self._redis.delete(rate_limit_key)


class RateLimiter(object):
    def __init__(self, resource, max_requests, expire=None, redis_pool=REDIS_POOL):
        """
        Rate limit factory. Checks if RateLimit is supported when limit is called.
        :param resource: resource identifier string (i.e. ‘user_pictures’)
        :param max_requests: integer (i.e. ‘10’)
        :param expire: seconds to wait before resetting counters (i.e. ‘60’)
        :param redis_pool: instance of redis.ConnectionPool.
               Default: ConnectionPool(host='127.0.0.1', port=6379, db=0)
       """
        self.resource = resource
        self.max_requests = max_requests
        self.expire = expire
        self.redis_pool = redis_pool

    def limit(self, client):
        """
        :param client: client identifier string (i.e. ‘192.168.0.10’)
        """
        return RateLimit(
            resource=self.resource,
            client=client,
            max_requests=self.max_requests,
            expire=self.expire,
            redis_pool=self.redis_pool,
        )
