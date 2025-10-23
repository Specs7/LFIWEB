"""Smoke test for the public site.

Checks:
 - GET / returns 200 and does not contain admin UI markers
 - GET /api/me returns {"user": null} for an anonymous request

Usage:
    python3 scripts/smoke_test.py --host https://your.site

Defaults to http://127.0.0.1:5000 for quick local checks.
"""
import argparse
import sys
import requests

ADMIN_MARKERS = ["id=\"admin-panel\"", "id=\"article-edit-modal\"", "adminArticleForm", "admin-panel"]


def check_home(host):
    url = host.rstrip('/') + '/'
    print('GET', url)
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        print('FAIL: / returned', r.status_code)
        return False
    body = r.text.lower()
    for m in ADMIN_MARKERS:
        if m.lower() in body:
            print('FAIL: found admin marker in public homepage:', m)
            return False
    print('OK: homepage looks clean')
    return True


def check_api_me(host):
    url = host.rstrip('/') + '/api/me'
    print('GET', url)
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        print('FAIL: /api/me returned', r.status_code)
        return False
    try:
        j = r.json()
    except Exception as e:
        print('FAIL: /api/me returned non-json', e)
        return False
    if j.get('user') is not None:
        print('FAIL: /api/me indicates a user is logged in (expected null):', j)
        return False
    print('OK: /api/me returns user:null for anonymous')
    return True


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='http://127.0.0.1:5000')
    args = p.parse_args()
    host = args.host
    ok = True
    try:
        ok &= check_home(host)
        ok &= check_api_me(host)
    except Exception as e:
        print('ERROR during smoke tests:', e)
        sys.exit(2)
    if ok:
        print('SMOKE TESTS PASSED')
        sys.exit(0)
    else:
        print('SMOKE TESTS FAILED')
        sys.exit(1)
