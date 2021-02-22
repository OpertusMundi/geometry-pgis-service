from wtforms import StringField, BooleanField, FloatField
from wtforms.validators import Optional, DataRequired, Regexp, Length
from .validators import UniqueLabel, NotUnderProcessLabel, Dataset
from . import BaseForm

class ConstructiveForm(BaseForm):
    """The form for constructive requests.

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
