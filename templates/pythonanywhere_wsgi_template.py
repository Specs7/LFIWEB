"""
Template: PythonAnywhere WSGI file that loads a private secrets file and starts the Flask app.

Copy the contents of this file into your PythonAnywhere WSGI file (e.g. /var/www/your_wsgi.py)
and ensure the `secrets_path` variable matches the location of the secrets file.

Do NOT commit your real secrets to git. Use the `create_lfiweb_secrets.sh` script on PythonAnywhere
to create the secrets file at `/home/DrancyInsoumis/.lfiweb_secrets` and set permissions to 600.
"""
import sys
import os

# --- Load secrets from private file -------------------------------------------------
secrets_path = '/home/DrancyInsoumis/.lfiweb_secrets'
if os.path.exists(secrets_path):
    with open(secrets_path, 'r') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            # Only set if not already present
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

# Fallback sane defaults (won't override secrets loaded above)
os.environ.setdefault('DB_PATH', '/home/DrancyInsoumis/DrancyInsoumis/data.db')
os.environ.setdefault('SITE_URL', 'https://DrancyInsoumis.pythonanywhere.com')
os.environ.setdefault('SESSION_COOKIE_SECURE', 'True')

# --- Add project to sys.path ------------------------------------------------------
project_home = '/home/DrancyInsoumis/DrancyInsoumis'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# If your app module is named `app.py` and exposes `app` (Flask), import it.
# Adjust the import below if your Flask application object is located elsewhere.
from app import app as application
