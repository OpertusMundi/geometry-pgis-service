from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, BooleanField
from wtforms.validators import Optional, Length, DataRequired, Regexp, AnyOf
from .validators import CRS, UniqueLabel, NotUnderProcessLabel, Encoding, Dataset
from . import BaseForm

class IngestForm(BaseForm):
    """The abstract form for ingest requests.

    Extends:
        BaseForm
    """
    label = StringField('label', validators=[
        DataRequired(),
        Length(min=3, max=255),
        Regexp('^[a-z0-9_]+$', message="Field must contain only latin small letters, numbers or underscore."),
        UniqueLabel(),
        NotUnderProcessLabel()
    ])
    delimiter = StringField('delimiter', validators=[Optional(), Length(min=1, max=2)])
    lat = StringField('lat', validators=[Optional()])
    lon = StringField('lon', validators=[Optional()])
    geom = StringField('geom', validators=[Optional()])
    crs = StringField('crs', validators=[Optional(), CRS()])
    encoding = StringField('encoding', validators=[Optional(), Encoding()])

class IngestFileForm(IngestForm):
    """The form for ingest requests with streaming file.

    Extends:
        IngestForm
    """
    resource = FileField('resource', validators=[FileRequired()])

class IngestPathForm(IngestForm):
    """The form for ingest requests with file path.

    Extends:
        IngestForm
    """
    resource = StringField('resource', validators=[DataRequired()])

class SetActiveForm(BaseForm):
    """The form for set active dataset requests.

    Extends:
        BaseForm
    """
    label = StringField('label', validators=[DataRequired(), Dataset()])

class ExportForm(BaseForm):
    """The form for export requests.

    Extends:
        BaseForm
    """
    label = StringField('label', validators=[Optional(), Dataset()])
    driver = StringField('driver', validators=[Optional(), AnyOf(['CSV', 'ESRI Shapefile', 'GeoJSON', 'GPKG', 'MapInfo File', 'DGN', 'KML'])])
    crs = StringField('crs', validators=[Optional(), CRS()])
    delimiter = StringField('delimiter', validators=[Optional(), Length(min=1, max=1)])
    name_field = StringField('name_field', validators=[Optional()])
    description_field = StringField('description_field', validators=[Optional()])
    encoding = StringField('encoding', validators=[Optional(), Encoding()])
    copy_to_output = BooleanField('copy_to_output', default=False, validators=[Optional()])
