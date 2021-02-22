"""Common Flask context functions, shared among blueprints."""

from flask import request, g, make_response
from flask.wrappers import Response
from geometry_service.database.model.session import Session
from geometry_service.loggers import logger

def get_token():
    """Retrieves the session from the header of the request.

    Returns:
        (None|Response): If session token does not exist in the header, returns a Flask Response. None otherwise.
    """
    from os import environ
    token = request.headers.get(environ['TOKEN_HEADER'])
    if token is None:
        logger.info("Session token not found in request headers.")
        return make_response({"status": "No session token found."}, 401)
    g.session = {'token': token}

def get_session():
    """Copies session from database to Flask session.

    Returns:
        (None|Response): If the session token was not found in the header or the session does not exist, returns a Flask Response. None otherwise.
    """
    response = get_token()
    if isinstance(response, Response):
        return response
    token = g.session['token']
    session = Session().get(token)
    if session is None:
        logger.info('No active session. [token="%s"]', token)
        return make_response({"status": "No active session."}, 401)
    for key in session.keys():
        if key == 'schema':
            g.session['db_schema'] = session['schema']
        else:
            g. session[key] = session[key]
