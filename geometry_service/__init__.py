"""
### A service to perform geometric operations on geospatial datasets.

The *geometry service* offers the ability to apply geometric operations on one or more spatial files. Multiple geometric operations can be, in general, consecutively applied, before the final resulted file is exported and downloaded.

The service uses sessions to store the ingested and generated datasets. Each session is associated with a session token, and the related datasets are available only within this session. Almost every request to this service should transfer this token in its header. A session is automatically created when the first spatial file is ingested.

Following the ingestion of a file, one can apply geometric operations in order to generate new datasets, or ingest more. Each dataset is associated with a user-defined *label*, which should be unique for the session. The user can choose upon which dataset is willing to apply each operation by choosing the corresponding label. Every session has one active dataset, which has the role to be the one used by default in cases that no label is supplied with the request. The active dataset is, in principle, the last ingested dataset, unless it has explicitly changed.

The session and all the related datasets are destroyed upon request or if the session remains idle for a certain amount of time.
"""

import os, sys
from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
import tempfile
from geometry_service.database import db
from ._version import __version__
from .api.doc_components import add_components
from .loggers import logger

# OpenAPI documentation
logger.debug('Initializing OpenAPI specification.')
spec = APISpec(
    title="Geometry API",
    version=__version__,
    info=dict(
        description=__doc__,
        contact={"email": "pmitropoulos@getmap.gr"}
    ),
    externalDocs={"description": "GitHub", "url": "https://github.com/OpertusMundi/geometry-service"},
    openapi_version="3.0.2",
    plugins=[FlaskPlugin()],
)
logger.debug('Adding OpenAPI specification components.')
add_components(spec)

# Check environment variables
if os.getenv('DATABASE_URI') is None:
    logger.fatal('Environment variable not set [variable="DATABASE_URI"]')
    sys.exit(1)
if os.getenv('SECRET_KEY') is None:
    logger.fatal('Environment variable not set [variable="SECRET_KEY"]')
    sys.exit(1)
if os.getenv('OUTPUT_DIR') is None:
    logger.fatal('Environment variable not set [variable="OUTPUT_DIR"]')
    sys.exit(1)
if os.getenv('TOKEN_HEADER') is None:
    os.environ['TOKEN_HEADER'] = "X-Token"
    logger.info('Set environment variable [TOKEN_HEADER="X-Token"]')
if os.getenv('WORKING_DIR') is None:
    working_dir = os.path.join(tempfile.gettempdir(), os.getenv('FLASK_APP'))
    os.environ['WORKING_DIR'] = working_dir
    logger.info('Set environment variable [WORKING_DIR="%s"]', working_dir)
if os.getenv('MAX_RESULTS_PAGE') is None:
    os.environ['MAX_RESULTS_PAGE'] = "50"
    logger.info('Set environment variable [MAX_RESULTS_PAGE="50"]')
if os.getenv('CORS') is None:
    os.environ['CORS'] = '*'
    logger.info('Set environment variable [CORS="*"]')
if os.getenv('CLEANUP_INTERVAL') is None:
    os.environ['CLEANUP_INTERVAL'] = "1440"
    logger.info('Set environment variable [CLEANUP_INTERVAL="1440"]')

# Create directories
for path in [os.environ['WORKING_DIR'], os.environ['OUTPUT_DIR']]:
    try:
        os.makedirs(path)
    except OSError:
        pass
    else:
        logger.info("Created directory: %s.", path)


def create_app():
    """Create flask app."""
    from flask import Flask, make_response
    from flask_migrate import Migrate
    from flask_cors import CORS
    from geometry_service.api import misc, session, dataset, constructive, filter_, join, jobs

    logger.debug('Initializing app.')
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ['SECRET_KEY'],
        SQLALCHEMY_DATABASE_URI=os.environ['DATABASE_URI'],
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JSON_SORT_KEYS=False,
        EXECUTOR_TYPE="process",
        EXECUTOR_MAX_WORKERS="1"
    )
    db.init_app(app)
    migrate = Migrate(app, db, directory=os.path.join(os.path.dirname(__file__), 'database', 'migrations'))

    #Enable CORS
    if os.getenv('CORS') is not None:
        if os.getenv('CORS')[0:1] == '[':
            origins = json.loads(os.getenv('CORS'))
        else:
            origins = os.getenv('CORS')
        cors = CORS(app, origins=origins)

    # Register Blueprints
    session.executor.init_app(app)
    logger.debug('Registering blueprints.')
    app.register_blueprint(session.bp)
    app.register_blueprint(dataset.bp)
    app.register_blueprint(constructive.bp)
    app.register_blueprint(filter_.bp)
    app.register_blueprint(join.bp)
    app.register_blueprint(jobs.bp)
    app.register_blueprint(misc.bp)

    # Register documentation
    logger.debug('Registering documentation.')
    with app.test_request_context():
        for view in app.view_functions.values():
            spec.path(view=view)

    @app.route("/", methods=['GET'])
    def index():
        """The index route, returns the JSON OpenAPI specification."""
        logger.info('Generating the OpenAPI document...')
        return make_response(spec.to_dict(), 200)

    # Register cli commands
    with app.app_context():
        import geometry_service.cli

    logger.debug('Created app.')
    return app
