import os
from flask import Blueprint, make_response, g, request
from flask.wrappers import Response
from ..context import get_session
from geometry_service.database.postgis import Postgis
from geometry_service.database.actions import db_add_dataset, db_log_action
from geometry_service.database.model import Datasets
from geometry_service.loggers import logger
from ..forms.constructive import ConstructiveForm


def _before_requests():
    """Executed before each request for this blueprint.

    Get the session details of the corresponding token, validates the form, and retrieves the dataset from database. The dataset and the form are stored as global flask objects, to be accessible from the requests.

    Returns:
        (None|Response): In case of validation error, returns a Flask response, None otherwise.
    """
    response = get_session()
    logger.info('API request [endpoint: "%s", token: "%s"]', request.endpoint, g.session['token'])
    if isinstance(response, Response):
        return response
    form = ConstructiveForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)
    if form.src.data == '':
        dataset = Datasets().get(uuid=g.session['active_instance'])
        if dataset is None:
            return make_response({"status": "No active dataset found."}, 404)
    else:
        dataset = Datasets().get(session=g.session['uuid'], label=form.src.data, deleted=False)
    g.dataset = dataset
    g.form = form


def _constructive(action, label, dataset, args=None):
    """Creates a new dataset with geometries constructed from applying an action to the original geometries.

    Creates a new DB View with the new dataset, and logs the action to DB.

    Arguments:
        action (str): The PostGIS function that will be used to construct the new geometries.
        label (str): The label given to the new dataset.
        dataset (dict): The dataset DB record.

    Keyword Arguments:
        args (str|list): An additional argument, or a list of additional arguments, for the PostGIS function (default: {None})

    Returns:
        (dict): Metadata for the new view dataset.
    """
    postgis = Postgis(g.session['db_schema'])
    view = postgis.create_view_action(label, dataset['table'], action, column='geom', args=args)
    meta = dataset['meta']
    tgt = db_add_dataset(session=g.session['uuid'], label=label, table=view, meta=meta)
    db_log_action(session=g.session['uuid'], action=request.endpoint, src_ds=dataset['uuid'], result_ds=tgt['uuid'])
    return meta


# FLASK ROUTES

bp = Blueprint('constructive', __name__, url_prefix='/constructive')
bp.before_request(_before_requests)

@bp.route('/centroid', methods=['POST'])
def centroid():
    """**Flask POST rule**.

    Constructs new geometries computing the centroid.
    ---
    post:
        summary: Constructs new geometries computing the centroid.
        description: Creates a new dataset with the geometry of each feature replaced by its centroid. The new dataset will become the active dataset of the session, and will subsequently be accessible using the provided label.
        tags:
            - Constructive
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: constructiveForm
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _constructive('ST_Centroid', g.form.label.data, g.dataset)
    return make_response(meta, 200)


@bp.route('/convex_hull', methods=['POST'])
def convex_hull():
    """**Flask POST rule**.

    Constructs new geometries computing the convex hull.
    ---
    post:
        summary: Constructs new geometries computing the convex hull.
        description: Creates a new dataset with the geometry of each feature replaced by its convex hull. The new dataset will become the active dataset of the session, and will subsequently be accessible using the provided label.
        tags:
            - Constructive
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: constructiveForm
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _constructive('ST_ConvexHull', g.form.label.data, g.dataset)
    return make_response(meta, 200)


@bp.route('/flip_geometries', methods=['POST'])
def flip_geometries():
    """**Flask POST rule**.

    Constructs new geometries flipping their coordinates.
    ---
    post:
        summary: Constructs new geometries flipping their coordinates.
        description: Creates a new dataset with the geometry of each feature replaced by a new geometry with flipped coordinates. Useful for fixing geometries which contain coordinates expressed as latitude/longitude (Y,X).<br/>The new dataset will become the active dataset of the session, and will subsequently be accessible using the provided label.
        tags:
            - Constructive
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: constructiveForm
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _constructive('ST_FlipCoordinates', g.form.label.data, g.dataset)
    return make_response(meta, 200)


@bp.route('/make_valid', methods=['POST'])
def make_valid():
    """**Flask POST rule**.

    Constructs new valid geometries.
    ---
    post:
        summary: Constructs new valid geometries.
        description: Creates a new dataset with the invalid geometries replaced by their valid representation, without losing any of the input vertices. Already-valid geometries are returned without further intervention.<br/>The new dataset will become the active dataset of the session, and will subsequently be accessible using the provided label.
        tags:
            - Constructive
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: constructiveForm
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _constructive('ST_MakeValid', g.form.label.data, g.dataset)
    return make_response(meta, 200)
