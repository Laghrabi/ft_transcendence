#!/bin/bash

set -e

SSL_DIR="infra/nginx/ssl"
mkdir -p "$SSL_DIR"

CERT_FILE="$SSL_DIR/careflow.crt"
KEY_FILE="$SSL_DIR/careflow.key"

if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
	echo "TLS certificate already exist"
	exit 0
fi

echo "Generating the SSL certificates..."

openssl req -x509 -nodes -days 365 \
		-newkey rsa:2048 \
		-keyout "$KEY_FILE" \
		-out "$CERT_FILE" \
		-subj "/C=MA/ST=Benguerir/L=1337/O=CareFlow/CN=localhost" \
		-addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
		2>/dev/null

chmod 644 "$KEY_FILE" "$CERT_FILE"

echo "TLS certificates generated successfully"