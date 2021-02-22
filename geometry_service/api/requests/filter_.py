import os
from flask import Blueprint, make_response, request, g
from flask.wrappers import Response
import pyproj
from ..context import get_session
from geometry_service.database.postgis import Postgis
from geometry_service.database.actions import db_add_dataset, db_log_action
from geometry_service.database.model import Datasets
from geometry_service.loggers import logger
from ..forms.filter import FilterFileForm, FilterStringForm, FilterBufferForm

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
    if request.endpoint == 'filter.within_buffer':
        form = FilterBufferForm()
    else:
        form = FilterFileForm() if 'wkt' in request.files.keys() else FilterStringForm()
    if not form.validate_on_submit():
        return make_response(form.errors, 400)
    if form.src.data == '':
        dataset = Datasets().get(uuid=g.session['active_instance'])
        if dataset is None:
            return make_response({"status": "No active dataset found."}, 404)
    else:
        dataset = Datasets().get(session=session['uuid'], label=form.src.data, deleted=False)
    g.dataset = dataset
    g.form = form


def _filter(action, label, dataset, wkt=None, arg=None, crs=None):
    """Creates a new dataset with filtered records.

    Creates a new DB View with the new dataset, and logs the action to the DB. All the records of the dataset that fulfil the condition of the PostGIS function (action) will be included in the view. The argument of the function is either supplied directly with the arg parameter either constructed from the geometry of the wkt parameter.

    Arguments:
        action (str): The PostGIS function that will be used to filter the table.
        label (str): The label given to the new dataset.
        dataset (dict): The dataset DB record.

    Keyword Arguments:
        wkt (str): The WKT to supply to the filter function (required if arg is None; default: {None})
        arg (str): The explicit argument of the filter function (required if wkt is None; default: {None})
        crs (str): The CRS of the WKT; if None the dataset CRS will be assumed (default: {None})

    Returns:
        (dict): Metadata for the new view dataset.

    Raises:
        TypeError: When none of wkt, arg is given.
    """
    meta = dataset['meta']
    if wkt is not None:
        srid = pyproj.crs.CRS.from_user_input(crs).to_epsg() if crs is not None and crs != '' else meta['epsg']
        arg = "ST_GeomFromText('{wkt}', {srid})".format(wkt=wkt, srid=srid)
    if arg is None:
        raise TypeError("_filter() missing one of arguments 'wkt', 'arg'")
    postgis = Postgis(g.session['db_schema'])
    view = postgis.create_view_filter(label, dataset['table'], action, arg, column='geom')
    tgt = db_add_dataset(session=g.session['uuid'], label=label, table=view, meta=meta)
    db_log_action(session=g.session['uuid'], action=request.endpoint, src_ds=dataset['uuid'], result_ds=tgt['uuid'])
    return meta


# FLASK ROUTES

bp = Blueprint('filter', __name__, url_prefix='/filter')
bp.before_request(_before_requests)

@bp.route('/contains', methods=['POST'])
def contains():
    """**Flask POST rule**.

    Apply contains filter on the dataset with a given geometry.
    ---
    post:
        summary: Apply contains filter on the dataset with a given geometry.
        description: Creates a new dataset, subset of the source, with the condition that the given geometry is completely inside the geometry of every feature in this dataset. The geometry is provided either as a WKT string either as a text file containing the WKT.
        tags:
            - Filter
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: filterForm
                multipart/form-data:
                    schema: filterFormMultipart
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _filter('ST_Contains', g.form.label.data, g.dataset, wkt=g.form.wkt.data, crs=g.form.crs.data)
    return make_response(meta, 200)


@bp.route('/contains_properly', methods=['POST'])
def contains_properly():
    """**Flask POST rule**.

    Apply contains_properly filter on the dataset with a given geometry.
    ---
    post:
        summary: Apply contains_properly filter on the dataset with a given geometry.
        description: Creates a new dataset, subset of the source, with the condition that the given geometry intersect the geometry of every feature in this dataset, **but** not its boundary (or exterior). The geometry is provided either as a WKT string either as a text file containing the WKT.
        tags:
            - Filter
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: filterForm
                multipart/form-data:
                    schema: filterFormMultipart
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _filter('ST_ContainsProperly', g.form.label.data, g.dataset, wkt=g.form.wkt.data, crs=g.form.crs.data)
    return make_response(meta, 200)


@bp.route('/covers', methods=['POST'])
def covers():
    """**Flask POST rule**.

    Apply covers filter on the dataset with a given geometry.
    ---
    post:
        summary: Apply covers filter on the dataset with a given geometry.
        description: Creates a new dataset, subset of the source, with the condition that no point in the given geometry is outside the geometry of every feature in this dataset. The geometry is provided either as a WKT string either as a text file containing the WKT.
        tags:
            - Filter
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: filterForm
                multipart/form-data:
                    schema: filterFormMultipart
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _filter('ST_Covers', g.form.label.data, g.dataset, wkt=g.form.wkt.data, crs=g.form.crs.data)
    return make_response(meta, 200)


@bp.route('/covered_by', methods=['POST'])
def covered_by():
    """**Flask POST rule**.

    Apply covered_by filter on the dataset with a given geometry.
    ---
    post:
        summary: Apply covered_by filter on the dataset with a given geometry.
        description: Creates a new dataset, subset of the source, with the condition that no point in the geometry of every feature in this dataset is outside the given geometry. The geometry is provided either as a WKT string either as a text file containing the WKT.
        tags:
            - Filter
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: filterForm
                multipart/form-data:
                    schema: filterFormMultipart
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _filter('ST_CoveredBy', g.form.label.data, g.dataset, wkt=g.form.wkt.data, crs=g.form.crs.data)
    return make_response(meta, 200)


@bp.route('/crosses', methods=['POST'])
def crosses():
    """**Flask POST rule**.

    Apply crosses filter on the dataset with a given geometry.
    ---
    post:
        summary: Apply crosses filter on the dataset with a given geometry.
        description: Creates a new dataset, subset of the source, with the condition that the intersection of the given geometry and the geometry of each feature in this dataset *spatially crosses*, that is, the geometries have some, but not all interior points in common. The geometry is provided either as a WKT string either as a text file containing the WKT.
        tags:
            - Filter
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: filterForm
                multipart/form-data:
                    schema: filterFormMultipart
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _filter('ST_Crosses', g.form.label.data, g.dataset, wkt=g.form.wkt.data, crs=g.form.crs.data)
    return make_response(meta, 200)


@bp.route('/disjoint', methods=['POST'])
def disjoint():
    """**Flask POST rule**.

    Apply disjoint filter on the dataset with a given geometry.
    ---
    post:
        summary: Apply disjoint filter on the dataset with a given geometry.
        description: >-
            Creates a new dataset, subset of the source, with only those features that their geometry respects all of the following conditions:

            * **Do not spatially overlap** with the given geometry. Two geometries spatially overlap when they intersect, but one does not completely contain the other.

            * **Do not touch** the given geometry, i.e. if the two geometries have common points, these are not belong only on their exteriors (boundaries).

            * **Do not contain** the given geometry, i.e. there is at least one point of the given geometry outside the feature's geometry.

            > The geometry is provided either as a WKT string either as a text file containing the WKT.
        tags:
            - Filter
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: filterForm
                multipart/form-data:
                    schema: filterFormMultipart
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _filter('ST_Disjoint', g.form.label.data, g.dataset, wkt=g.form.wkt.data, crs=g.form.crs.data)
    return make_response(meta, 200)


@bp.route('/intersects', methods=['POST'])
def intersects():
    """**Flask POST rule**.

    Apply intersects filter on the dataset with a given geometry.
    ---
    post:
        summary: Apply intersects filter on the dataset with a given geometry.
        description: Creates a new dataset, subset of the source, with the condition that the given geometry and the geometry of each feature in this dataset share any portion of space. The geometry is provided either as a WKT string either as a text file containing the WKT.
        tags:
            - Filter
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: filterForm
                multipart/form-data:
                    schema: filterFormMultipart
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _filter('ST_Intersects', g.form.label.data, g.dataset, wkt=g.form.wkt.data, crs=g.form.crs.data)
    return make_response(meta, 200)


@bp.route('/within', methods=['POST'])
def within():
    """**Flask POST rule**.

    Apply within filter on the dataset with a given geometry.
    ---
    post:
        summary: Apply within filter on the dataset with a given geometry.
        description: Creates a new dataset, subset of the source, with the condition that each feature in this dataset is completely inside the given geometry. The geometry is provided either as a WKT string either as a text file containing the WKT.
        tags:
            - Filter
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: filterForm
                multipart/form-data:
                    schema: filterFormMultipart
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    meta = _filter('ST_Within', g.form.label.data, g.dataset, wkt=g.form.wkt.data, crs=g.form.crs.data)
    return make_response(meta, 200)


@bp.route('/within_buffer', methods=['POST'])
def within_buffer():
    """**Flask POST rule**.

    Apply within_buffer filter on the dataset with a given buffer.
    ---
    post:
        summary: Apply within_buffer filter on the dataset with a given buffer.
        description: Creates a new dataset, subset of the source, with the condition that each feature in this dataset is within a given *radius* from a given point defined by *center_x*, *center_y*.
        tags:
            - Filter
        parameters:
            - sessionToken
        requestBody:
            required: true
            content:
                application/x-www-form-urlencoded:
                    schema: filterBufferForm
        responses:
            200: newDatasetResponse
            400: validationErrorResponse
            401: noSessionResponse
            404: datasetNotFoundResponse
    """
    crs = g.form.crs.data
    srid = pyproj.crs.CRS.from_user_input(crs).to_epsg() if crs is not None and crs != '' else g.dataset['meta']['epsg']
    point = "ST_SetSRID( ST_Point( {center_x}, {center_y}), {srid})".format(center_x=g.form.center_x.data, center_y=g.form.center_y.data, srid=srid)
    if srid != g.dataset['meta']['epsg']:
        point = "ST_Transform({point}, {srid})".format(point=point, srid=g.dataset['meta']['epsg'])
    arg = "{point}, {radius}".format(point=point, radius=g.form.radius.data)
    meta = _filter('ST_DWithin', g.form.label.data, g.dataset, arg=arg)
    return make_response(meta, 200)
