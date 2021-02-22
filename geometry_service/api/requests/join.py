import os
from flask import Blueprint, make_response, request, g
from flask.wrappers import Response
import pyproj
from ..context import get_session
from geometry_service.database.postgis import Postgis
from geometry_service.database.actions import db_add_dataset, db_log_action
from geometry_service.database.model import Datasets
from ..forms.join import JoinForm, JoinDistanceForm
from geometry_service.loggers import logger

def _before_requests():
    """Executed before each request for this blueprint.

    Get the session details of the corresponding token, validates the form, and retrieves main dataset from database. The dataset and the form are stored as global flask objects, to be accessible from the requests.

    Returns:
        (None|Response): In case of validation error, returns a Flask response, None otherwise.
    """
    response = get_session()
    logger.info('API request [endpoint: "%s", token: "%s"]', request.endpoint, g.session['token'])
    if isinstance(response, Response):
        return response
    if request.endpoint == 'join.within_distance':
        form = JoinDistanceForm()
    else:
        form = JoinForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)
    if form.left.data == '':
        dataset = Datasets().get(uuid=g.session['active_instance'])
        if dataset is None:
            return make_response({"status": "No active dataset found."}, 404)
    else:
        dataset = Datasets().get(session=g.session['uuid'], label=form.left.data, deleted=False)
    g.dataset = dataset
    g.form = form


def _join(action, label, join, join_type='outer', args=None, srid=None):
    meta = g.dataset['meta']
    postgis = Postgis(g.session['db_schema'])
    view = postgis.create_view_join(label, g.dataset['table'], join, action, join_type=join_type, args=args, srid=srid)
    tgt = db_add_dataset(session=g.session['uuid'], label=label, table=view, meta=meta)
    db_log_action(session=g.session['uuid'], action=request.endpoint, src_ds=g.dataset['uuid'], result_ds=tgt['uuid'])
    return meta


# FLASK ROUTES

bp = Blueprint('join', __name__, url_prefix='/join')
bp.before_request(_before_requests)

@bp.route('/contains', methods=['POST'])
def contains():
    """**Flask POST rule**.

    Apply spatial join on two datasets drived by contains relationship.
    ---
    post:
        summary: Apply spatial join on two datasets drived by contains relationship.
        description: Creates a joined dataset on the condition that the geometry of the second dataset (**right**) is completely inside the geometry of the first (**left**). The new dataset contains attributes from both datasets, prefixed with the label of each dataset, and geometry from the left dataset.
        tags:
            - Join
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: joinForm
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _join('ST_Contains', g.form.label.data, g.form.right.data, join_type=g.form.join_type.data)
    return make_response(meta, 200)

@bp.route('/intersects', methods=['POST'])
def intersects():
    """**Flask POST rule**.

    Apply spatial join on two datasets drived by intersects relationship.
    ---
    post:
        summary: Apply spatial join on two datasets drived by intersects relationship.
        description: Creates a joined dataset on the condition that two geometries intersects. The new dataset contains attributes from both datasets, prefixed with the label of each dataset, and geometry from the left dataset.
        tags:
            - Join
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: joinForm
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _join('ST_Intersects', g.form.label.data, g.form.right.data, join_type=g.form.join_type.data)
    return make_response(meta, 200)

@bp.route('/within', methods=['POST'])
def within():
    """**Flask POST rule**.

    Apply spatial join on two datasets drived by within relationship.
    ---
    post:
        summary: Apply spatial join on two datasets drived by within relationship.
        description: Creates a joined dataset on the condition that the geometry of the first dataset (**left**) is completely inside the geometry of the other (**right**). The new dataset contains attributes from both datasets, prefixed with the label of each dataset, and geometry from the left dataset.
        tags:
            - Join
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: joinForm
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _join('ST_Within', g.form.label.data, g.form.right.data, join_type=g.form.join_type.data)
    return make_response(meta, 200)

@bp.route('/within_distance', methods=['POST'])
def within_distance():
    """**Flask POST rule**.

    Apply spatial join on two datasets drived by within distance relationship.
    ---
    post:
        summary: Apply spatial join on two datasets drived by within distance relationship.
        description: Creates a joined dataset on the condition that two geometries are within the given distance. The new dataset contains attributes from both datasets, prefixed with the label of each dataset, and geometry from the left dataset.
        tags:
            - Join
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: joinDistanceForm
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    ds_right = Datasets().get(session=g.session['uuid'], label=g.form.right.data, deleted=False)
    srid = g.dataset['meta']['epsg'] if ds_right['meta']['epsg'] != g.dataset['meta']['epsg'] else None
    meta = _join('ST_DWithin', g.form.label.data, g.form.right.data, join_type=g.form.join_type.data, args=[g.form.distance.data], srid=srid)
    return make_response(meta, 200)