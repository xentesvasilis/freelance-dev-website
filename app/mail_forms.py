from flask_wtf import FlaskForm
from wtforms import HiddenField
from wtforms.validators import DataRequired, Length


class RetryEmailForm(FlaskForm):
    retry_key = HiddenField(validators=[DataRequired(), Length(max=200)])
