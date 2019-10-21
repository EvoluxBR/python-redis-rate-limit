import time

from redis_rate_limit import RateLimitBackend


class RedisCounter(object):
    def __init__(self, expire):
        self.counter = 0
        self.expire = expire
        self.ts = time.time()

    @property
    def ttl(self):
        if not self.expire:
            return -1

        ttl = (self.ts + self.expire - time.time()) * 1000
        return max(0, ttl)

    @property
    def expired(self):
        return self.ttl == 0

    def incr(self):
        self.counter += 1
        self.ts = time.time()


class MemoryBackend(RateLimitBackend):
    db = {}

    def __init__(self, redis_pool=None, expire=None):
        self._expire = expire

    def _get(self, key):
        if key not in self.db:
            return None

        value = self.db[key]
        if value.expired:
            self.delete(key)
            return None

        return value

    def get(self, key):
        value = self._get(key)
        if value:
            return value.counter
        return None

    def ttl(self, key):
        value = self._get(key)
        if value:
            return value.ttl
        return -2

    def incr(self, key):
        value = self._get(key)
        if not value:
            value = RedisCounter(self._expire)

        value.incr()
        self.db[key] = value
        return value.counter

    def scan(self, starts_with):
        return [k for k in self.db.keys() if k.startswith(starts_with)]

    def delete(self, key):
        del self.db[key]
