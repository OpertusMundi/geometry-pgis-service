import os
from flask import Blueprint, make_response, g, request, jsonify
from flask.wrappers import Response
from werkzeug.utils import secure_filename
from flask_executor import Executor
from ..forms.session import IngestFileForm, IngestPathForm, SetActiveForm, ExportForm
from ..context import get_token, get_session
from geometry_service.database import db
from geometry_service.database.model import Datasets, Queue
from geometry_service.database.actions import *
from geometry_service.database.postgis import Postgis
from geometry_service.exceptions import SessionDoesNotExist, NotUniqueViolation
from geometry_service.loggers import logger

def _mkdir(path):
    """Creates recursively the path, ignoring warnings for existing directories.

    Arguments:
        path (str): The path to be created.

    Returns:
        (str): The created path.
    """
    try:
        os.makedirs(path)
    except OSError:
        pass
    else:
        logger.info("Created directory: %s.", path)
    return path

def _before_requests():
    """Executed before each request for this blueprint.

    Get the session details of the corresponding token or the session token.

    Returns:
        None|Response: In case of error, returns a Flask response, None otherwise.
    """
    response = get_token() if request.endpoint in ['session.ingest'] else get_session()
    logger.info('API request [endpoint: "%s", token: "%s"]', request.endpoint, g.session['token'])
    if isinstance(response, Response):
        return response


def ingest_process(queue, session, src_file, label, **kwargs):
    """The process that ingests a file into PostGIS.

    Arguments:
        queue (dict): Queue details.
        session (dict): Session details.
        src_file (str): Full path of the file to ingest.
        label (str): The label assigned to the created dataset.
        **kwargs: Additional arguments for postgis.ingest.

    Returns:
        (tuple):
            * (UUID): Queue uuid.
            * (UUID): Session uuid.
            * (dict): Dataset details.
            * (bool): Process status.
            * (str): Error message in case of failure.
    """
    try:
        postgis = Postgis(session['db_schema'])
        table, meta = postgis.ingest(src_file, label, **kwargs)
        dataset = {'label': label, 'table': table, 'filename': src_file, 'meta': meta}
        return (queue['uuid'], session['uuid'], dataset, True, None)
    except Exception as e:
        logger.warning('Ingestion failed. [error: "%s"]', str(e))
        return (queue['uuid'], session['uuid'], None, False, str(e))


def _ingest_callback(future):
    """The ingestion callback function.

    Arguments:
        future (obj): The future object.
    """
    queue, session, dataset, status, error_msg = future.result()
    db_update_ingest_status(queue, session, dataset, status, error_msg)


def export_process(queue, session, table, path, driver, copy_to_output=False, **kwargs):
    """The process that exports a PostGIS dataset into a spatial file.

    Arguments:
        queue (dict): Queue details.
        session (dict): Session details.
        table (str): The table name that will be exported.
        path (str): The path that the spatial file will be written.
        driver (str): The driver that will be used to write the spatial file.
        **kwargs: Additional arguments for exporting the file.

    Keyword Arguments:
        copy_to_output (bool): Whether to copy the file to output path (default: {False})

    Returns:
        (tuple):
            * (dict): Queue details.
            * (dict): Session details.
            * (str): The path of the resulted file.
            * (bool): The status of the process, True on success, False otherwise.
            * (str): The error message in case of failure.
            * (bool): The copy_to_output argument.
    """
    try:
        postgis = Postgis(session['db_schema'])
        file = postgis.to_file(table, path, driver, **kwargs)
    except Exception as e:
        logger.warning('Export failed. [error: "%s"]', str(e))
        return (queue, session, None, False, str(e), copy_to_output)
    return (queue, session, file, True, None, copy_to_output)


def _export_callback(future):
    """The export callback function.

    Updates DB with the export status.

    Arguments:
        future (obj): The future object.
    """
    from datetime import datetime
    from shutil import copyfile
    queue, session, file, status, error_msg, copy_to_output = future.result()
    output_file = None
    if status:
        if copy_to_output:
            filename = os.path.basename(file)
            output_path = os.path.join(datetime.now().strftime("%y%m"), session['token'], queue['ticket'])
            output_file = os.path.join(output_path, filename)
            full_output = os.path.join(os.environ['OUTPUT_DIR'], output_path)
            _mkdir(full_output)
            copyfile(file, os.path.join(full_output, filename))
    db_update_export_status(queue['uuid'], status, file, output_path=output_file, error_msg=error_msg)


def _get_idempotency_key(headers):
    """Retrieves the X-Idempotency-Key from the request headers.

    Arguments:
        headers (obj): The headers of the request.

    Raises:
        NotUniqueViolation: The key already exists.
    """
    key = headers.get('X-Idempotency-Key')
    g.session['idempotent_key'] = key
    if key is not None:
        q = Queue.query.filter_by(idempotent_key=key)
        if db.session.query(q.exists()).scalar():
            raise NotUniqueViolation()



def create_session(token):
    """Creates a new session.

    Registers the session to database, creates the working directory for the session, and adds the session details to flask app session.

    Arguments:
        token (str): The session token.
    """
    session = db_create_session(token)
    g.session = {}
    for attr in session.keys():
        if attr == 'working_path':
            g.session['working_path'] = _mkdir(session['working_path'])
        elif attr == 'schema':
            g.session['db_schema'] = session['schema']
        else:
            g.session[attr] = session[attr]


def close_session(token):
    """Closes a session.

    Registers the session as closed to the database, and removes the working directory.

    Arguments:
        token (str): The session token.
    """
    from shutil import rmtree
    db_close_session(token)
    try:
        rmtree(g.session['working_path'])
    except FileNotFoundError:
        pass
    else:
        logger.info("Removed directory: %s.", g.session['working_path'])


# FLASK ROUTES

executor = Executor()
bp = Blueprint('session', __name__, url_prefix='/session')
bp.before_request(_before_requests)

@bp.route('/', methods=['GET'])
def info():
    """**Flask GET rule**.

    Information about the session.
    ---
    get:
        summary: Information about the session.
        description: Returns information about the session.
        tags:
            - Session
        parameters:
            - sessionToken
        responses:
            200:
                description: Session was found.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                lastRequest:
                                    type: string
                                    format: date-time
                                    description: The datetime of last request of the session.
                                    example: "Thu, 11 Feb 2021 12:55:51 GMT"
                                numberOfDatasets:
                                    type: integer
                                    description: The numbers of datasets created during this session.
                                    example: 9
                                activeDataset:
                                    $ref: "#components/schemas/datasetExtendedInfo"
            401: noSessionResponse
    """
    number_of_datasets = Datasets.query.filter_by(session=g.session['uuid'], deleted=False).count()
    dataset = db_dataset_extended_info(g.session['uuid'], uuid=g.session['active_instance'])

    return make_response({'lastRequest': g.session['last_request'], 'numberOfDatasets': number_of_datasets, 'activeDataset': dataset}, 200)


@bp.route('/ingest', methods=['POST'])
def ingest():
    """**Flask POST rule**.

    Uploads a spatial asset to subsequently use for geometric operations.
    ---
    post:
        summary: Uploads a spatial asset to subsequently use for geometric operations.
        description: Ingests a spatial asset to session, in order to use it subsequently for geometric operations. The asset could be either uploaded either defined by a resolvable path. On succes, the dataset will be accessed by the label given in the request body, and would be available only within the session.
        tags:
            - Session
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: ingestForm
                multipart/form-data:
                    schema: ingestFormMultipart
        responses:
            202: deferredResponse
            400: validationErrorResponse
    """
    token = g.session['token']
    create_session(token)
    form = IngestFileForm() if 'resource' in request.files.keys() else IngestPathForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)
    if 'resource' in request.files.keys():
        src_filename = secure_filename(form.resource.data.filename)
        src_file = os.path.join(g.session['working_path'], src_filename)
        form.resource.data.save(src_file)
    else:
        src_file = form.resource.data

    kwargs = {}
    for arg in ['crs', 'encoding', 'delimiter', 'lat', 'lon', 'geom']:
        value = getattr(form, arg).data
        if value != '':
            kwargs[arg] = value

    try:
        _get_idempotency_key(request.headers)
    except NotUniqueViolation:
        return make_response({"X-Idempotency-Key": ['Field must be unique.']})
    queue = db_queue(session=g.session['uuid'], request='ingest', label=form.label.data, idempotent_key=g.session['idempotent_key'])
    future = executor.submit(ingest_process, queue, g.session, src_file, form.label.data, **kwargs)
    future.add_done_callback(_ingest_callback)

    return make_response({'ticket': queue['ticket'], 'statusUri': "/jobs/status?ticket={ticket}".format(ticket=queue['ticket'])}, 202)


@bp.route('/close', methods=['DELETE'])
def close():
    """**Flask DELETE rule**.

    Closes a session.
    ---
    delete:
        summary: Closes a session.
        description: All ingested and created datasets within the session are destroyed, and the session is closed.
        tags:
            - Session
        parameters:
            - sessionToken
        responses:
            200:
                description: The session was closed.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                status:
                                    type: string
                                    example: ok
            401: noSessionResponse
            404:
                description: The session was not found.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                status:
                                    type: string
                                    example: Session does not exist.
    """
    token = g.session['token']
    try:
        close_session(token)
    except SessionDoesNotExist as e:
        return make_response({'status': 'Session does not exist.'}, 404)
    return make_response({'status': 'ok'}, 200)


@bp.route('/set_active', methods=['PUT'])
def set_active():
    """**Flask PUT rule**.

    Change the active dataset for the session.
    ---
    put:
        summary: Change the active dataset for the session.
        description: Set the dataset specified by the given 'label' as the active dataset for the session.
        tags:
            - Session
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema:
                        type: object
                        properties:
                            label:
                                type: string
                                description: The label of the dataset which will become the active for the session.
                                example: dataset2
                        required: ['label']
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
    """
    response = get_session()
    if isinstance(response, Response):
        return response
    form = SetActiveForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)
    dataset = Datasets().get(session=g.session['uuid'], label=form.label.data, deleted=False)
    db_update_session(g.session['uuid'], active_instance=dataset['uuid'])
    return make_response(dataset['meta'], 200)


@bp.route('/export', methods=['GET', 'POST'])
def export():
    """**Flask GET, POST rule**.

    Returns a list with the exports requested in the session.
    ---
    get:
        summary: Returns a list with the exports requested in the session.
        tags:
            - Session
        parameters:
            - sessionToken
        responses:
            200: exportsListResponse
            401: noSessionResponse
    post:
        summary: Exports a database to file.
        tags:
            - Session
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: exportForm
        responses:
            202: deferredResponse
            400: validationErrorResponse
            401: noSessionResponse
    """
    from geometry_service.database.model import Exports, Datasets

    if request.method == 'GET':
        return make_response(jsonify(db_export_list(g.session['uuid'])), 200)

    form = ExportForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)
    if form.label.data != '':
        dataset = Datasets().get(session=g.session['uuid'], label=form.label.data, deleted=False)
    else:
        dataset = Datasets().get(uuid=g.session['active_instance'], deleted=False)
    try:
        _get_idempotency_key(request.headers)
    except NotUniqueViolation:
        return make_response({"X-Idempotency-Key": ['Field must be unique.']})
    driver = form.driver.data or dataset['meta']['driver']
    export = Exports().get(dataset=dataset['uuid'], driver=driver)
    if export is not None and export['status'] is not None:
        return make_response('Export is already %s.' % (export['status']), 400)
    export = db_log_export(dataset=dataset['uuid'], driver=driver)
    queue = db_queue(session=g.session['uuid'], request='export', label=dataset['label'], export=export['uuid'], idempotent_key=g.session['idempotent_key'])

    path = g.session['working_path']
    kwargs = {}
    for arg in ['crs', 'encoding', 'delimiter', 'name_field', 'description_field']:
        value = getattr(form, arg).data
        if value != '':
            kwargs[arg] = value

    future = executor.submit(export_process, queue, g.session, dataset['table'], path, driver, copy_to_output=form.copy_to_output.data, **kwargs)
    future.add_done_callback(_export_callback)

    return make_response({'ticket': queue['ticket'], 'statusUri': "/jobs/status?ticket={ticket}".format(ticket=queue['ticket'])}, 202)
