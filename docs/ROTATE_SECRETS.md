# Rotating secrets and credentials (PythonAnywhere)

This document describes safe, minimal steps to rotate the `SECRET_KEY` and SMTP credentials on PythonAnywhere and invalidate outstanding magic-link tokens.

1) Prepare a new SECRET_KEY

   - Use a cryptographically strong secret. Example (run locally):

     python3 -c "import secrets; print(secrets.token_urlsafe(64))"

   - Keep the generated secret in a secure vault (do not commit to git).

2) Set SECRET_KEY on PythonAnywhere

   - Go to your PythonAnywhere Dashboard -> Web -> select your web app.
   - In the "Environment Variables" section add or update `SECRET_KEY` with the new value.
   - Alternatively, you can place a secrets file at `/home/yourusername/.lfiweb_secrets` and load it in your web app WSGI or startup.

3) Restart your web app

   - Click the "Reload" button for your web app in PythonAnywhere or run (on the host):

     pa_reload_command_or_manual_reload

   - After restart, session cookies signed with the old key will be rejected.

4) Invalidate outstanding magic-link tokens (important)

   - SSH/console into PythonAnywhere or use the Files UI to run the provided helper script:

     python3 scripts/invalidate_tokens.py --db /home/yourusername/path/to/data.db --yes

   - The script creates a timestamped backup of the DB before modifying it.

5) Rotate SMTP credentials

   - If you used an app password (recommended), generate a new app password and update `SMTP_PASS` in your environment variables (Web -> Environment variables) or in your secrets file.
   - Test sending a magic link from the admin UI or run a small SMTP check helper.

6) Post-rotation checks

   - Confirm you can login using a new magic link (request a link, consume it).
   - Check `admin/status` endpoint for `redis` and `storage_bytes` (if configured).
   - Monitor logs for errors.

7) Notes

   - If you do not have direct shell access to run the SQL/script, you can use the PythonAnywhere Files tool to upload the script and run it via the "Bash console".
   - Do not commit secrets into the repository. Use the PythonAnywhere environment variables or a private file with permission 600.
