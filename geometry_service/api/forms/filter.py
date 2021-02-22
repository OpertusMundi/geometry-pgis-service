from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, BooleanField, FloatField
from wtforms.validators import Optional, DataRequired, Regexp, Length
from .validators import UniqueLabel, NotUnderProcessLabel, CRS, WKT, WKTFile, Dataset
from . import BaseForm

class FilterForm(BaseForm):
    """The abstract form for filter requests.

    Extends:
        BaseForm
    """
    src = StringField('label', validators=[Optional(), Dataset()])
    label = StringField('label', validators=[
        DataRequired(),
        Length(min=3, max=255),
        Regexp('^[a-z0-9_]+$', message="Field must contain only latin small letters, numbers or underscore."),
        UniqueLabel(),
        NotUnderProcessLabel()
    ])
    crs = StringField('crs', validators=[Optional(), CRS()])


class FilterFileForm(FilterForm):
    """The form for filter requests, with a file containing the WKT geometry.

    Extends:
        FilterForm
    """
    wkt = FileField('wkt', validators=[FileRequired(), WKTFile()])


class FilterStringForm(FilterForm):
    """The form for filter requests, with a WKT string.

    Extends:
        FilterForm
    """
    wkt = StringField('wkt', validators=[DataRequired(), WKT()])


class FilterBufferForm(FilterForm):
    """The form for filter requests with buffer.

    Extends:
        FilterForm
    """
    center_x = FloatField('center_x', validators=[DataRequired()])
    center_y = FloatField('center_y', validators=[DataRequired()])
    radius = FloatField('radius', validators=[DataRequired()])
