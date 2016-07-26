#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import time
from redis_rate_limit import RateLimit, TooManyRequests


class TestRedisRateLimit(unittest.TestCase):
    def setUp(self):
        """
        Initialises Rate Limit class and delete all keys from Redis.
        """
        self.rate_limit = RateLimit(resource='test', client='localhost',
                                    max_requests=10)
        self.rate_limit._reset()

    def _make_10_requests(self):
        """
        Increments usage ten times.
        """
        for x in range(0, 10):
            with self.rate_limit:
                pass

    def test_limit_10_max_request(self):
        """
        Should raise TooManyRequests Exception when trying to increment for the
        eleventh time.
        """
        self.assertEquals(self.rate_limit.get_usage(), 0)
        self.assertEquals(self.rate_limit.has_been_reached(), False)

        self._make_10_requests()
        self.assertEquals(self.rate_limit.get_usage(), 10)
        self.assertEquals(self.rate_limit.has_been_reached(), True)

        with self.assertRaises(TooManyRequests):
            with self.rate_limit:
                pass

        self.assertEquals(self.rate_limit.get_usage(), 11)
        self.assertEquals(self.rate_limit.has_been_reached(), True)

    def test_expire(self):
        """
        Should not raise TooManyRequests Exception when trying to increment for
        the eleventh time after the expire time.
        """
        self._make_10_requests()
        time.sleep(1)
        with self.rate_limit:
            pass

    def test_not_expired(self):
        """
        Should raise TooManyRequests Exception when the expire time has not
        been reached yet.
        """
        self.rate_limit = RateLimit(resource='test', client='localhost',
                                    max_requests=10, expire=2)
        self._make_10_requests()
        time.sleep(1)
        with self.assertRaises(TooManyRequests):
            with self.rate_limit:
                pass


if __name__ == '__main__':
    unittest.main()

