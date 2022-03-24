python-redis-rate-limit
=======================
.. image:: https://github.com/EvoluxBR/python-redis-rate-limit/actions/workflows/python-package.yml/badge.svg
    :target: https://github.com/EvoluxBR/python-redis-rate-limit/actions/workflows/python-package.yml

.. image:: https://img.shields.io/pypi/v/python-redis-rate-limit.svg
    :target: https://pypi.python.org/pypi/python-redis-rate-limit

.. image:: https://img.shields.io/pypi/dm/python-redis-rate-limit.svg
    :target: https://pypi.python.org/pypi/python-redis-rate-limit


This lib offers an abstraction of a Rate Limit algorithm implemented on top of
Redis >= 2.6.0.

Supported Python Versions: 2.7, 3.5+

Example: 10 requests per second

.. code-block:: python

    from redis_rate_limit import RateLimit, TooManyRequests
    try:
      with RateLimit(resource='users_list', client='192.168.0.10', max_requests=10):
        return '200 OK'
    except TooManyRequests:
      return '429 Too Many Requests'

Example: using as a decorator

.. code-block:: python

    from redis_rate_limit import RateLimit, TooManyRequests

    @RateLimit(resource='users_list', client='192.168.0.10', max_requests=10)
    def list_users():
      return '200 OK'

    try:
      return list_users()
    except TooManyRequests:
      return '429 Too Many Requests'

Example: 600 requests per minute

.. code-block:: python

    from redis_rate_limit import RateLimit, TooManyRequests
    try:
      with RateLimit(resource='users_list', client='192.168.0.10', max_requests=600, expire=60):
        return '200 OK'
    except TooManyRequests:
      return '429 Too Many Requests'

Example: 100 requests per hour

.. code-block:: python

    from redis_rate_limit import RateLimit, TooManyRequests
    try:
      with RateLimit(resource='users_list', client='192.168.0.10', max_requests=100, expire=3600):
        return '200 OK'
    except TooManyRequests:
      return '429 Too Many Requests'

Example: you can also setup a factory to use it later

.. code-block:: python

    from redis_rate_limit import RateLimiter, TooManyRequests
    limiter = RateLimiter(resource='users_list', max_requests=100, expire=3600)
    try:
      with limiter.limit(client='192.168.0.10'):
        return '200 OK'
    except TooManyRequests:
      return '429 Too Many Requests'

Example: you can also pass an optional Redis Pool

.. code-block:: python

    import redis
    from redis_rate_limit import RateLimit, TooManyRequests
    redis_pool = redis.ConnectionPool(host='127.0.0.1', port=6379, db=0)
    try:
      with RateLimit(resource='users_list', client='192.168.0.10', max_requests=10, redis_pool=redis_pool):
        return '200 OK'
    except TooManyRequests:
      return '429 Too Many Requests'
