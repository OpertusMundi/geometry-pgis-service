import os
from flask import Blueprint, make_response
import tempfile
from os import unlink
from geometry_service.database.postgis import Postgis
from geometry_service.loggers import logger

def _checkDirectoryWritable(d):
    fd, fname = tempfile.mkstemp(None, None, d)
    unlink(fname)

def _checkConnectToPostgis():
    postgres = Postgis('public')
    engine_url = postgres.check()
    logger.debug('_checkConnectToPostgis(): Connected to %s' % (engine_url))

bp = Blueprint('misc', __name__)

@bp.route("/health", methods=['GET'])
def health():
    """**Flask GET rule**

    Perform basic health checks.
    ---
    get:
        summary: Get health status.
        tags:
            - Misc
        responses:
            200:
                description: An object with status information.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                status:
                                    type: string
                                    enum:
                                        - OK
                                        - FAILED
                                    description: A status of 'OK' or 'FAILED'.
                                details:
                                    type: object
                                    description: The reason of failure for each component, or 'OK' if not failed.
                                    properties:
                                        fiona:
                                            type: string
                                            example: OK
                                        filesystem:
                                            type: string
                                            example: OK
                                        postgis:
                                            type: string
                                            example: OK
    """
    from fiona.env import Env

    logger.info('Performing health checks...')
    msg = {'fiona': 'OK', 'filesystem': 'OK', 'postgis': 'OK'}
    status = True

    with Env() as gdalenv:
        drivers = list(gdalenv.drivers().keys())
        for drv in ['CSV', 'GeoJSON', 'ESRI Shapefile']:
            if drv not in drivers:
                msg['fiona'] = 'GDAL is not properly installed.'
                status = False
                break

    for path in [os.environ['WORKING_DIR'], os.environ['OUTPUT_DIR']]:
        try:
            _checkDirectoryWritable(path)
        except Exception as e:
            msg['filesystem'] = str(e)
            status = False
            break

    try:
        _checkConnectToPostgis()
    except Exception as e:
        msg['postgis'] = str(e)
        status = False

    return make_response({'status': 'OK' if status else 'FAILED', 'details': msg}, 200)
