import os
from flask import Blueprint, make_response, request, g, jsonify, send_file
from flask.wrappers import Response
from ..context import get_session
from geometry_service.database.postgis import Postgis
from geometry_service.database.actions import db_dataset_extended_info
from geometry_service.loggers import logger

def _before_requests():
    """Executed before each request for this blueprint.

    Get the session details of the corresponding token, and retrieves the dataset from database. The dataset is stored as global flask object, to be accessible from the requests.

    Returns:
        (None|Response): In case of validation error, returns a Flask response, None otherwise.
    """
    from geometry_service.database.model import Datasets
    response = get_session()
    logger.info('API request [endpoint: "%s", token: "%s"]', request.endpoint, g.session['token'])
    if isinstance(response, Response):
        return response
    if request.endpoint not in ['dataset.info', 'dataset.download']:
        label = request.view_args['label']
        dataset = None
        if label is None:
            error_msg = "No active dataset found."
            if g.session['active_instance'] is not None:
                dataset = Datasets().get(uuid=g.session['active_instance'], deleted=False)
        else:
            error_msg = "Dataset with label '%s' not found." % (label)
            dataset = Datasets().get(session=g.session['uuid'], label=label, deleted=False)
        if dataset is None:
            return make_response({"status": error_msg}, 404)
        g.dataset = dataset


# FLASK ROUTES

bp = Blueprint('dataset', __name__, url_prefix='/dataset')
bp.before_request(_before_requests)

@bp.route('/', methods=['GET'])
def info():
    """**Flask GET rule**.

    Returns a list of the available datasets in the session.
    ---
    get:
        summary: Returns a list of the available datasets in the session.
        parameters:
            - sessionToken
        tags:
            - Dataset
        responses:
            200:
                description: The list with the session's datasets.
                content:
                    application/json:
                        schema:
                            type: array
                            description: Each item corresponds to a dataset, ordered by creation date.
                            items:
                                $ref: "#components/schemas/datasetExtendedInfo"
            401: noSessionResponse
    """
    datasets = db_dataset_extended_info(g.session['uuid'])
    return jsonify(datasets)


@bp.route('/view', defaults={'label': None}, methods=['GET'])
def view_without_label(label=None):
    """**Flask GET rule**.

    Paginated tabular view of the active dataset.
    ---
    get:
        summary: Paginated tabular view of the active dataset.
        parameters:
            - sessionToken
            - page
            - resultsPerPage
    """
    return _view(label=label)

@bp.route('/view/<label>', methods=['GET'])
def view_with_label(label):
    """**Flask GET rule**.

    Paginated tabular view of the dataset corresponding to the given 'label'.
    ---
    get:
        summary: Paginated tabular view of the dataset corresponding to the given 'label'.
        parameters:
            - sessionToken
            - label
            - page
            - resultsPerPage
    """
    return _view(label=label)

def _view(label=None):
    """
        tags:
            - Dataset
        responses:
            200:
                description: A tabular view of the dataset subset for the given page.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                info:
                                    $ref: "#/components/schemas/paginationInfo"
                                data:
                                    type: array
                                    description: The actual data for the given page.
                                    items:
                                        type: object
                                        description: The key is the attribute name.
                                        additionalProperties:
                                            anyOf:
                                                - type: string
                                                - type: number
                                    example:
                                        -
                                            id: 981
                                            name: example
                                            geometry: POLYGON((6.4 49., 6.5 50., 6.6 49.5, 6.4 49.))
                                        -
                                            id: 982
                                            name: other_example
                                            geometry: POINT(6.1659779 49.6150126)
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    page = request.args.get('page', default=1, type=int)
    results_per_page = min(request.args.get('results_per_page', default=10, type=int), int(os.environ['MAX_RESULTS_PAGE']))
    postgis = Postgis(g.session['db_schema'])
    result = postgis.view(g.dataset['table'], page=page, results_per_page=results_per_page)
    return make_response(result, 200)
view_without_label.__doc__ += _view.__doc__
view_with_label.__doc__ += _view.__doc__


@bp.route('/geojson', defaults={'label': None}, methods=['GET'])
def geojson_without_label(label=None):
    """**Flask GET rule**.

    Paginated GeoJSON view of the active dataset.
    ---
    get:
        summary: Paginated GeoJSON view of the active dataset.
        parameters:
            - sessionToken
            - page
            - resultsPerPage
    """
    return _geojson(label=label)

@bp.route('/geojson/<label>', methods=['GET'])
def geojson_with_label(label):
    """**Flask GET rule**.

    Paginated GeoJSON view of the dataset corresponding to the given 'label'.
    ---
    get:
        summary: Paginated GeoJSON view of the dataset corresponding to the given 'label'.
        parameters:
            - sessionToken
            - label
            - page
            - resultsPerPage
    """
    return _geojson(label=label)

def _geojson(label=None):
    """
        tags:
            - Dataset
        responses:
            200:
                description: A GeoJSON view of the dataset subset for the given page.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                info:
                                    $ref: "#/components/schemas/paginationInfo"
                                data:
                                    $ref: "#/components/schemas/geoJSON"
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    page = request.args.get('page', default=1, type=int)
    results_per_page = min(request.args.get('results_per_page', default=10, type=int), int(os.environ['MAX_RESULTS_PAGE']))
    postgis = Postgis(g.session['db_schema'])
    result = postgis.geojson(g.dataset['table'], page=page, results_per_page=results_per_page)
    return make_response(result, 200)
geojson_without_label.__doc__ += _geojson.__doc__
geojson_with_label.__doc__ += _geojson.__doc__


@bp.route('/download/<filename>', methods=['GET'])
def download(filename):
    """**Flask GET rule**.

    Download an exported file.
    ---
    get:
        summary: Download an exported file.
        parameters:
            - sessionToken
            -
                in: path
                name: filename
                schema:
                    type: string
                description: The filename to download.
        tags:
            - Dataset
        responses:
            200:
                description: The requested file.
                content:
                    application/x-tar:
                        schema:
                            type: string
                            format: binary
            401: noSessionResponse
            404:
                description: File not found.
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                status:
                                    type: string
                                    description: Error message
                                    example: File not found.
    """
    path = os.path.join(g.session['working_path'], filename)
    if os.path.isfile(path):
        file_content = open(path, 'rb')
        response = send_file(file_content, attachment_filename=filename, as_attachment=True)
        response.headers['Content-Length'] = str(os.path.getsize(path))
        return response
    else:
        return make_response({"status": "File not found."}, 404)
