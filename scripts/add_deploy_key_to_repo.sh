#!/usr/bin/env bash
# Add an SSH public key as a deploy key to a GitHub repository via the API.
# Usage:
#   export GITHUB_TOKEN=ghp_...   # create a token with `repo` scope (for private repos) or appropriate scopes
#   ./scripts/add_deploy_key_to_repo.sh Specs7 LFIWEB ~/.ssh/drancy.pub "drancy deploy key" false
# Parameters:
#   $1 = owner (e.g. Specs7)
#   $2 = repo  (e.g. LFIWEB)
#   $3 = pubkey_path (defaults to ~/.ssh/id_ed25519.pub)
#   $4 = title (optional)
#   $5 = read_only (true/false) default true

set -euo pipefail

if [ -z "${GITHUB_TOKEN:-}" ]; then
  echo "Error: please export GITHUB_TOKEN with a Personal Access Token that has 'repo' scope (for private repos)" >&2
  exit 2
fi

OWNER=${1:-}
REPO=${2:-}
PUBKEY_PATH=${3:-$HOME/.ssh/id_ed25519.pub}
TITLE=${4:-"deploy-key-$(date -u +%Y%m%dT%H%M%SZ)"}
READ_ONLY=${5:-true}

if [ -z "$OWNER" ] || [ -z "$REPO" ]; then
  echo "Usage: $0 <owner> <repo> [pubkey_path] [title] [read_only]" >&2
  exit 2
fi

if [ ! -f "$PUBKEY_PATH" ]; then
  echo "Public key not found at $PUBKEY_PATH" >&2
  exit 3
fi

KEY_CONTENT=$(cat "$PUBKEY_PATH")

json=$(jq -n --arg t "$TITLE" --arg k "$KEY_CONTENT" --argjson ro $( [ "$READ_ONLY" = "true" ] && echo true || echo false ) '{title:$t, key:$k, read_only:$ro}')

echo "Adding deploy key to $OWNER/$REPO (read_only=$READ_ONLY) ..."

resp=$(curl -sS -w "\n%{http_code}" -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d "$json" \
  "https://api.github.com/repos/$OWNER/$REPO/keys")

body=$(echo "$resp" | sed '$d')
code=$(echo "$resp" | tail -n1)

if [ "$code" = "201" ]; then
  echo "Deploy key added successfully."
  echo "$body" | jq '.'
  exit 0
else
  echo "Failed to add deploy key (HTTP $code):" >&2
  echo "$body" | jq '.' >&2 || echo "$body" >&2
  exit 4
fi
