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

