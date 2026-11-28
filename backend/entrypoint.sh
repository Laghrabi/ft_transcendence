#!/bin/bash
set -e

TOKEN_FILE="/vault/token/app-token"
MAX_WAIT=60
WAITED=0
until [ -f "$TOKEN_FILE" ] && curl -s -f http://vault:8200/v1/sys/health >/dev/null; do
  WAITED=$((WAITED + 1))
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "ERROR: Timed out after ${MAX_WAIT}s waiting for Vault ($TOKEN_FILE and /v1/sys/health)." >&2
    exit 1
  fi
  sleep 1
done

SECRETS_JSON=$(curl -s -f -H "X-Vault-Token: $(cat "$TOKEN_FILE")" http://vault:8200/v1/secret/data/careflow)

eval "$(echo "$SECRETS_JSON" | python3 -c '
import sys, json, shlex
data = json.load(sys.stdin).get("data", {}).get("data", {})
for k, v in data.items():
    print(f"export {k}={shlex.quote(str(v))}")
')"

python manage.py migrate --noinput

if [ "${DJANGO_DEBUG:-0}" = "1" ] && [ "$(echo "${SEED_DEV_DATA:-false}" | tr '[:upper:]' '[:lower:]')" = "true" ]; then
    python manage.py seed_dev_data --confirm-local --with-staff
fi

# Collect static files into shared volume
python manage.py collectstatic --noinput 2>/dev/null || true

exec daphne -b 0.0.0.0 -p 8000 "${DJANGO_ASGI_APP:-config.asgi:application}"
