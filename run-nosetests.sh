#!/bin/sh
#set -x
set -e

export FLASK_APP="geometry_service"
export SECRET_KEY="$(dd if=/dev/urandom bs=12 count=1 status=none | xxd -p -c 12)"

if [ -f "${POSTGRES_PASS_FILE}" ]; then
    POSTGRES_PASS="$(cat ${POSTGRES_PASS_FILE})"
fi
export DATABASE_URI="postgresql://${POSTGRES_USER}:${POSTGRES_PASS}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB_NAME}"

# Initialize database

flask db upgrade

# Run

exec nosetests $@
