#!/usr/bin/env bash
# Lightweight remediation script for PythonAnywhere / similar hosts.
# Usage examples:
#   Dry-run (show what will be done):
#     bash scripts/pa_remediate.sh --repo . --db backend/data.db
#
#   Apply changes (non-interactive):
#     bash scripts/pa_remediate.sh --repo . --db /home/youruser/path/data.db --yes --expire-tokens

set -euo pipefail

REPO_DIR="$(pwd)"
VENV_DIR="${REPO_DIR}/.venv"
DB_PATH=""
DRY_RUN=1
EXPIRE_TOKENS=0
YES=0

usage(){
  cat <<EOF
pa_remediate.sh - basic remediation for LFIWEB on PythonAnywhere

Options:
  --repo PATH        Repository root (default: current dir)
  --venv PATH        Virtualenv path (default: ./\.venv)
  --db PATH          Path to production SQLite DB (default: tries backend/data.db)
  --yes              Apply changes (default: dry-run)
  --expire-tokens    Expire login tokens (will run scripts/invalidate_tokens.py --yes) (requires --yes)
  --help

This script does NOT echo secret values. It will create backups and prompt when destructive
actions are requested unless --yes is provided.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_DIR="$2"; shift 2;;
    --venv) VENV_DIR="$2"; shift 2;;
    --db) DB_PATH="$2"; shift 2;;
    --yes) YES=1; DRY_RUN=0; shift;;
    --expire-tokens) EXPIRE_TOKENS=1; shift;;
    --help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

REPO_DIR="$(realpath "$REPO_DIR")"
VENV_DIR="$(realpath "$VENV_DIR")"

echo "Repository: $REPO_DIR"
echo "Virtualenv: $VENV_DIR"

if [[ -z "$DB_PATH" ]]; then
  # prefer backend/data.db
  if [[ -f "$REPO_DIR/backend/data.db" ]]; then
    DB_PATH="$REPO_DIR/backend/data.db"
  else
    # try to find any .db file
    DB_PATH="$(find "$REPO_DIR" -maxdepth 3 -name 'data.db' -print -quit || true)"
  fi
fi

echo "Detected DB path: ${DB_PATH:-<none>}"

echo
echo "Planned actions (dry-run=${DRY_RUN}, expire_tokens=${EXPIRE_TOKENS}):"
echo " - Ensure virtualenv exists at $VENV_DIR and install requirements"
echo " - Backup DB: ${DB_PATH:-<none>}"
echo " - Secure uploads directory: backend/static/uploads (chmod directories -> 750, files -> 640)"
echo " - Optionally run scripts/invalidate_tokens.py to expire tokens (only if --expire-tokens and --yes)"

if [[ $DRY_RUN -eq 1 ]]; then
  echo
  echo "Dry-run mode: no changes will be made. Re-run with --yes to apply."
  exit 0
fi

if [[ $YES -ne 1 ]]; then
  echo "Confirm you want to apply the planned actions. Re-run with --yes to skip this prompt."
  read -r -p "Apply changes now? [y/N]: " ans
  if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
    echo "Aborting."; exit 1
  fi
fi

echo "Starting remediation..."

# 1) Create virtualenv if missing and install requirements
if [[ ! -x "$VENV_DIR/bin/activate" ]]; then
  echo "Creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
else
  echo "Virtualenv already exists"
fi

echo "Activating virtualenv and installing requirements (may take a while)"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
pip install --upgrade pip >/dev/null || true
if [[ -f "$REPO_DIR/requirements.txt" ]]; then
  pip install -r "$REPO_DIR/requirements.txt"
else
  echo "No requirements.txt found in repo root; skipping pip install"
fi

# 2) Backup DB if present
if [[ -n "$DB_PATH" && -f "$DB_PATH" ]]; then
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  BACKUP="${DB_PATH}.${TS}.bak"
  echo "Creating DB backup: $BACKUP"
  cp -p "$DB_PATH" "$BACKUP"
  chmod 600 "$BACKUP" || true
else
  echo "No DB found at $DB_PATH; skipping DB backup"
fi

# 3) Secure uploads directory
UPLOADS_DIR="$REPO_DIR/backend/static/uploads"
if [[ -d "$UPLOADS_DIR" ]]; then
  echo "Securing uploads directory: $UPLOADS_DIR"
  find "$UPLOADS_DIR" -type d -exec chmod 750 {} + || true
  find "$UPLOADS_DIR" -type f -exec chmod 640 {} + || true
else
  echo "Uploads directory not found; creating: $UPLOADS_DIR"
  mkdir -p "$UPLOADS_DIR"
  chmod 750 "$UPLOADS_DIR"
fi

# 4) Optionally expire tokens
if [[ $EXPIRE_TOKENS -eq 1 ]]; then
  if [[ -z "$DB_PATH" || ! -f "$DB_PATH" ]]; then
    echo "Cannot expire tokens: DB not found at $DB_PATH"
  else
    echo "Running token expiration script (creates its own DB backup):"
    python3 "$REPO_DIR/scripts/invalidate_tokens.py" --db "$DB_PATH" --yes
  fi
fi

echo "Remediation complete. Recommended next steps:" 
echo " - Set environment variables in PythonAnywhere Web -> Environment variables: SECRET_KEY, SITE_URL, DB_PATH (absolute), SMTP_* and REDIS_URL if used." 
echo " - Reload the web app from the PythonAnywhere Web panel." 
echo " - Check logs for errors and run smoke tests." 

deactivate || true

exit 0
