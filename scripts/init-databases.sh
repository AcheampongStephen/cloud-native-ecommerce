#!/bin/sh
set -eu
for service in identity product inventory payment order notification; do
  var="$(printf '%s' "$service" | tr '[:lower:]' '[:upper:]')_DB_PASSWORD"
  password="$(printenv "$var")"
  psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=service="$service" --set=password="$password" --set=ON_ERROR_STOP=1 <<'SQL'
CREATE ROLE :"service" LOGIN PASSWORD :'password';
CREATE DATABASE :"service" OWNER :"service";
REVOKE CONNECT ON DATABASE :"service" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"service" TO :"service";
SQL
done
