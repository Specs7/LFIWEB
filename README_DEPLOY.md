# LFIWEB — Run, Deploy & Changelog

This file explains how to run the project locally, recommended deployment steps, and a detailed changelog of edits made during the integration of the Flask backend and admin features.

## Quick start (development)

1. Create and activate a virtual environment:

   python3 -m venv .venv
   source .venv/bin/activate

2. Install dependencies for the backend:

   pip install -r backend/requirements.txt

3. Initialize the database and create an admin (interactive):

   # initialize DB
   python -c "from backend.app import init_db; init_db()"

   # create admin (interactive script)
   python backend/create_admin.py

4. Run the development server (dev mode):

   python backend/app.py

   The app runs on http://0.0.0.0:5000 by default. For production, use a WSGI server.

5. Admin login (passwordless magic-link):

   - Request a magic link:
     curl -X POST -H "Content-Type: application/json" -d '{"email":"admin@example.com"}' http://localhost:5000/auth/request-token
   - If SMTP is not configured the server logs the magic link in `backend/server.log`.
   - Visit the logged URL or open it in the browser to set the session cookie.

## Running tests

With the virtualenv activated and dependencies installed run:

   pytest -q backend/tests

Tests use an ephemeral SQLite DB and mock session CSRF token where needed.

## Deploying to production (recommended checklist)

- Use Gunicorn or another WSGI server (do not use the Flask dev server).
- Serve behind a reverse proxy (nginx) with TLS (Let's Encrypt).
- Set environment variables:
  - `SECRET_KEY` — a secure random value
  - `DB_PATH` — path to your production SQLite file or a real DB
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `FROM_EMAIL` — for magic-link emails
  - `SITE_URL` — public URL for magic-link generation
  - `SESSION_COOKIE_SECURE=True` in production
- Consider replacing SQLite with PostgreSQL for higher reliability.
- Enable proper logging, backups, and monitoring.

## Security notes

- CSRF protection: server sets a `session['csrf_token']` after magic-link verify and the frontend sends it via `X-CSRF-Token` header for state-changing requests.
- Tokens are hashed (SHA-256) in the DB and are single-use with expiry.
- Basic security headers and a CSP are set in responses. Harden CSP further for production.

## Changelog — edits performed

All edits were made in the workspace to integrate a Flask backend, admin flows, and security improvements. Below is a chronological summary of what was added/changed.

- Added backend package and server
  - `backend/app.py` — main Flask app with endpoints:
    - POST `/auth/request-token` — request magic link
    - GET `/admin/verify` — verify token and set session + CSRF token
    - GET `/admin` and `/admin/request` — admin pages
    - GET `/api/articles` — list articles
    - POST `/api/articles` — create article (admin + CSRF)
    - PUT `/api/articles/<id>` — update article (admin + CSRF)
    - DELETE `/api/articles/<id>` — delete article (admin + CSRF)
    - GET `/api/me` — returns current user info
  - Implemented DB initialization (users, login_tokens, articles) in `init_db()`.
  - Implemented `send_mail()` with SMTP fallback to server log when SMTP not configured.

- Frontend integration
  - `backend/templates/lfi_municipal_site.html` — template serving the frontend and exposing CSRF token via a meta tag when set in session.
  - `backend/static/css/main.css` — extracted styles, added modal styles.
  - `backend/static/js/main.js` — frontend logic to fetch articles, show admin panel when `/api/me` indicates admin, create/update/delete articles using the JSON API and CSRF header.
  - Replaced dangerous innerHTML usage with safe DOM creation and `escapeHtml()`.

- Admin UX improvements
  - Implemented an admin panel that is shown when the logged user is admin.
  - Added a modal-based article editor instead of prompt-based edits.

- Security improvements
  - Tokens stored as SHA-256 hashes, single-use, expiry.
  - CSRF protection by storing csrf token in session and requiring `X-CSRF-Token` header on state-changing endpoints.
  - Basic security headers and Content-Security-Policy added in `after_request`.
  - Server-side validation for article inputs (lengths and safe image URL checks) and rate limits on token issuance.

- Tests
  - `backend/tests/test_articles.py` — pytest suite exercising article CRUD with a test DB and session CSRF token.
  - `backend/requirements.txt` — pytest added.

- Misc
  - `backend/__init__.py` — exposes app, init_db, get_db for imports/tests.
  - `backend/create_admin.py` — helper to create admin users (existing in repo).

## Files added/changed (concise)

- Added: `README_DEPLOY.md` (this file)
- Changed: `backend/app.py`, `backend/__init__.py`, `backend/templates/lfi_municipal_site.html`, `backend/static/js/main.js`, `backend/static/css/main.css`, `backend/tests/test_articles.py`, `backend/requirements.txt`

## Next recommended tasks

- Add SMTP configuration and a reliable email provider for production.
- Implement image upload handling and store media in S3 or similar.
- Add more tests for auth flows (token expiry, reuse, rate limiting) and CSRF failure.
- Improve logging and monitoring; set up backups for the DB.

---

If you want, I can now write this content into `README.md` (overwrite) or `DEPLOY.md` in the repo root. Which filename do you prefer? Also tell me if you want any extra sections (example ENV files, systemd unit, Dockerfile, or Heroku/Gunicorn deployment snippet) and I'll add them.
