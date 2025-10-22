#!/usr/bin/env bash
# Update the PythonAnywhere WSGI file to import backend.app and load private secrets.
# Usage (on PythonAnywhere):
#   bash update_pa_wsgi.sh /var/www/your_wsgi_file.py
# Example for this project on PA:
#   bash update_pa_wsgi.sh /var/www/drancyinsoumis_pythonanywhere_com_wsgi.py

set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 3 ]; then
  echo "Usage: $0 /var/www/your_wsgi_file.py [project_home] [secrets_path]"
  echo "Example: $0 /var/www/your_wsgi_file.py /home/yourusername/yourrepo /home/yourusername/.lfiweb_secrets"
  exit 1
fi

WSGI_PATH="$1"
PROJECT_HOME="${2:-/home/DrancyInsoumis/DrancyInsoumis}"
SECRETS_PATH="${3:-/home/DrancyInsoumis/.lfiweb_secrets}"

if [ ! -e "$WSGI_PATH" ]; then
  echo "Warning: $WSGI_PATH does not exist. The script will still create it if writable."
fi

BACKUP_DIR="/home/$(whoami)/wsgi_backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
if [ -e "$WSGI_PATH" ]; then
  cp "$WSGI_PATH" "$BACKUP_DIR/$(basename $WSGI_PATH).$TIMESTAMP.bak"
  echo "Backed up existing WSGI to $BACKUP_DIR/$(basename $WSGI_PATH).$TIMESTAMP.bak"
fi

cat > "$WSGI_PATH" <<PY
import sys, os

# Load private secrets file if present
secrets_path = '${SECRETS_PATH}'
if os.path.exists(secrets_path):
    with open(secrets_path, 'r') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

# sane defaults (won't override loaded secrets)
os.environ.setdefault('DB_PATH', '${PROJECT_HOME}/data.db')
os.environ.setdefault('SITE_URL', 'https://${USER:-yourusername}.pythonanywhere.com')
os.environ.setdefault('SESSION_COOKIE_SECURE', 'True')

# add project root to sys.path
project_home = '${PROJECT_HOME}'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import the backend Flask app (adjust if your app location differs)
from backend.app import app as application
PY

chmod 644 "$WSGI_PATH" || true
echo "Wrote new WSGI to $WSGI_PATH. project_home=$PROJECT_HOME secrets_path=$SECRETS_PATH"
echo "A backup of the previous file (if any) was stored in $BACKUP_DIR"
echo "Go to the PythonAnywhere Web tab and click Reload to apply the changes."
