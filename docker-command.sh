#!/bin/sh
#set -x
set -e

# Check environment

python_version="$(python3 -c 'import platform; print(platform.python_version())' | cut -d '.' -f 1,2)"
if [ "${python_version}" != "${PYTHON_VERSION}" ]; then
    echo "PYTHON_VERSION (${PYTHON_VERSION}) different with version reported from python3 executable (${python_version})" 1>&2 && exit 1
fi

if [ ! -f "${SECRET_KEY_FILE}" ]; then
    echo "SECRET_KEY_FILE does not exist!" 1>&2 && exit 1
fi

for var in 'OUTPUT_DIR' 'POSTGRES_HOST' 'POSTGRES_PORT' 'POSTGRES_USER' 'POSTGRES_DB_NAME'; do
  eval value='$'${var}
  if [ -z ${value} ]; then
    echo "${var} is not set!" 1>&2 && exit 1
  fi
done

if [ ! -f "${POSTGRES_PASS_FILE}" ]; then
    echo "POSTGRESS_PASS_FILE does not exist!" 1>&2 && exit 1
fi
POSTGRES_PASS="$(cat ${POSTGRES_PASS_FILE})"

export LOGGING_FILE_CONFIG="./logging.conf"
if [ ! -f "${LOGGING_FILE_CONFIG}" ]; then
    echo "LOGGING_FILE_CONFIG (configuration for Python logging) does not exist!" 1>&2 && exit 1
fi

if [ -n "${LOGGING_ROOT_LEVEL}" ]; then
    sed -i -e "/^\[logger_root\]/,/^\[.*/ { s/^level=.*/level=${LOGGING_ROOT_LEVEL}/ }" ${LOGGING_FILE_CONFIG}
fi

export DATABASE_URI="postgresql://${POSTGRES_USER}:${POSTGRES_PASS}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB_NAME}"
export FLASK_APP="geometry_service"
export SECRET_KEY="$(cat ${SECRET_KEY_FILE})"

# Initialize/Upgrade database

flask db upgrade

# Configure and start WSGI server

if [ "${FLASK_ENV}" = "development" ]; then
    # Run a development server
    exec /usr/local/bin/wsgi.py
fi

num_workers="4"
server_port="5000"
timeout="1200"
num_threads="1"
gunicorn_ssl_options=
if [ -n "${TLS_CERTIFICATE}" ] && [ -n "${TLS_KEY}" ]; then
    gunicorn_ssl_options="--keyfile ${TLS_KEY} --certfile ${TLS_CERTIFICATE}"
    server_port="5443"
fi

exec gunicorn --log-config ${LOGGING_FILE_CONFIG} --access-logfile - \
  --workers ${num_workers} \
  -t ${timeout} \
  --threads ${num_threads} \
  --bind "0.0.0.0:${server_port}" ${gunicorn_ssl_options} \
  "geometry_service:create_app()"
