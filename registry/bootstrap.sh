#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p registry/auth registry/certs nginx/conf.d pgadmin
chmod 755 registry registry/auth registry/certs nginx nginx/conf.d pgadmin

if [[ ! -f .env ]]; then
  ip="$(ip -4 route get 1.1.1.1 | awk '{for (i = 1; i <= NF; i++) if ($i == "src") { print $(i + 1); exit }}')"
  umask 077
  cat > .env <<EOF
POSTGRES_USER=autoservice
POSTGRES_PASSWORD=$(openssl rand -hex 24)
POSTGRES_DB=autoservice
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=$(openssl rand -hex 24)
REGISTRY_HOST=${ip}
REGISTRY_PORT=5000
REGISTRY_USER=autoservice
REGISTRY_PASSWORD=$(openssl rand -hex 24)
REGISTRY_HTTP_SECRET=$(openssl rand -hex 32)
EOF
  chmod 600 .env
  echo "Created .env"
fi

set -a
# shellcheck disable=SC1091
source ./.env
set +a

python3 - <<'PY'
import os
from pathlib import Path
import bcrypt

user = os.environ["REGISTRY_USER"]
password = os.environ["REGISTRY_PASSWORD"].encode()
hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12)).decode()
path = Path("registry/auth/htpasswd")
path.write_text(f"{user}:{hashed}\n")
os.chmod(path, 0o644)
PY

host="${REGISTRY_HOST}"
port="${REGISTRY_PORT:-5000}"
force="${1:-}"

if [[ ! -f registry/certs/registry.crt || "$force" == "--force" ]]; then
  san="$(mktemp)"
  cat > "$san" <<EOF
[req]
distinguished_name = dn
prompt = no
[dn]
CN = ${host}
[v3_req]
subjectAltName = @alt_names
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
basicConstraints = CA:FALSE
[alt_names]
DNS.1 = localhost
DNS.2 = registry
IP.1 = 127.0.0.1
EOF
  if [[ "$host" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "IP.2 = ${host}" >> "$san"
  else
    echo "DNS.3 = ${host}" >> "$san"
  fi

  openssl genrsa -out registry/certs/ca.key 4096
  openssl req -x509 -new -nodes -key registry/certs/ca.key -sha256 -days 3650 \
    -out registry/certs/ca.crt -subj "/CN=Autoservice Local Registry CA"
  openssl genrsa -out registry/certs/registry.key 4096
  openssl req -new -key registry/certs/registry.key -out registry/certs/registry.csr -config "$san"
  openssl x509 -req -in registry/certs/registry.csr \
    -CA registry/certs/ca.crt -CAkey registry/certs/ca.key -CAcreateserial \
    -out registry/certs/registry.crt -days 825 -sha256 \
    -extensions v3_req -extfile "$san"
  rm -f "$san" registry/certs/registry.csr
  echo "Issued registry certificate for ${host}"
fi

chmod 644 registry/certs/ca.crt registry/certs/registry.crt registry/auth/htpasswd
chmod 600 registry/certs/ca.key registry/certs/registry.key .env

install_ca() {
  local dest="/etc/docker/certs.d/${1}:${port}"
  mkdir -p "$dest"
  cp registry/certs/ca.crt "${dest}/ca.crt"
  chmod 755 /etc/docker/certs.d "${dest}"
  chmod 644 "${dest}/ca.crt"
}

install_ca "$host"
install_ca "127.0.0.1"

echo "Registry: https://${host}:${port}"
echo "docker login user: ${REGISTRY_USER}"
echo "Password is in .env (REGISTRY_PASSWORD)"
echo "Copy registry/certs/ca.crt to the client: /etc/docker/certs.d/${host}:${port}/ca.crt"
