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
    current = tonumber(redis.call("incr", KEYS[1]))
    if current == 1 then
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

    def has_been_reached(self):
        """
        Checks if Rate Limit has been reached.

        :return: bool: True if limit has been reached or False otherwise
        """
        return self.get_usage() >= self._max_requests

    def increment_usage(self):
        """
        Calls a LUA script that should increment the resource usage by client.

        If the resource limit overflows the maximum number of requests, this
        method raises an Exception.

        :return: integer: current usage
        """
        try:
            current_usage = self._redis.evalsha(
                INCREMENT_SCRIPT_HASH, 1, self._rate_limit_key, self._expire)
        except NoScriptError:
            current_usage = self._redis.eval(
                INCREMENT_SCRIPT, 1, self._rate_limit_key, self._expire)

        if int(current_usage) > self._max_requests:
            raise TooManyRequests()

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
