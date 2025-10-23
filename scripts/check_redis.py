#!/usr/bin/env python3
"""Check REDIS_URL connectivity and simple rate-limit sample."""
import os
REDIS_URL = os.getenv('REDIS_URL')
if not REDIS_URL:
    print('REDIS_URL not configured. Set REDIS_URL env var to test Redis connectivity.')
    raise SystemExit(0)
try:
    import redis
    r = redis.from_url(REDIS_URL)
    print('PING ->', r.ping())
    k = 'lfi_test_key'
    r.delete(k)
    r.zadd(k, { 'm1': 1 })
    print('ZCARD ->', r.zcard(k))
except Exception as e:
    print('Redis error:', e)
    raise
