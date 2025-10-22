# Deploy to PythonAnywhere (step-by-step)

This short guide walks you through deploying the LFIWEB Flask app to PythonAnywhere.

Prerequisites
- A PythonAnywhere account (free for small/demo apps). Sign up at https://www.pythonanywhere.com
- Your project repository available on GitHub, or a way to upload the project files to PythonAnywhere (upload via the web dashboard or use the console and git clone).

Overview of steps
1. Upload or clone the repository to your PythonAnywhere home directory.
2. Create and activate a virtualenv and install dependencies.
3. Configure the Web app (WSGI file, virtualenv path, static files mapping, environment variables).
4. Initialize the SQLite DB and create an admin user.
5. Reload the web app and test.
 
Quick PythonAnywhere checklist

- WSGI: make sure the `project_home` in your WSGI file points to `/home/DrancyInsoumis/DrancyInsoumis` and that the WSGI imports your app.
- DB: set `DB_PATH` in Web → Environment variables to `/home/DrancyInsoumis/DrancyInsoumis/data.db`.
- SITE_URL: set `SITE_URL` to `https://DrancyInsoumis.pythonanywhere.com` so magic-links and redirects use the public domain (not localhost).
- Static mapping: point `/static/` to `/home/DrancyInsoumis/DrancyInsoumis/static` (or `/home/DrancyInsoumis/DrancyInsoumis/backend/static` if you keep a `backend` folder).
- Virtualenv: set the Virtualenv path to `/home/DrancyInsoumis/.virtualenvs/lfiweb-venv`.

Detailed steps

1) Upload/clone the repo

- Using the PythonAnywhere dashboard: go to the Files tab and upload a zip of your repo, then unzip it.
- Or open a Bash console on PythonAnywhere and run (if your repo is on GitHub):

  git clone https://github.com/<yourname>/<your-repo>.git
  cd <your-repo>

2) Create a virtualenv and install deps

Open a Bash console on PythonAnywhere and run:

  # choose a Python version available on PA (e.g. 3.10)
  python3.10 -m venv ~/.virtualenvs/lfiweb-venv
  source ~/.virtualenvs/lfiweb-venv/bin/activate
  pip install --upgrade pip
  pip install -r backend/requirements.txt

3) Create the Web app in PythonAnywhere

- In the PythonAnywhere dashboard go to the Web tab and click "Add a new web app".
- Choose Manual configuration -> Python 3.10 (or the Python version you used above).
- Set the Source code directory to the repository folder (for example `/home/yourusername/<your-repo>`).
- Set the Virtualenv path to `/home/yourusername/.virtualenvs/lfiweb-venv` (or whichever path you created).

4) Edit the WSGI configuration

Open the WSGI file linked in the Web tab (it opens an editor). Replace its contents (or add) with the snippet below. Adjust `yourusername` and the repo path accordingly.

```python
# WSGI configuration snippet for PythonAnywhere
import sys, os

# add project root to sys.path
project_home = '/home/DrancyInsoumis/DrancyInsoumis'
if project_home not in sys.path:
  sys.path.insert(0, project_home)

# If your app module is at project root (app.py) import it; otherwise adjust the import
# For this project app.py lives at /home/DrancyInsoumis/DrancyInsoumis/app.py
from app import app as application

```

Exact WSGI file (ready to paste)

```python
import sys, os

project_home = '/home/DrancyInsoumis/DrancyInsoumis'
if project_home not in sys.path:
  sys.path.insert(0, project_home)

# Temporary overrides are sometimes useful while debugging but prefer the Web UI for permanent values
# os.environ.setdefault('DB_PATH', '/home/DrancyInsoumis/DrancyInsoumis/data.db')
# os.environ.setdefault('SECRET_KEY', 'replace-with-a-long-secret')
# os.environ.setdefault('SITE_URL', 'https://DrancyInsoumis.pythonanywhere.com')

from app import app as application
```

Optional: automatic WSGI updater script

If you prefer to update the PythonAnywhere WSGI file from a console instead of editing the Web UI editor, there's a helper script in `scripts/update_pa_wsgi.sh` you can run on the PythonAnywhere Bash console. It will back up the existing WSGI file and write a WSGI that loads a private secrets file and imports `backend.app` as the Flask application.

Example (run on PythonAnywhere):

```bash
# replace the path below with the WSGI file path shown in your Web tab
bash scripts/update_pa_wsgi.sh /var/www/yourusername_pythonanywhere_com_wsgi.py /home/yourusername/yourrepo /home/yourusername/.lfiweb_secrets
```

The script arguments are: WSGI_PATH [project_home] [secrets_path]. If you omit the last two it uses sensible defaults for the repository layout used in this guide.


Exact environment variables to add in Web → Environment variables

Key (name)        | Value
------------------|-----------------------------------------------
DB_PATH           | /home/DrancyInsoumis/DrancyInsoumis/data.db
SECRET_KEY        | (paste the long secret you generated)
SITE_URL          | https://DrancyInsoumis.pythonanywhere.com
SESSION_COOKIE_SECURE | True

Paste those four entries exactly into the Web tab → Environment variables, then click Reload.


Important: prefer setting sensitive environment variables using the Web tab (Environment variables) instead of hardcoding them here.

5) Configure static files mapping

In the Web tab, add a Static files mapping:

- URL: /static/
- Directory: `/home/yourusername/<your-repo>/backend/static`

This lets nginx on PythonAnywhere serve CSS/JS/images efficiently.

6) Environment variables

Open the Web tab -> Environment variables and add at minimum:

- DB_PATH = `/home/yourusername/<your-repo>/backend/data.db`  (if using SQLite)
- SECRET_KEY = (a long random secret)
- SITE_URL = `https://yourusername.pythonanywhere.com`
- SESSION_COOKIE_SECURE = True
- (Optional) SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, FROM_EMAIL if you want real emails

7) Initialize the DB and create an admin

Open a Bash console (use the virtualenv) and run:

  source ~/.virtualenvs/lfiweb-venv/bin/activate
  python -c "from backend.app import init_db; init_db()"

Then create an admin user (interactive script):

  python backend/create_admin.py

Alternatively insert a user manually via a Python one-liner if desired.

8) Reload the web app

Go back to the Web tab and click the "Reload" button for your web app. Then visit `https://yourusername.pythonanywhere.com`.

Testing the magic-link flow

- Request a magic link (locally or via curl):
  curl -X POST -H "Content-Type: application/json" -d '{"email":"admin@example.com"}' https://yourusername.pythonanywhere.com/auth/request-token
- If SMTP is configured, the email will be sent. If not, the app logs the magic-link; check the error/logs on PythonAnywhere (Error log or access the server log file if you wrote one).

Troubleshooting

- Check the Error log in the Web tab for import errors, missing packages, or WSGI exceptions.
- If static files 404, verify your static mapping points to `backend/static` and you reloaded the web app.
- If the CSRF token is missing or session doesn't persist, ensure `SITE_URL` is set to your public URL and `SESSION_COOKIE_SECURE` matches your TLS usage.
- For issues sending email, configure SMTP env vars or use an external provider (SendGrid/Mailgun) and update `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL`.

PythonAnywhere-specific gotchas

- Static file mapping must point to a directory (for example `/home/yourusername/<your-repo>/static` or `/home/yourusername/<your-repo>/backend/static`). Do NOT point the Static mapping to your `data.db` file. Example mapping:

  URL: /static/
  Directory: /home/yourusername/<your-repo>/backend/static

- Environment variables used by your WSGI process must be set in the Web tab → Environment variables (or set in the WSGI file). Exports done in a Bash console are not visible to the WSGI process.

- SITE_URL controls URLs generated by the app (magic links and redirects). If `SITE_URL` is missing you'll see URLs with `http://localhost:5000/...` in the logs. Set:

  SITE_URL = https://yourusername.pythonanywhere.com

- DB_PATH must point to the exact SQLite file used by your WSGI process. Common mistake: the console and WSGI use different working directories and therefore different DB files. Example:

  DB_PATH = /home/yourusername/<your-repo>/data.db

- While debugging you may temporarily set `os.environ['DB_PATH']` and `os.environ['SECRET_KEY']` in the WSGI file to force the correct values — but remove those overrides once you have added the values to Web → Environment variables.

- Requesting the directory URL `/static/` may return 404 (most servers do not serve a directory index); always test specific asset paths such as `/static/css/main.css` to verify the static mapping.

- Magic links: if SMTP is not configured the app logs the magic link in `server.log` under "Mail contents:". After you set `SITE_URL` re-request a magic link; the next logged link should begin with your public domain.

Notes & recommendations

- For production use a proper managed DB (Postgres/MySQL) instead of SQLite when you expect concurrency or larger scale.
- Protect your `SECRET_KEY` and other secrets using the PythonAnywhere environment variables UI.
- Configure log rotation and backups for your `data.db` if you keep using SQLite.

If you want, I can add:
- a sample `.env.example` for local dev,
- a Dockerfile and docker-compose for local testing,
- or a sample Gunicorn systemd unit and nginx proxy instructions for VPS deployment.

Tell me which of those you want next and I'll add it.
