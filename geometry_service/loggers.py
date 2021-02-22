from os import getenv
from logging import getLogger

logger = getLogger(getenv('FLASK_APP'))
