python-redis-rate-limit
=======================

.. image:: https://travis-ci.org/EvoluxBR/python-redis-rate-limit.svg?branch=master
    :target: https://travis-ci.org/EvoluxBR/python-redis-rate-limit

.. image:: https://img.shields.io/pypi/v/python-redis-rate-limit.svg
    :target: https://pypi.python.org/pypi/python-redis-rate-limit


This lib offers an abstraction of a Rate Limit algorithm implemented on top of
Redis >= 2.6.0.

Example: 10 requests per second

.. code-block:: python

    >>> from redis_rate_limit import RateLimit, TooManyRequests
    >>> try:
    >>>   with RateLimit(resource='users_list', client='192.168.0.10', max_requests=10):
    >>>     return '200 OK'
    >>> except TooManyRequests:
    >>>   return '429 Too Many Requests'
    >>>

Example: 600 requests per minute

.. code-block:: python

    >>> from redis_rate_limit import RateLimit, TooManyRequests
    >>> try:
    >>>   with RateLimit(resource='users_list', client='192.168.0.10', max_requests=600, expire=60):
    >>>     return '200 OK'
    >>> except TooManyRequests:
    >>>   return '429 Too Many Requests'
    >>>

Example: 100 requests per hour

.. code-block:: python

    >>> from redis_rate_limit import RateLimit, TooManyRequests
    >>> try:
    >>>   with RateLimit(resource='users_list', client='192.168.0.10', max_requests=100, expire=3600):
    >>>     return '200 OK'
    >>> except TooManyRequests:
    >>>   return '429 Too Many Requests'
    >>>
