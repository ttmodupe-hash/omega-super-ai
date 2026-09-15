#!/usr/bin/env bash
# PUSH_COMMANDS.sh - one-shot release push for ttmodupe-hash/omega-super-ai.
# Run INSIDE the clone root (e.g., /workspaces/omega-super-ai in Codespaces),
# AFTER copying the unzipped release contents into this directory.
set -euo pipefail

VERSION="v5.31.0"
EXPECTED_REMOTE="ttmodupe-hash/omega-super-ai"

echo "[0/7] verifying the release tree actually landed in this clone"
if [ ! -f core/main.py ] || [ ! -f requirements.txt ] || [ ! -d .github/workflows ]; then
  echo "FAIL: release files are not in $(pwd)."
  echo "Copy them first, e.g.:"
  echo "  unzip omega-luqi-ai-engine-v5.31.0-full.zip -d /tmp/release"
  echo "  (cd /tmp/release/omega-luqi-ai-engine && tar cf - .) | tar xf - -C $(pwd)"
  echo "then re-run ./PUSH_COMMANDS.sh"
  exit 1
fi
git status --short | head -5
echo "  (above: the first few pending changes - if EMPTY, the copy failed)"

echo "[1/7] verifying remote target"
git remote -v | grep -q "$EXPECTED_REMOTE" || {
  echo "FAIL: origin is not $EXPECTED_REMOTE. Fix with:"
  echo "  git remote set-url origin https://github.com/$EXPECTED_REMOTE.git"
  exit 1
}

echo "[2/7] fetching monolith anchor history (v25.1.0 lineage)"
git pull origin main --rebase --allow-unrelated-histories

echo "[3/7] staging consolidated tree (engine + legacy vault + docs)"
git add -A

echo "[4/7] committing $VERSION"
git commit -m "release: $VERSION integrated digital legacy migration, database triggers, data portability schemas, and verified monolith archive"

echo "[5/7] self-healing tags (removing any stale tag that points at the wrong commit)"
git tag -d "$VERSION" 2>/dev/null || true
git push origin ":refs/tags/$VERSION" 2>/dev/null || true

echo "[6/7] tagging $VERSION on THIS commit"
git tag -a "$VERSION" -m "release $VERSION final architecture"

echo "[7/7] pushing branch + tag"
git push origin main
git push origin "$VERSION"

echo ""
echo "VERIFY - all three must pass:"
echo "  1. git log --oneline -1   -> date 2026-09-15, release message"
echo "  2. Actions tab            -> omega_luqi_sync.yml running"
echo "  3. This check from anywhere: newest commit on github.com/$EXPECTED_REMOTE is today"
