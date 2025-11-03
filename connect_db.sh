#!/bin/bash
# Helper script to connect to MySQL database
cd "$(dirname "$0")"
source .env
mysql -h "${MYSQL_HOST}" -P "${MYSQL_PORT}" -u "${MYSQL_USER}" -p"${MYSQL_PASSWORD}" "${MYSQL_DATABASE}"
