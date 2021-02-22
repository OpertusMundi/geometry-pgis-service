from flask_wtf import FlaskForm

class BaseForm(FlaskForm):
    """The WTForms base form, it disables CSRF.

    Extends:
        FlaskForm
    """
    class Meta:
        csrf = False
