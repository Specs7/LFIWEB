# LFIWEB smoke test and deployment notes

Quick notes and commands to run the project locally and on PythonAnywhere.

Requirements

- Python 3.10+
- Install repo requirements:

```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

Run the app locally

```bash
# From project root
export FLASK_APP=backend.app
export DB_PATH=$(pwd)/data.db
export SECRET_KEY="a secure secret"
flask run
```

Smoke-test runner (no external deps beyond Flask)

```bash
python3 backend/run_smoke.py
```

PythonAnywhere deployment notes

- Set WSGI entrypoint to `from backend.app import app`.
- Configure environment variables in the web UI: DB_PATH (path to data.db), SECRET_KEY, SITE_URL, SMTP_HOST/PORT/USER/PASS and FROM_EMAIL for magic-link emails.
- Add static files mapping: `/static/uploads/` -> `/home/<username>/LFIWEB/backend/static/uploads/`
