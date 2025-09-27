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
project_home = '/home/yourusername/<your-repo>'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Optionally set environment variables here (you can also set them in the Web > Environment variables UI)
# os.environ['DB_PATH'] = '/home/yourusername/<your-repo>/backend/data.db'
# os.environ['SECRET_KEY'] = 'replace-with-a-secure-secret'
# os.environ['SITE_URL'] = 'https://yourusername.pythonanywhere.com'

from backend.app import app as application

```

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

Notes & recommendations

- For production use a proper managed DB (Postgres/MySQL) instead of SQLite when you expect concurrency or larger scale.
- Protect your `SECRET_KEY` and other secrets using the PythonAnywhere environment variables UI.
- Configure log rotation and backups for your `data.db` if you keep using SQLite.

If you want, I can add:
- a sample `.env.example` for local dev,
- a Dockerfile and docker-compose for local testing,
- or a sample Gunicorn systemd unit and nginx proxy instructions for VPS deployment.

Tell me which of those you want next and I'll add it.
