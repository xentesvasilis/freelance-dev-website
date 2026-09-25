import secrets
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


STATUSES = ("new", "contacted", "qualified", "won", "lost", "archived")


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
