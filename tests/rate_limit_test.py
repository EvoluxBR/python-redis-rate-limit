#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import time
from redis_rate_limit import RateLimit, RateLimiter, TooManyRequests


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
        self.assertEqual(self.rate_limit.get_usage(), 0)
        self.assertEqual(self.rate_limit.has_been_reached(), False)

        self._make_10_requests()
        self.assertEqual(self.rate_limit.get_usage(), 10)
        self.assertEqual(self.rate_limit.has_been_reached(), True)

        with self.assertRaises(TooManyRequests):
            with self.rate_limit:
                pass

        self.assertEqual(self.rate_limit.get_usage(), 11)
        self.assertEqual(self.rate_limit.has_been_reached(), True)

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

    def test_limit_10_using_rate_limiter(self):
        """
        Should raise TooManyRequests Exception when trying to increment for the
        eleventh time.
        """
        self.rate_limit = RateLimiter(resource='test', max_requests=10,
                                      expire=2).limit(client='localhost')
        self.assertEqual(self.rate_limit.get_usage(), 0)
        self.assertEqual(self.rate_limit.has_been_reached(), False)

        self._make_10_requests()
        self.assertEqual(self.rate_limit.get_usage(), 10)
        self.assertEqual(self.rate_limit.has_been_reached(), True)

        with self.assertRaises(TooManyRequests):
            with self.rate_limit:
                pass

        self.assertEqual(self.rate_limit.get_usage(), 11)
        self.assertEqual(self.rate_limit.has_been_reached(), True)

    def test_wait_time_limit_reached(self):
        """
        Should report wait time approximately equal to expire after reaching
        the limit without delay between requests.
        """
        self.rate_limit = RateLimit(resource='test', client='localhost',
                                    max_requests=10, expire=1)
        self._make_10_requests()
        with self.assertRaises(TooManyRequests):
            with self.rate_limit:
                pass
        self.assertAlmostEqual(self.rate_limit.get_wait_time(), 1, places=2)

    def test_wait_time_limit_expired(self):
        """
        Should report wait time equal to expire / max_requests before any
        requests were made and after the limit has expired.
        """
        self.rate_limit = RateLimit(resource='test', client='localhost',
                                    max_requests=10, expire=1)
        self.assertEqual(self.rate_limit.get_wait_time(), 1./10)
        self._make_10_requests()
        time.sleep(1)
        self.assertEqual(self.rate_limit.get_wait_time(), 1./10)
    
    def test_context_manager_returns_usage(self):
        """
        Should return the usage when used as a context manager.
        """
        self.rate_limit = RateLimit(resource='test', client='localhost',
        max_requests=1, expire=1)
        with self.rate_limit as usage:
            self.assertEqual(usage, 1)

    def test_limit_10_using_as_decorator(self):
        """
        Should raise TooManyRequests Exception when trying to increment for the
        eleventh time.
        """
        self.assertEqual(self.rate_limit.get_usage(), 0)
        self.assertEqual(self.rate_limit.has_been_reached(), False)

        self._make_10_requests()
        self.assertEqual(self.rate_limit.get_usage(), 10)
        self.assertEqual(self.rate_limit.has_been_reached(), True)

        @self.rate_limit
        def limit_with_decorator():
            pass

        with self.assertRaises(TooManyRequests):
            limit_with_decorator()

        self.assertEqual(self.rate_limit.get_usage(), 11)
        self.assertEqual(self.rate_limit.has_been_reached(), True)

    def test_increment_multiple(self):
        """
        Test incrementing usage by a value > 1
        """
        self.rate_limit.increment_usage(7)
        self.rate_limit.increment_usage(3)

        self.assertEqual(self.rate_limit.get_usage(), 10)
        self.assertEqual(self.rate_limit.has_been_reached(), True)

        with self.assertRaises(TooManyRequests):
            self.rate_limit.increment_usage(1)

        self.assertEqual(self.rate_limit.get_usage(), 11)
        self.assertEqual(self.rate_limit.has_been_reached(), True)

        with self.assertRaises(TooManyRequests):
            self.rate_limit.increment_usage(5)

        self.assertEqual(self.rate_limit.get_usage(), 16)
        self.assertEqual(self.rate_limit.has_been_reached(), True)

    def test_increment_multiple_too_much(self):
        """
        Test that we cannot bulk-increment a value higher than
        the bucket limit.
        """
        with self.assertRaises(ValueError):
            self.rate_limit.increment_usage(11)

        self.assertEqual(self.rate_limit.get_usage(), 0)
        self.assertEqual(self.rate_limit.has_been_reached(), False)

    def test_increment_by_zero(self):
        """
        Should not allow increment by zero.
        """
        self.assertEqual(self.rate_limit.get_usage(), 0)
        self.assertEqual(self.rate_limit.has_been_reached(), False)

        self.rate_limit.increment_usage(5)
        self.assertEqual(self.rate_limit.get_usage(), 5)
        self.assertEqual(self.rate_limit.has_been_reached(), False)

        with self.assertRaises(ValueError):
            self.rate_limit.increment_usage(0)

        self.assertEqual(self.rate_limit.get_usage(), 5)
        self.assertEqual(self.rate_limit.has_been_reached(), False)

    def test_increment_by_negative(self):
        """
        Should not allow decrement the counter.
        """
        self.assertEqual(self.rate_limit.get_usage(), 0)
        self.assertEqual(self.rate_limit.has_been_reached(), False)
        with self.assertRaises(ValueError):
            self.rate_limit.increment_usage(-5)

        self.assertEqual(self.rate_limit.get_usage(), 0)
        self.assertEqual(self.rate_limit.has_been_reached(), False)


if __name__ == '__main__':
    unittest.main()
