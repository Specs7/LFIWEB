#!/usr/bin/env python3
"""
Append a timestamped chat message to Rachid.md.

Usage:
  python scripts/append_chat_to_rachid.py --role "User" --message "..."

This script is intentionally minimal and safe for local use. It will
append the entry to the repository file `Rachid.md` if that file exists.
"""
import argparse
import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RACHID = ROOT / "Rachid.md"


def append(role: str, message: str):
    if not RACHID.exists():
        raise SystemExit(f"{RACHID} not found")
    ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    entry = f"\n{ts} — {role}: {message}\n"
    with RACHID.open("a", encoding="utf-8") as f:
        f.write(entry)
    print(f"Appended to {RACHID}: {ts} — {role}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--role", required=True, help="Role of the message (User/Assistant)")
    p.add_argument("--message", required=True, help="Message text to append")
    args = p.parse_args()
    append(args.role, args.message)


if __name__ == "__main__":
    main()
