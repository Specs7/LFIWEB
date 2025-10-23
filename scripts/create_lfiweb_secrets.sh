#!/usr/bin/env bash
# Create a private secrets file for PythonAnywhere deployment
# Usage: run this on PythonAnywhere (or copy the heredoc contents) and then edit
# the placeholders in /home/DrancyInsoumis/.lfiweb_secrets before reloading the web app.

set -euo pipefail

SECRETS_PATH="/home/DrancyInsoumis/.lfiweb_secrets"

cat > "$SECRETS_PATH" <<'EOF'
DB_PATH=/home/DrancyInsoumis/DrancyInsoumis/data.db
SECRET_KEY=REPLACE_WITH_A_LONG_RANDOM_SECRET
SITE_URL=https://DrancyInsoumis.pythonanywhere.com
SESSION_COOKIE_SECURE=True

# SMTP (Gmail app password example) - replace SMTP_PASS with your App Password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<your-email@example.com>
SMTP_PASS=REPLACE_WITH_YOUR_APP_PASSWORD
FROM_EMAIL="LFIWEB <<your-email@example.com>>"
EOF

chmod 600 "$SECRETS_PATH"
echo "Created $SECRETS_PATH with permissions 600. Edit it to replace placeholders, then Reload your web app."
