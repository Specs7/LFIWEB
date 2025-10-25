#!/usr/bin/env bash
set -euo pipefail

# Small helper to verify that the checked-out code on this host matches origin/main
# Usage: run from the repository root or from anywhere (script will cd to repo root)

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "Repository root: $REPO_ROOT"
echo "Fetching remote..."
git fetch origin

LOCAL_HEAD=$(git rev-parse --verify HEAD)
REMOTE_HEAD=$(git rev-parse --verify origin/main)

echo "Local HEAD:  $LOCAL_HEAD"
echo "Remote origin/main: $REMOTE_HEAD"

if [ "$LOCAL_HEAD" = "$REMOTE_HEAD" ]; then
  echo "✅ Commit hashes are identical. The checked-out commit equals origin/main."
else
  echo "⚠️ Commit hashes differ."
  echo "Files differing between local HEAD and origin/main:" 
  git --no-pager diff --name-only "$LOCAL_HEAD" "$REMOTE_HEAD" || true
fi

echo
echo "Working tree cleanliness (uncommitted changes):"
git status --porcelain || true

echo
echo "Tree object comparison (optional detailed): generating lists..."
git ls-tree -r "$LOCAL_HEAD" | sort > /tmp/local-tree.txt
git ls-tree -r "$REMOTE_HEAD" | sort > /tmp/remote-tree.txt

echo "Diff (local vs remote):"
diff -u /tmp/local-tree.txt /tmp/remote-tree.txt || echo "(diff finished or no differences)"

echo
echo "If you want to make this host match origin/main exactly, run on this host:\n  git fetch origin && git reset --hard origin/main"

exit 0
