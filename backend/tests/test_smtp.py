import os
import sys
import importlib


class DummySMTP:
    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.tls = False
        self.logged_in = False
        self.sent = False
    def starttls(self):
        self.tls = True
    def login(self, user, pwd):
        if user == 'bad':
            raise Exception('auth failed')
        self.logged_in = True
    def send_message(self, msg):
        self.sent = True
    def quit(self):
        pass


def load_app(tmp_path):
    db = tmp_path / "test.db"
    os.environ['DB_PATH'] = str(db)
    if 'backend.app' in sys.modules:
        del sys.modules['backend.app']
    import backend.app as appmod
    importlib.reload(appmod)
    appmod.init_db()
    return appmod


def test_send_magic_link_via_smtp(tmp_path, monkeypatch):
    appmod = load_app(tmp_path)
    # configure SMTP env vars
    os.environ['SMTP_HOST'] = 'smtp.test'
    os.environ['SMTP_PORT'] = '2525'
    os.environ['SMTP_USER'] = 'user'
    os.environ['SMTP_PASS'] = 'pass'
    # patch smtplib.SMTP to our dummy
    import smtplib
    monkeypatch.setattr(smtplib, 'SMTP', DummySMTP)
    sent = appmod.send_magic_link('user@example.test', 10, 'token123')
    assert sent is True


def test_send_magic_link_smtp_auth_fail(tmp_path, monkeypatch):
    appmod = load_app(tmp_path)
    os.environ['SMTP_HOST'] = 'smtp.bad'
    os.environ['SMTP_PORT'] = '2525'
    os.environ['SMTP_USER'] = 'bad'
    os.environ['SMTP_PASS'] = 'bad'
    import smtplib
    monkeypatch.setattr(smtplib, 'SMTP', DummySMTP)
    sent = appmod.send_magic_link('user@example.test', 11, 'token123')
    # auth failure should be caught and return False
    assert sent is False
