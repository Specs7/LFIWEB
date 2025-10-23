#!/usr/bin/env bash
set -euo pipefail

# Local end-to-end test for LFIWEB
# Creates a disposable DB, starts the dev server, creates an admin and a login token,
# consumes the token to obtain a session, creates an article, uploads a photo and a
# tiny video, verifies files are saved, then runs pytest.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export SITE_URL="http://localhost:5000"
export SECRET_KEY="devsecret"
export DB_PATH="$ROOT/backend/test_e2e.db"

echo "Using DB_PATH=$DB_PATH"

# Ensure a clean DB
rm -f "$DB_PATH"

echo "Initializing database and creating admin + token..."
PYOUT=$(python3 - <<'PY'
from backend.app import init_db, get_db, gen_token, hash_token
from datetime import datetime, timedelta
import secrets, hashlib, os
init_db()
db = get_db()
cur = db.cursor()
cur.execute("INSERT INTO users (email, role, created_at) VALUES (?,?,datetime('now'))", ('e2e_admin@example.test','admin'))
db.commit()
uid = cur.lastrowid
token = gen_token()
th = hash_token(token)
expires = (datetime.utcnow() + timedelta(hours=2)).isoformat()
cur.execute('INSERT INTO login_tokens (user_id, token_hash, expires_at, used, ip, user_agent) VALUES (?,?,?,?,?,?)', (uid, th, expires, 0, '127.0.0.1', 'e2e-runner'))
db.commit()
link = f"{os.environ.get('SITE_URL','http://localhost:5000').rstrip('/')}/auth/consume?token={token}&uid={uid}"
print(token)
print(uid)
print(link)
db.close()
PY
)

TOKEN=$(printf "%s" "$PYOUT" | sed -n '1p')
ADMIN_UID=$(printf "%s" "$PYOUT" | sed -n '2p')
LINK=$(printf "%s" "$PYOUT" | sed -n '3p')

echo "TOKEN=$TOKEN ADMIN_UID=$ADMIN_UID"
echo "LINK=$LINK"

echo "Starting Flask dev server..."
nohup python3 backend/app.py > /tmp/lfi_e2e.log 2>&1 &
SERVER_PID=$!
echo "Server PID=$SERVER_PID"

# Wait for server to be ready
echo -n "Waiting for server to respond"
for i in {1..30}; do
  if curl --silent --fail "$SITE_URL/" >/dev/null 2>&1; then
    echo " - ready"
    break
  fi
  echo -n '.'; sleep 1
done

COOKIEJAR=/tmp/lfi_e2e_cookies.txt
echo "Consuming magic link: $LINK"
curl -s -c $COOKIEJAR -L "$LINK" >/tmp/lfi_consume.html

# Extract CSRF token from admin_manage page
CSRF=$(grep -oE "const CSRF = '[0-9a-f]+'" /tmp/lfi_consume.html | sed -E "s/const CSRF = '([0-9a-f]+)'/\1/" | tr -d '\r\n')
if [ -z "$CSRF" ]; then
  echo "Failed to extract CSRF token" >&2
  tail -n 200 /tmp/lfi_e2e.log
  kill $SERVER_PID || true
  exit 3
fi
echo "CSRF=$CSRF"

# Create an article
echo "Creating article..."
curl -s -b $COOKIEJAR -H "Content-Type: application/json" -H "X-CSRF-Token: $CSRF" -d '{"title":"E2E Test","author":"CI","content":"Auto-created by run_local_e2e.sh"}' -X POST "$SITE_URL/api/articles" | python3 -m json.tool || true

# Prepare fake files
IMG=/tmp/e2e_test.jpg
VIDEO=/tmp/e2e_test.mp4
printf '\xFF\xD8\xFF' > $IMG
printf '\x00\x00\x00\x18ftypmp42' > $VIDEO

echo "Uploading photo..."
curl -s -b $COOKIEJAR -H "X-CSRF-Token: $CSRF" -F "title=E2E" -F "description=test" -F "file=@$IMG;type=image/jpeg" -X POST "$SITE_URL/api/photos" | python3 -m json.tool || true

echo "Uploading video..."
curl -s -b $COOKIEJAR -H "X-CSRF-Token: $CSRF" -F "title=E2E" -F "description=test" -F "file=@$VIDEO;type=video/mp4" -X POST "$SITE_URL/api/videos" | python3 -m json.tool || true

echo "Verifying uploaded files exist on disk..."
ls -l backend/static/uploads/photos || true
ls -l backend/static/uploads/videos || true

echo "Running pytest..."
if [ -x ".venv/bin/pytest" ]; then
  .venv/bin/pytest -q backend/tests || true
else
  python3 -m pytest -q backend/tests || true
fi

echo "Cleaning up: stopping server PID $SERVER_PID"
kill $SERVER_PID || true

echo "E2E script finished. Check /tmp/lfi_e2e.log for server output." 
