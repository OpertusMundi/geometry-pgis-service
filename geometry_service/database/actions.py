"""A collection of DB actions."""

from sqlalchemy.sql import func
from hashlib import md5
import os
from uuid import uuid4
from . import db
from .model import *
from geometry_service.exceptions import SessionDoesNotExist

def db_create_session(token):
    """Prepares the database for a new session.

    Adds a record to the session table, and creates the schema to store the session datasets.

    Arguments:
        token (str): The session token.

    Returns:
        (dict): The new session record.
    """
    session = Session.query.filter_by(token=token, active=True).first()
    if session is None:
        uuid = str(uuid4())
        hashed = md5(str(uuid).encode()).hexdigest()
        schema = 'data_' + hashed
        working_path = os.path.join(os.environ['WORKING_DIR'], 'session', hashed)
        session = Session(uuid=uuid, token=token, active=True, schema=schema, working_path=working_path)
        db.session.execute('DROP SCHEMA IF EXISTS %s' % (session.schema))
        db.session.execute('CREATE SCHEMA %s' % (session.schema))
        db.session.add(session)
        db.session.commit()
    else:
        session.last_request = func.now()
        db.session.commit()
    return dict(session)


def db_close_session(token):
    """Closes a session in the database.

    Updates the corresponding record in session table, and drops the schema with the session datasets.

    Arguments:
        token (str): The session token.

    Raises:
        SessionDoesNotExist: No session associated with the token found.
    """
    session = Session.query.filter_by(token=token, active=True).first()
    if session is None:
        raise SessionDoesNotExist('Session does not exist')
    else:
        session.active = False
        session.active_instance = None
        db.session.execute('DROP SCHEMA IF EXISTS %s CASCADE' % (session.schema))
        db.session.commit()


def db_update_session(uuid, commit=True, **data):
    """Updates a session record.

    Arguments:
        uuid (str): The uuid PK of the record.
        **data: The data to update on the session.

    Keyword Arguments:
        commit (bool): Whether to commit the transanction (default: (True))

    Returns:
        (dict): The updated session record.

    Raises:
        SessionDoesNotExist: [description]
    """
    session = Session.query.get(uuid)
    if session is None:
        raise SessionDoesNotExist
    for key in data.keys():
        setattr(session, key, data[key])
    if commit:
        db.session.commit()
    return dict(session)


def db_add_dataset(commit=True, **data):
    """Adds a dataset record.

    Arguments:
        **data: The dataset record data.

    Keyword Arguments:
        commit (bool): Whether to commit the transanction (default: (True))

    Returns:
        (dict): The inserted dataset record.
    """
    assert isinstance(data, dict)
    fields = data.keys()
    assert 'label' in fields
    assert 'session' in fields
    assert 'table' in fields
    assert 'meta' in fields
    dataset = Datasets(**data)
    db.session.add(dataset)
    if commit:
        db.session.commit()
    return dict(dataset)


def db_log_export(**data):
    """Adds an export record.

    Arguments:
        **data: The export record data.

    Returns:
        (dict): The inserted export record.
    """
    assert 'dataset' in data.keys()
    assert 'driver' in data.keys()
    export = Exports(**data)
    db.session.add(export)
    db.session.commit()
    return dict(export)


def db_log_action(**data):
    """Adds an action record.

    Arguments:
        **data: The action record data.

    Returns:
        (dict): The inserted action record.
    """
    fields = data.keys()
    assert 'session' in fields
    assert 'action' in fields
    assert 'src_ds' in fields
    assert 'result_ds' in fields
    action = Actions(**data)
    db.session.add(action)
    db.session.commit()

    return dict(action)


def db_queue(**data):
    """Add a record to queue table.

    Arguments:
        **data: The queue record data.

    Returns:
        (dict): The inserted queue record.
    """
    fields = data.keys()
    assert 'request' in fields
    assert 'label' in fields
    queue = Queue(**data)
    db.session.add(queue)
    db.session.commit()
    return dict(queue)


def db_dataset_extended_info(session, uuid=None):
    """Returns extended information about datasets in the session.

    Information about all datasets or a specific dataset in the session will be retrieved. It is combined query, joining the actions and datasets tables.

    Arguments:
        session (str): The session uuid.

    Keyword Arguments:
        uuid (str): The dataset uuid (PK). If not None, only the specific dataset will be queried, otherwise all datasets of the session will be involved in the query (default: (None))

    Returns:
        (list|dict): A dictionary with dataset's information (uuid is not None), or a list of such dictionaries (uuid is None).
    """
    from sqlalchemy.orm import aliased
    from sqlalchemy import case
    ds = aliased(Datasets)
    src = aliased(Datasets)
    driver = case([(src.label.is_(None), ds.meta['driver'])], else_=None)
    datasets = Datasets.query \
        .with_entities(
            ds.label, ds.created, ds.meta['bbox'], ds.meta['epsg'], ds.meta['features'], \
            driver, src.label, Actions.action
        )
    if uuid is None:
        datasets = datasets.filter(ds.session==session, ds.deleted is not False)
    else:
        datasets = datasets.filter(ds.session==session, ds.deleted is not False, ds.uuid == uuid)

    datasets = datasets \
        .join(Actions, ds.uuid==Actions.result_ds, isouter=True) \
        .join(src, Actions.src_ds == src.uuid, isouter=True) \
        .order_by(ds.created.asc())

    if uuid is None:
        datasets = [dict(zip(['label', 'created', 'bbox', 'epsg', 'features', 'driver', 'source', 'action'], ds)) for ds in datasets.all()]
    else:
        datasets = dict(zip(['label', 'created', 'bbox', 'epsg', 'features', 'driver', 'source', 'action'], datasets.first()))

    return datasets


def db_export_list(session):
    """Returns extended information about exports in the session.

    Information about all datasets will be retrieved. It is a combined query, joining the datasets and exports tables, and grouping by dataset label.

    Arguments:
        session (str): The session uuid.

    Returns:
        (list): A list with exports for each dataset.
    """
    from sqlalchemy.orm import aliased
    from sqlalchemy.sql import func
    from sqlalchemy import case

    ds = aliased(Datasets)
    exp = aliased(Exports)
    filename = func.reverse(func.substr(func.reverse(exp.file), 0, func.strpos(func.reverse(exp.file), '/')))
    link = case([(exp.file.isnot(None), func.concat('/dataset/download/', filename))], else_=None)
    json = func.json_build_object('driver', exp.driver, 'link', link, 'output_path', exp.output_path, 'status', exp.status)
    json_agg = func.json_agg(json)
    exports = ds.query \
        .with_entities(ds.label, json_agg) \
        .filter(ds.session==session) \
        .join(exp, exp.dataset==ds.uuid) \
        .group_by(ds.label) \
        .all()

    return [dict(zip(['label', 'exports'], export)) for export in exports]


def db_update_export_status(uuid, status, file, error_msg=None, output_path=None):
    """Updates export status

    Arguments:
        uuid (UUID): Queue table PK.
        status (bool): The export status, True on success, False otherwise.
        file (str): Exported file full path.

    Keyword Arguments:
        error_msg (str): Error message in case of failure.
        output_path (str): The relative path in the output directory.
    """
    from datetime import datetime, timezone
    queue = Queue.query.get(uuid)
    queue.completed = True
    queue.status = status
    queue.execution_time = (datetime.now(timezone.utc) - queue.initiated).total_seconds()
    queue.error_msg = error_msg
    db.session.add(queue)
    export =  Exports.query.get(queue.export)
    export.status = 'completed' if status else 'failed'
    export.file = file
    export.output_path = output_path
    db.session.add(export)
    db.session.commit()


def db_update_ingest_status(uuid, session, dataset, status, error_msg):
    """Updates ingest status.

    Arguments:
        uuid (UUID): Queue table PK.
        session (UUID): Session table PK.
        dataset (dict): The dataset details.
        status (bool): The ingest status; True on success, False otherwise.
        error_msg (str): Error message in case of failure.
    """
    from datetime import datetime, timezone
    queue = Queue.query.get(uuid)
    if status:
        new_dataset = db_add_dataset(session=session, **dataset)
        db_update_session(session, commit=False, active_instance=new_dataset['uuid'])
        queue.dataset = new_dataset['uuid']
    queue.completed = True
    queue.status = status
    queue.error_msg = error_msg
    queue.execution_time = (datetime.now(timezone.utc) - queue.initiated).total_seconds()
    db.session.add(queue)
    db.session.commit()


def db_get_active_jobs():
    """Returns a list with all the active jobs.

    Retrieves the active processes and information about the session each one belongs.

    Returns:
        (list): The list with items the details about each active process.
    """
    from sqlalchemy.orm import aliased

    j = aliased(Queue)
    s = aliased(Session)

    jobs = j.query \
        .with_entities(s.token, s.last_request, j.ticket, j.idempotent_key, j.request, j.initiated) \
        .filter(j.completed==False) \
        .join(s, s.uuid==j.session) \
        .all()

    return [dict(zip(['sessionToken', 'sessionLastRequest', 'ticket', 'idempotencyKey', 'requestType', 'initiated'], job)) for job in jobs]
