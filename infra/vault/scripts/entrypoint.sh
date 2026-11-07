#!/bin/sh
set -e

vault server -config=/vault/config/vault.hcl &
VAULT_PID=$!

trap "kill -TERM $VAULT_PID 2>/dev/null" TERM INT

until wget -q -O - "http://127.0.0.1:8200/v1/sys/health?standbyok=true&uninitcode=200&sealedcode=200" >/dev/null 2>&1; do
  sleep 1
done

KEYS_FILE="/vault/file/init-keys.json"
TOKEN_FILE="/vault/token/app-token"

if ! vault status -address=http://127.0.0.1:8200 2>/dev/null | grep -q 'Initialized.*true'; then
  vault operator init -address=http://127.0.0.1:8200 -key-shares=1 -key-threshold=1 -format=json > "$KEYS_FILE"
fi

UNSEAL_KEY=$(sed -n '/"unseal_keys_b64"/,/]/ s/.*"\([A-Za-z0-9+/=]\{30,\}\)".*/\1/p' "$KEYS_FILE")
ROOT_TOKEN=$(sed -n 's/.*"root_token": *"\([^"]*\)".*/\1/p' "$KEYS_FILE")

if vault status -address=http://127.0.0.1:8200 2>/dev/null | grep -q 'Sealed.*true'; then
  vault operator unseal -address=http://127.0.0.1:8200 "$UNSEAL_KEY"
fi

export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="$ROOT_TOKEN"

if ! vault secrets list 2>/dev/null | grep -q '^secret/'; then
  vault secrets enable -path=secret kv-v2
fi

if ! vault kv get secret/careflow >/dev/null 2>&1; then
  GENERATED_KEY=$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32)
  vault kv put secret/careflow \
    DB_HOST="${DB_HOST:-db}" \
    DB_PORT="${DB_PORT:-5432}" \
    POSTGRES_DB="${POSTGRES_DB:-careflow_db}" \
    POSTGRES_USER="${POSTGRES_USER:-careflow_user}" \
    POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?Error: POSTGRES_PASSWORD required}" \
    DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-$GENERATED_KEY}" \
    REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"
fi

mkdir -p /vault/token
echo "$ROOT_TOKEN" > "$TOKEN_FILE"
chmod 755 /vault/token
chmod 644 "$TOKEN_FILE"

wait $VAULT_PID

