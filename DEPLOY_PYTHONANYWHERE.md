PythonAnywhere deployment checklist for LFIWEB

1) Files and WSGI
- Upload your project to PythonAnywhere (via git clone, upload zip, or SFTP) into `/home/<yourusername>/LFIWEB`.
- Ensure `backend` is present and `backend/app.py` is the Flask app.
- WSGI configuration (in the PythonAnywhere Web tab, edit the WSGI file): add/import the app:

  Replace the WSGI file contents or add near the top:

  from os import environ, path
  import sys
  # add project root to sys.path
  project_home = '/home/<yourusername>/LFIWEB'
  if project_home not in sys.path:
      sys.path.insert(0, project_home)

  # set env vars here if you prefer; otherwise set them in the Web UI
  environ['DB_PATH'] = path.join(project_home, 'data.db')
  environ['SECRET_KEY'] = 'replace-with-a-secure-secret'
  # environ['SITE_URL'] = 'https://<yourusername>.pythonanywhere.com'

  from backend.app import app as application

  Note: PythonAnywhere expects the WSGI callable to be named `application`.

# PythonAnywhere deployment checklist for LFIWEB

This document contains step-by-step, copy-paste friendly instructions to get the Flask app in `backend/app.py` running on PythonAnywhere.

## 0) Prep: push code to GitHub / upload to PythonAnywhere
- Put the project in `/home/<yourusername>/LFIWEB` on PythonAnywhere by one of:
  - git clone your repo on the PythonAnywhere Bash console
  - Upload a zip via the web UI and extract it into your home directory
  - SFTP / scp

## 1) Create a virtualenv & install requirements (recommended)
Open a Bash console on PythonAnywhere and run (use Python 3.10+ if available):

```bash
cd /home/<yourusername>/LFIWEB
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r backend/requirements.txt
```

If you prefer the system interpreter you may skip the venv step, but virtualenv is recommended.

## 2) WSGI configuration (Web tab -> WSGI file)
Edit the WSGI file from the PythonAnywhere Web tab and replace or add the following near the top. This makes the project importable and sets a couple of safe default env vars.

```python
import os
import sys
from os import path, environ

project_home = '/home/<yourusername>/LFIWEB'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Optional: set lightweight defaults here. Prefer setting secrets in the Web UI environment variables.
environ.setdefault('DB_PATH', path.join(project_home, 'data.db'))
environ.setdefault('SECRET_KEY', 'replace-this-with-a-strong-secret')
# environ.setdefault('SITE_URL', 'https://<yourusername>.pythonanywhere.com')

# Activate virtualenv if you created one
activate_this = path.join(project_home, '.venv', 'bin', 'activate_this.py')
if path.exists(activate_this):
    # old-style activation file may not exist; the virtualenv will still work if you select it in Web UI
    try:
        with open(activate_this) as f:
            exec(f.read(), {'__file__': activate_this})
    except Exception:
        pass

from backend.app import app as application

# PythonAnywhere expects the WSGI callable to be named `application`.
```

Notes:
- For the virtualenv, it's usually easier to point the Web -> Virtualenv setting to `/home/<yourusername>/LFIWEB/.venv` rather than trying to activate it inside the WSGI file.

## 3) Environment variables (Web -> Environment Variables)
In the PythonAnywhere Web tab set the following environment variables (minimum):

- DB_PATH=/home/<yourusername>/LFIWEB/data.db
- SECRET_KEY=(a long random secret)
- SITE_URL=https://<yourusername>.pythonanywhere.com

Optional (email / quotas / rate limiting):

- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL (for magic-link email delivery)
- SMTP_USE_TLS=1 (or 0)
- REDIS_URL (if you provision a Redis instance and want centralized rate-limiting)
- IMAGE_MAX_BYTES, VIDEO_MAX_BYTES, MAX_TOTAL_UPLOAD_BYTES (override defaults if you need smaller/larger quotas)
- RL_WINDOW_SECONDS, RL_MAX_REQUESTS (rate-limit tuning)

Security note: never commit SECRET_KEY or SMTP secrets into git. Use the Web UI env panel.

## 4) Static files mapping
In the Web tab add a static files mapping so uploaded files can be served directly by PythonAnywhere (faster than via Flask):

- URL: /static/uploads/
- Directory: /home/<yourusername>/LFIWEB/backend/static/uploads/

Also make sure `/static/admin.css` (and any other static assets in `backend/static/`) are reachable from the Web tab settings if needed.

## 5) Initialize the database & create an admin
Open a Bash console on PythonAnywhere (in the same virtualenv if you created one) and run:

```bash
cd /home/<yourusername>/LFIWEB
source .venv/bin/activate   # only if you created a venv
python3 -c "from backend.app import init_db; init_db()"

# Create an admin user interactively (script included in the repo):
python3 backend/create_admin.py

# Alternatively create a single admin by piping an email or running a short snippet:
python3 - <<'PY'
from backend.app import get_db
db = get_db()
db.execute("INSERT OR IGNORE INTO users (email,is_admin) VALUES (?,1)", ('admin@example.com',))
db.commit()
print('created admin admin@example.com')
PY
```

The `create_admin.py` helper is provided to make it easier; using the short snippet above creates a single admin row in the DB.

## 6) File permissions & disk quota
- Uploaded files will be stored under `backend/static/uploads/photos/` and `backend/static/uploads/videos/`.
- Files in your home directory are owned by your account and writable by the web app. If you run into permission problems, ensure the owner is your user.
- Watch PythonAnywhere storage quotas for video-heavy sites. Use `MAX_TOTAL_UPLOAD_BYTES` to limit combined usage.

## 7) Email (magic-link) verification
- If you set SMTP env vars, `send_magic_link` in `backend/app.py` will attempt to send emails. Use an App Password for Gmail.
- To test email sending from the PythonAnywhere console:

```bash
cd /home/<yourusername>/LFIWEB
source .venv/bin/activate
python3 scripts/test_smtp_local.py
```

If SMTP is not configured the app will log the magic link to the error log for manual use.

## 8) Health & rate-limiting
- If you configure `REDIS_URL` the app will use Redis for rate-limiting `/auth/request-token`.
- Use the `/admin/status` endpoint (admin only) to inspect storage usage and Redis connectivity.

## 9) Logs and debugging
- Check the Web -> Error log and Access log in PythonAnywhere for startup and runtime errors.
- If your app fails to start, the error log will contain the traceback. Common causes: wrong `SECRET_KEY` format, missing dependencies, wrong `DB_PATH`.

## 10) Restart & sanity check
- After setting the WSGI file and environment variables restart the web app from the PythonAnywhere Web tab.
- Try:

```bash
curl -i "https://<yourusername>.pythonanywhere.com/"
# or open in a browser
```

Then request a magic link (POST /auth/request-token) or use the admin UI to confirm the site works end-to-end.

## 11) Production hardening (recommended)
- Use HTTPS (PythonAnywhere provides HTTPS on your .pythonanywhere.com domain).
- Set a strong `SECRET_KEY` and rotate it only if you also re-issue sessions.
- Limit upload sizes using `IMAGE_MAX_BYTES`, `VIDEO_MAX_BYTES` and `MAX_TOTAL_UPLOAD_BYTES`.
- Provision Redis (e.g., Redis Cloud or a managed provider) and set `REDIS_URL` if you need global rate-limiting across multiple worker processes.
- Consider moving large video files to object storage (S3, Backblaze B2) if you expect high volume.

If you'd like, I can prepare a sample `pythonanywhere-wsgi.conf` file or create a small one-line script you can paste into the Web tab WSGI editor.

---

That’s it — after setting up WSGI and env vars restart the web app from the PythonAnywhere Web tab.
