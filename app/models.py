import secrets
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm import validates

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


STATUSES = ("new", "contacted", "qualified", "won", "lost", "archived")
PROJECT_STATUSES = ("proposal", "proposal_sent", "accepted", "in_development", "waiting_for_client",
                    "testing", "delivered", "maintenance", "on_hold", "cancelled")
PROJECT_PRIORITIES = ("low", "normal", "high", "urgent")
PROJECT_MILESTONES = {"accepted": "accepted_at", "in_development": "development_started_at",
                      "testing": "testing_started_at", "delivered": "delivered_at",
                      "maintenance": "maintenance_started_at"}


class ProjectCase(db.Model):
    """Private operational record, never a published PortfolioProject."""
    __table_args__ = (
        db.CheckConstraint("status IN ('proposal','proposal_sent','accepted','in_development','waiting_for_client','testing','delivered','maintenance','on_hold','cancelled')", name="valid_project_status"),
        db.CheckConstraint("priority IN ('low','normal','high','urgent')", name="valid_project_priority"),
        db.CheckConstraint("quoted_price_cents IS NULL OR quoted_price_cents >= 0", name="nonnegative_project_price"),
        db.CheckConstraint("currency = 'EUR'", name="project_currency_eur"),
        db.CheckConstraint("target_delivery_date IS NULL OR target_start_date IS NULL OR target_delivery_date >= target_start_date", name="valid_project_dates"),
    )
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id", ondelete="SET NULL"), unique=True)
    lead = db.relationship("Lead", backref=db.backref("project_case", uselist=False, passive_deletes=True))
    title = db.Column(db.String(200), nullable=False)
    client_name = db.Column(db.String(120), nullable=False)
    client_email = db.Column(db.String(254), nullable=False)
    client_phone = db.Column(db.String(40))
    company = db.Column(db.String(160))
    industry = db.Column(db.String(120), index=True)
    project_summary = db.Column(db.Text, nullable=False)
    internal_notes = db.Column(db.Text)
    package_name = db.Column(db.String(120))
    quoted_price_cents = db.Column(db.Integer)
    currency = db.Column(db.String(3), nullable=False, default="EUR", server_default="EUR")
    status = db.Column(db.String(30), nullable=False, default="proposal", server_default="proposal", index=True)
    priority = db.Column(db.String(10), nullable=False, default="normal", server_default="normal", index=True)
    target_start_date = db.Column(db.Date)
    target_delivery_date = db.Column(db.Date, index=True)
    accepted_at = db.Column(db.DateTime(timezone=True))
    development_started_at = db.Column(db.DateTime(timezone=True))
    testing_started_at = db.Column(db.DateTime(timezone=True))
    delivered_at = db.Column(db.DateTime(timezone=True))
    maintenance_started_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow, index=True)

    @validates("status")
    def record_first_milestone(self, key, value):
        if value not in PROJECT_STATUSES:
            raise ValueError("Invalid project status")
        milestone = PROJECT_MILESTONES.get(value)
        if milestone and getattr(self, milestone) is None:
            setattr(self, milestone, utcnow())
        return value

    @property
    def quoted_price_display(self):
        if self.quoted_price_cents is None:
            return "—"
        euros, cents = divmod(self.quoted_price_cents, 100)
        return f"€{euros:,}" + (f".{cents:02d}" if cents else "")


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Lead(db.Model):
    __table_args__ = (db.CheckConstraint("status IN ('new','contacted','qualified','won','lost','archived')", name="valid_lead_status"),)
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    phone = db.Column(db.String(40))
    company = db.Column(db.String(160))
    industry = db.Column(db.String(40), nullable=False)
    requirements_json = db.Column(db.JSON, nullable=False)
    budget_range = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text, nullable=False)
    timeframe = db.Column(db.String(40), nullable=False)
    language = db.Column(db.String(2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="new", index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    contacted_at = db.Column(db.DateTime(timezone=True))
    notes = db.Column(db.Text)
    privacy_accepted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    privacy_version = db.Column(db.String(30), nullable=False, default="2026-09-draft")
    email_status = db.Column(db.String(20), nullable=False, default="pending")


class PortfolioProject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), nullable=False, unique=True)
    title = db.Column(db.JSON, nullable=False)
    short_description = db.Column(db.JSON, nullable=False)
    description = db.Column(db.JSON, nullable=False)
    industry = db.Column(db.String(100), nullable=False)
    technologies = db.Column(db.JSON, nullable=False)
    features = db.Column(db.JSON, nullable=False)
    image = db.Column(db.String(255))
    featured = db.Column(db.Boolean, nullable=False, default=False)
    published = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
