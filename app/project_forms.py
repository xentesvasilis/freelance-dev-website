import re
from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from .crm import crm_label
from .forms import single_line
from .models import PROJECT_PRIORITIES, PROJECT_STATUSES


def no_null_bytes(form, field):
    if field.data and "\x00" in field.data:
        raise ValidationError("Invalid text.")


class ProjectStatusForm(FlaskForm):
    status = SelectField("Status", choices=[(s, s) for s in PROJECT_STATUSES], validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.choices = [(s, crm_label(s)) for s in PROJECT_STATUSES]
        self.status.label.text = crm_label("Status")


class ProjectForm(ProjectStatusForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=200), single_line])
    client_name = StringField("Client name", validators=[DataRequired(), Length(max=120), single_line])
    client_email = StringField("Email", validators=[DataRequired(), Email(), Length(max=254), single_line])
    client_phone = StringField("Phone", validators=[Optional(), Length(max=40), single_line])
    company = StringField("Company", validators=[Optional(), Length(max=160), single_line])
    industry = StringField("Industry", validators=[Optional(), Length(max=120), single_line])
    project_summary = TextAreaField("Summary", validators=[DataRequired(), Length(max=10000), no_null_bytes])
    internal_notes = TextAreaField("Internal notes", validators=[Optional(), Length(max=10000), no_null_bytes])
    package_name = StringField("Package", validators=[Optional(), Length(max=120), single_line])
    quoted_price = StringField("Quoted price (EUR)", validators=[Optional(), Length(max=16)])
    priority = SelectField("Priority", choices=[(p, p) for p in PROJECT_PRIORITIES], validators=[DataRequired()])
    target_start_date = DateField("Target start", validators=[Optional()])
    target_delivery_date = DateField("Target delivery", validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self:
            field.label.text = crm_label(field.label.text)
            if isinstance(field.data, str):
                field.data = field.data.strip()
        self.priority.choices = [(p, crm_label(p)) for p in PROJECT_PRIORITIES]

    def validate_quoted_price(self, field):
        if not re.fullmatch(r"\d{1,8}(?:\.\d{1,2})?", field.data, flags=re.ASCII):
            raise ValidationError(crm_label("Use a nonnegative amount with at most two decimal places, e.g. 1700.50."))
        if Decimal(field.data) * 100 > 2147483647:
            raise ValidationError(crm_label("Use a nonnegative amount with at most two decimal places, e.g. 1700.50."))

    def validate_target_delivery_date(self, field):
        if field.data and self.target_start_date.data and field.data < self.target_start_date.data:
            raise ValidationError(crm_label("Delivery must not be before start."))

    @property
    def price_cents(self):
        return int(Decimal(self.quoted_price.data) * 100) if self.quoted_price.data else None


class ConvertProjectForm(FlaskForm):
    confirm = BooleanField(validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.confirm.label.text = crm_label("Confirm creation of a private project. The lead and its status will stay unchanged.")
