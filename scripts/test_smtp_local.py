#!/usr/bin/env python3
"""Simple SMTP tester that uses the runtime environment variables.

Does not store any credentials. If SMTP vars are missing it prints the magic
link that would have been sent (app logs behavior matches this).
"""
import os
import smtplib
from email.message import EmailMessage
from urllib.parse import urlparse

SMTP_HOST = os.getenv('SMTP_HOST')
if not SMTP_HOST:
    print('SMTP_HOST not set. The app will log magic links instead of sending emails.')
    raise SystemExit(0)

SMTP_PORT = int(os.getenv('SMTP_PORT') or 587)
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', '1') not in ('0','false','False')
FROM_EMAIL = os.getenv('FROM_EMAIL', SMTP_USER or f"no-reply@{urlparse(os.getenv('SITE_URL','localhost')).hostname}")

def send_test(to_email):
    msg = EmailMessage()
    msg['Subject'] = 'LFIWEB SMTP test'
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email
    msg.set_content('This is a test email from LFIWEB.')
    s = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
    if SMTP_USE_TLS:
        s.starttls()
    if SMTP_USER and SMTP_PASS:
        s.login(SMTP_USER, SMTP_PASS)
    s.send_message(msg)
    s.quit()

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: test_smtp_local.py recipient@example.com')
        raise SystemExit(2)
    send_test(sys.argv[1])
    print('Email sent (or no exception raised).')
#!/usr/bin/env python3
"""Small helper to test SMTP sending using the project's send_magic_link helper.

Usage:
  export SMTP_HOST=... SMTP_PORT=... SMTP_USER=... SMTP_PASS=... SITE_URL=...
  python scripts/test_smtp_local.py you@example.test
"""
import sys
import importlib
import os

if len(sys.argv) < 2:
    print('Usage: test_smtp_local.py recipient@example.test')
    sys.exit(2)
recip = sys.argv[1]
# reload app module so it reads env vars at call time
if 'backend.app' in sys.modules:
    del sys.modules['backend.app']
import backend.app as appmod
importlib.reload(appmod)
print('Calling send_magic_link to', recip)
ok = appmod.send_magic_link(recip, 9999, 'localtesttoken')
print('send_magic_link returned', ok)

