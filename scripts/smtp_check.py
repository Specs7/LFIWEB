#!/usr/bin/env python3
"""SMTP checker helper.

This module is safe to import (no SystemExit on import). Run directly to send a test
email if SMTP env vars are configured.
"""
import os
import smtplib
from email.message import EmailMessage
from urllib.parse import urlparse


def send_test(to_email: str):
    smtp_host = os.getenv('SMTP_HOST')
    if not smtp_host:
        print('SMTP_HOST not set. The app will log magic links instead of sending emails.')
        return 0

    smtp_port = int(os.getenv('SMTP_PORT') or 587)
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')
    smtp_use_tls = os.getenv('SMTP_USE_TLS', '1') not in ('0', 'false', 'False')
    from_email = os.getenv('FROM_EMAIL', smtp_user or f"no-reply@{urlparse(os.getenv('SITE_URL','localhost')).hostname}")

    msg = EmailMessage()
    msg['Subject'] = 'LFIWEB SMTP test'
    msg['From'] = from_email
    msg['To'] = to_email
    msg.set_content('This is a test email from LFIWEB.')
    s = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
    try:
        if smtp_use_tls:
            s.starttls()
        if smtp_user and smtp_pass:
            s.login(smtp_user, smtp_pass)
        s.send_message(msg)
        print('Email sent (no exception raised).')
        return 0
    finally:
        try:
            s.quit()
        except Exception:
            pass


def main():
    import sys
    if len(sys.argv) < 2:
        print('Usage: smtp_check.py recipient@example.com')
        return 2
    return send_test(sys.argv[1])


if __name__ == '__main__':
    raise SystemExit(main())
