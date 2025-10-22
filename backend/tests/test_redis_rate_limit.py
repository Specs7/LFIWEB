import os
import sys
import importlib


class DummyRedis:
    def __init__(self, eval_result=1):
        self.eval_result = eval_result
    def eval(self, *args, **kwargs):
        return self.eval_result


def load_app(tmp_path):
    db = tmp_path / "test.db"
    os.environ['DB_PATH'] = str(db)
    if 'backend.app' in sys.modules:
        del sys.modules['backend.app']
    import backend.app as appmod
    importlib.reload(appmod)
    appmod.init_db()
    return appmod


def test_redis_rate_limiter_allows_when_under_limit(tmp_path):
    appmod = load_app(tmp_path)
    # inject dummy redis client that returns a small count
    appmod._redis = DummyRedis(eval_result=1)
    limited = appmod.is_rate_limited_redis('testkey')
    assert limited is False


def test_redis_rate_limiter_blocks_when_over_limit(tmp_path):
    appmod = load_app(tmp_path)
    appmod._redis = DummyRedis(eval_result=appmod.RL_MAX_REQUESTS + 5)
    limited = appmod.is_rate_limited_redis('testkey')
    assert limited is True
