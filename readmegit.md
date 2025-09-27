# LFIWEB — Quick run & deploy (short)

This short `readmegit.md` contains the minimal steps to run the project locally, test it, and common pointers for quick deployments. Place in the repository root and push when ready.

## Quick local setup (Linux)

1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies

```bash
pip install -r backend/requirements.txt
```

3. Initialize the SQLite database

```bash
# from project root
python -c "from backend.app import init_db; init_db()"
```

4. Run the dev server

```bash
# runs on http://127.0.0.1:5000
python backend/app.py
```

Notes
- In development, if SMTP is not configured, magic links are logged to `backend/server.log`.
- Default DB path is `data.db` in the project root; change via `DB_PATH` env var.

## Admin / magic-link flow (dev)

1. Request a magic link (replace email):

```bash
curl -X POST -H "Content-Type: application/json" -d '{"email":"admin@example.com"}' http://localhost:5000/auth/request-token
```

2. If SMTP is not configured, open the logged link found in `backend/server.log` to verify and set the session cookie.

3. On successful verify the server sets a session + CSRF token visible in the page meta tag. Use that CSRF token for POST/PUT/DELETE requests as `X-CSRF-Token`.

## Run tests

```bash
# from project root
.venv/bin/pytest -q backend/tests
```

## Quick production notes

- Use a real SECRET_KEY and set `SESSION_COOKIE_SECURE=true` and proper env vars for SMTP and DB.
- For a small deployment, use gunicorn behind nginx or a platform like PythonAnywhere.

Example `gunicorn` start (systemd or Docker):

```bash
# run from project root
gunicorn -w 4 -b 127.0.0.1:8000 backend.app:app
```

- Consider moving from SQLite to PostgreSQL for production if you expect concurrent writes.
- Ensure HTTPS termination at the reverse proxy (nginx or platform) and configure SMTP credentials.

## Pushing to GitHub (local -> remote)

If you already created a GitHub repo named `LFIWEB`, push with:

```bash
cd /home/achil/LFIWEB
git init
git add .
git commit -m "Initial commit"
git branch -M main
# SSH remote example
git remote add origin git@github.com:USERNAME/LFIWEB.git
git push -u origin main
```

Or use the GitHub CLI:

```bash
gh repo create USERNAME/LFIWEB --public --source=. --remote=origin --push
```

Replace `USERNAME` and visibility as needed.

---

If you want this file to be used as the project's README on GitHub instead of `README.md`, tell me and I will move/rename it to `README.md` before you push.
