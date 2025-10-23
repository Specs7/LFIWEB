#!/usr/bin/env python3
"""
PythonAnywhere audit script for the LFIWEB project.

Usage (on PythonAnywhere console inside your repo):
  # dry run checks (no DB modifications)
  python3 scripts/pa_audit.py --repo ~/your-repo-directory --site https://yourdomain.pythonanywhere.com

  # include DB checks (will only read DB, not modify)
  python3 scripts/pa_audit.py --repo ~/your-repo-directory --check-db --db /home/yourusername/path/to/data.db

The script intentionally never prints secret values; it only reports presence/length.
It collects:
 - git commit hash and whether origin/main matches
 - uncommitted changes
 - python version and virtualenv info
 - presence of key env vars (SECRET_KEY, SITE_URL, SMTP_*, REDIS_URL)
 - scan for data.db in the repo directory
 - optional DB token counts (if --check-db is provided)
 - WSGI file hint search for typical PythonAnywhere path
 - uploads directory existence and permissions
 - small HTTP smoke test to the provided site URL (if given)

Output: prints a human-readable summary and writes `pa_audit_report.json` in the repo dir if writable.
"""

import argparse
import json
import os
import subprocess
import sys
import stat
import sqlite3
from datetime import datetime
from pathlib import Path


def run(cmd, cwd=None, capture=True, check=False):
    try:
        if capture:
            res = subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        else:
            res = subprocess.run(cmd, shell=True, cwd=cwd)
            return res.returncode, '', ''
    except Exception as e:
        return 255, '', str(e)


def check_git(repo_path):
    out = {}
    out['repo_path'] = str(repo_path)
    rc, stdout, stderr = run('git rev-parse --is-inside-work-tree', cwd=repo_path)
    out['is_git'] = rc == 0 and stdout == 'true'
    if not out['is_git']:
        out['git_error'] = stderr or stdout
        return out
    rc, head, _ = run('git rev-parse HEAD', cwd=repo_path)
    out['local_head'] = head
    rc, remote, _ = run('git ls-remote origin refs/heads/main', cwd=repo_path)
    if rc == 0 and remote:
        out['origin_main'] = remote.split()[0]
    else:
        out['origin_main'] = None
    rc, status, _ = run('git status --porcelain', cwd=repo_path)
    out['git_status_porcelain'] = status.splitlines()
    rc, diff_files, _ = run('git diff --name-only origin/main', cwd=repo_path)
    out['diff_from_origin_main'] = diff_files.splitlines()
    return out


def check_python():
    out = {}
    out['python_executable'] = sys.executable
    out['python_version'] = sys.version.splitlines()[0]
    out['virtualenv'] = os.getenv('VIRTUAL_ENV') or None
    # limited pip freeze (first 200 entries) to avoid huge output
    rc, stdout, stderr = run('pip freeze', capture=True)
    if rc == 0:
        lines = stdout.splitlines()
        out['pip_freeze_count'] = len(lines)
        out['pip_freeze_head'] = lines[:200]
    else:
        out['pip_freeze_error'] = stderr or stdout
    return out


def check_env(vars_to_check=()):
    out = {}
    for k in vars_to_check:
        v = os.getenv(k)
        if v is None:
            out[k] = 'MISSING'
        else:
            out[k] = f'SET (len={len(v)})'
    return out


def find_db_files(repo_path):
    found = []
    for p in Path(repo_path).rglob('*.db'):
        # ignore typical backups with .bak
        if p.name.endswith('.bak'):
            continue
        found.append(str(p))
    return found


def db_token_counts(db_path):
    out = {'db_path': db_path}
    if not os.path.exists(db_path):
        out['error'] = 'not found'
        return out
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM login_tokens')
        out['total_tokens'] = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM login_tokens WHERE used=0')
        out['outstanding_tokens'] = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM login_tokens WHERE used=1')
        out['used_tokens'] = cur.fetchone()[0]
    except Exception as e:
        out['error'] = str(e)
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return out


def check_wsgi_hint():
    out = {}
    # Try common PythonAnywhere WSGI path pattern
    user = os.getenv('USER') or os.getenv('USERNAME') or Path.home().owner()
    candidates = [f"/var/www/{user}_pythonanywhere_com_wsgi.py", 
                  f"/var/www/{user}_pythonanywhere_com_wsgi.py"]
    located = []
    for c in candidates:
        if os.path.exists(c):
            located.append(c)
            try:
                with open(c, 'r') as fh:
                    txt = fh.read()
                out[c] = 'FOUND'
                out[c+'_contains_backend_app'] = 'backend.app' in txt
            except Exception as e:
                out[c] = f'FOUND_but_error_reading: {e}'
        else:
            out[c] = 'MISSING'
    out['candidates_checked'] = candidates
    return out


def check_uploads(repo_path):
    ups = Path(repo_path) / 'backend' / 'static' / 'uploads'
    out = {}
    out['uploads_path'] = str(ups)
    out['exists'] = ups.exists()
    if ups.exists():
        try:
            st = ups.stat()
            out['mode_octal'] = oct(st.st_mode & 0o777)
            out['owner_uid'] = st.st_uid
            # list up to 20 files
            files = [str(p) for p in ups.rglob('*') if p.is_file()][:20]
            out['sample_files'] = files
        except Exception as e:
            out['error'] = str(e)
    return out


def smoke_http(site_url):
    out = {'site_url': site_url}
    if not site_url:
        out['error'] = 'no site provided'
        return out
    try:
        import urllib.request
        req = urllib.request.Request(site_url, method='GET', headers={'User-Agent':'pa-audit/1.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            out['http_status'] = r.getcode()
            out['final_url'] = r.geturl()
            out['content_sample'] = r.read(1024).decode('utf-8', errors='replace')
    except Exception as e:
        out['error'] = str(e)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=False, default='.', help='Path to the repository root (on PA)')
    p.add_argument('--check-db', action='store_true', help='Perform DB read-only checks if DB path provided or found')
    p.add_argument('--db', default=None, help='Path to production data.db (optional)')
    p.add_argument('--site', default=None, help='Public site URL for a small HTTP smoke test')
    p.add_argument('--out', default='pa_audit_report.json', help='Output JSON report file name')

    args = p.parse_args()
    repo = os.path.abspath(args.repo)

    report = {'timestamp_utc': datetime.utcnow().isoformat(), 'repo': repo}

    report['git'] = check_git(repo)
    report['python'] = check_python()
    report['env'] = check_env(('SECRET_KEY','SITE_URL','SMTP_HOST','SMTP_USER','SMTP_PASS','REDIS_URL','FROM_EMAIL'))
    report['db_files_found'] = find_db_files(repo)
    report['wsgi'] = check_wsgi_hint()
    report['uploads'] = check_uploads(repo)

    if args.check_db or args.db:
        dbpath = args.db or (report['db_files_found'][0] if report['db_files_found'] else None)
        if dbpath:
            report['db_check'] = db_token_counts(dbpath)
        else:
            report['db_check'] = {'error': 'no db found/provided'}

    if args.site:
        report['smoke_http'] = smoke_http(args.site)

    # write report
    outpath = os.path.join(repo, args.out)
    try:
        with open(outpath, 'w') as fh:
            json.dump(report, fh, indent=2)
        printed = f'Wrote report to {outpath}'
    except Exception as e:
        printed = f'Failed to write report to {outpath}: {e}'

    # human summary
    print('\n--- PA Audit Summary ---')
    print('Repo:', repo)
    g = report['git']
    if not g.get('is_git'):
        print('Git: NOT A GIT REPO -', g.get('git_error'))
    else:
        print('Local HEAD:', g.get('local_head'))
        print('Origin/main:', g.get('origin_main'))
        print('Uncommitted changes:', len(g.get('git_status_porcelain') or []))
        print('Files different from origin/main:', len(g.get('diff_from_origin_main') or []))
    print('Python:', report['python'].get('python_version'))
    print('Virtualenv:', report['python'].get('virtualenv'))
    print('Env vars:')
    for k,v in report['env'].items():
        print(' ', k, ':', v)
    print('DB files found:', report['db_files_found'])
    if 'db_check' in report:
        print('DB check:', report['db_check'])
    print('Uploads:', 'exists' if report['uploads'].get('exists') else 'missing')
    if args.site:
        print('HTTP smoke:', report.get('smoke_http', {}).get('http_status') or report.get('smoke_http', {}).get('error'))
    print(printed)
    print('Full JSON report saved under:', outpath)

if __name__ == '__main__':
    main()
