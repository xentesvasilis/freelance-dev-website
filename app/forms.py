import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, SelectMultipleField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from wtforms.widgets import CheckboxInput, ListWidget

from .content import CHOICES, tr
from .models import STATUSES


class LocalRequired(DataRequired):
    def __call__(self, form, field):
        return DataRequired(message=tr("required_error"))(form, field)


class LocalLength(Length):
    def __call__(self, form, field):
        return Length(min=self.min, max=self.max, message=tr("length_error"))(form, field)


class LocalEmail(Email):
    def __call__(self, form, field):
        return Email(message=tr("email_error"))(form, field)


def single_line(form, field):
    if field.data and re.search(r"[\x00-\x1f\x7f]", field.data):
        raise ValidationError(tr("unsafe_error"))


def required():
    return LocalRequired()


def bounded(minimum, maximum):
    return LocalLength(min=minimum, max=maximum)


class LocalSelect(SelectField):
    def pre_validate(self, form):
        try:
            super().pre_validate(form)
        except ValidationError:
            raise ValidationError(tr("choice_error")) from None


class LocalMulti(SelectMultipleField):
    def pre_validate(self, form):
        try:
            super().pre_validate(form)
        except ValidationError:
            raise ValidationError(tr("choice_error")) from None


class LeadForm(FlaskForm):
    name = StringField(validators=[required(), bounded(2, 120), single_line])
    email = StringField(validators=[required(), LocalEmail(), bounded(3, 254), single_line])
    phone = StringField(validators=[Optional(), bounded(0, 40), single_line])
    company = StringField(validators=[Optional(), bounded(0, 160), single_line])
    industry = LocalSelect(validators=[required()])
    requirements = LocalMulti(validators=[required()], widget=ListWidget(prefix_label=False), option_widget=CheckboxInput())
    budget = LocalSelect(validators=[required()])
    description = TextAreaField(validators=[required(), bounded(15, 4000)])
    timeframe = LocalSelect(validators=[required()])
    privacy_accept = BooleanField(validators=[required()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, choices in CHOICES.items():
            field = getattr(self, name)
            field.choices = [(key, tr(label)) for key, label in choices]
            if name != "requirements":
                field.choices.insert(0, ("", tr("select")))
        for name in ("name", "email", "phone", "company", "description"):
            field = getattr(self, name)
            if isinstance(field.data, str):
                field.data = field.data.strip()


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=256)])


class StatusForm(FlaskForm):
    status = SelectField("Status", choices=[(s, s.title()) for s in STATUSES], validators=[DataRequired()])


class NotesForm(FlaskForm):
    notes = TextAreaField("Internal notes", validators=[Length(max=10000)])
