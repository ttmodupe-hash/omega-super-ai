#!/bin/bash
# ==============================================================================
# LUQI-AI SECURE KEY PROVISIONING (hardened)
# Backs up .env, detects placeholder keys, migrates BEFORE restarting,
# then verifies health + token board. Run on the host, never in git.
# ==============================================================================
set -euo pipefail

ENV_FILE="${1:-/opt/luqi-ai/.env}"
SERVICE_NAME="${2:-luqi-core.service}"

if [ ! -f "$ENV_FILE" ]; then
  echo "FAIL: $ENV_FILE not found"; exit 1
fi

echo "[1/6] Backup existing vault"
cp "$ENV_FILE" "$ENV_FILE.bak.$(date +%Y%m%d%H%M%S)"
chmod 600 "$ENV_FILE".bak.* 2>/dev/null || true

echo "[2/6] Scrub old multipolar keys"
sed -i '/^GEMINI_API_KEY=/d' "$ENV_FILE" || true
sed -i '/^CLAUDE_API_KEY=/d' "$ENV_FILE" || true
sed -i '/^KIMI_API_KEY=/d' "$ENV_FILE" || true

echo "[3/6] Append keys (EDIT the placeholders below before running)"
cat << 'EOF' >> "$ENV_FILE"
GEMINI_API_KEY="AIzaSyYourJohannesburgLocalDataResidencyRegionKey"
CLAUDE_API_KEY="sk-ant-api03-YourHighStandardEngineeringClaudeKey"
KIMI_API_KEY="sk-moonshot-YourFlagship1MContextResearchKey"
EOF
chmod 600 "$ENV_FILE"

if grep -q "Your.*Key" "$ENV_FILE"; then
  echo "WARN: placeholder key strings detected - replace with real tokens before"
  echo "       treating the deployment as live. Board will show them as present."
fi

echo "[4/6] Apply migrations BEFORE restart (service boots against migrated schema)"
cd "$(dirname "$ENV_FILE")" && alembic upgrade head

echo "[5/6] Restart service"
sudo systemctl restart "$SERVICE_NAME"
sleep 3

echo "[6/6] Verify"
curl -fsS http://localhost:8000/v1/health && echo "" || echo "WARN: health check failed - inspect: journalctl -u $SERVICE_NAME -f"
echo "Token board (admin key required): curl -H 'X-Luqi-Admin-Auth: <key>' http://localhost:8000/v1/system/token-status"
echo "Done."
