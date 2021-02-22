from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, BooleanField, FloatField
from wtforms.validators import Optional, InputRequired, Regexp, Length, AnyOf, NumberRange
from .validators import UniqueLabel, NotUnderProcessLabel, CRS, WKT, WKTFile, Dataset
from . import BaseForm

class JoinForm(BaseForm):
    left = StringField('label', validators=[InputRequired(), Dataset()])
    right = StringField('label', validators=[InputRequired(), Dataset()])
    label = StringField('label', validators=[
        InputRequired(),
        Length(min=3, max=255),
        Regexp('^[a-z0-9_]+$', message="Field must contain only latin small letters, numbers or underscore."),
        UniqueLabel(),
        NotUnderProcessLabel()
    ])
    join_type = StringField('join_type', default='outer', validators=[Optional(), AnyOf(['inner', 'outer'])])

class JoinDistanceForm(JoinForm):
    distance = FloatField('distance', validators=[InputRequired(), NumberRange(min=0)])
