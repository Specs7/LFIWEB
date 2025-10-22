import os
import sys
import importlib
import io


def load_app(tmp_path):
    db = tmp_path / "test.db"
    os.environ['DB_PATH'] = str(db)
    if 'backend.app' in sys.modules:
        del sys.modules['backend.app']
    import backend.app as appmod
    importlib.reload(appmod)
    appmod.init_db()
    return appmod


def test_send_magic_link_logs_when_no_smtp(tmp_path, caplog):
    appmod = load_app(tmp_path)
    # ensure SMTP not configured
    os.environ.pop('SMTP_HOST', None)
    # ensure caplog captures info-level logs
    caplog.set_level('INFO')
    sent = appmod.send_magic_link('user@example.test', 1, 'dummytoken')
    assert sent is True
    # should have an info log containing 'magic link'
    found = any('magic link' in r.getMessage().lower() for r in caplog.records)
    assert found
