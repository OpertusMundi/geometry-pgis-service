"""A collection of custom WTForms Validators."""

from wtforms.validators import ValidationError

class CRS(object):
    """Validates CRS fields."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be a valid CRS.'
        self.message = message

    def __call__(self, form, field):
        import pyproj
        from pyproj.exceptions import CRSError
        try:
            pyproj.crs.CRS.from_user_input(field.data)
        except CRSError:
            raise ValidationError(self.message)


class UniqueLabel(object):
    """Validates a new label for dataset.

    The label given to a new dataset should be unique for the session.
    """
    def __init__(self, message=None):
        if not message:
            message = 'Field must be unique for the session.'
        self.message = message

    def __call__(self, form, field):
        from flask import g
        from geometry_service.database.model import Datasets
        from geometry_service.database import db

        q = Datasets.query.filter_by(session=g.session['uuid'], label=field.data, deleted=False)
        if db.session.query(q.exists()).scalar():
            raise ValidationError(self.message)


class NotUnderProcessLabel(object):
    """Validates a new label for dataset.

    The label given to a new dataset should not have been used for other dataset still in progess.
    """
    def __init__(self, message=None):
        if not message:
            message = 'Field must not be already used for processing request.'
        self.message = message

    def __call__(self, form, field):
        from flask import g
        from geometry_service.database.model import Queue
        from geometry_service.database import db

        q = Queue.query.filter_by(session=g.session['uuid'], request='ingest', label=field.data, completed=False)
        if db.session.query(q.exists()).scalar():
            raise ValidationError(self.message)


class Encoding(object):
    """Validates an encoding field."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be a valid encoding.'
        self.message = message

    def __call__(self, form, field):
        try:
            ''.encode(encoding=field.data, errors='replace')
        except LookupError:
            raise ValidationError(self.message)


class WKT(object):
    """Validates a Well-Known-Text geometry field."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be a valid Well-Known-Text geometry.'
        self.message = message

    def __call__(self, form, field):
        from shapely import wkt
        try:
            wkt.loads(field.data)
        except:
            raise ValidationError(self.message)


class WKTFile(object):
    """Validates the content of a file containing a Well-Known-Text geometry."""
    def __init__(self, message=None):
        if not message:
            message = 'File must contain a valid Well-Known-Text geometry.'
        self.message = message

    def __call__(self, form, field):
        from shapely import wkt
        content = field.data.read().decode()
        try:
            wkt.loads(content)
        except :
            raise ValidationError(self.message)
        else:
            field.data = content


class Dataset(object):
    """Validates the label field for an existing dataset."""
    def __init__(self, message=None):
        if not message:
            message = 'Field must be the label of an existing dataset.'
        self.message = message

    def __call__(self, form, field):
        from flask import g
        from geometry_service.database.model import Datasets
        if field.data != '':
            dataset = Datasets().get(session=g.session['uuid'], label=field.data, deleted=False)
            if dataset is None:
                raise ValidationError(self.message)
