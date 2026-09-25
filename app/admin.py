from functools import wraps

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, limiter
from .forms import LoginForm, NotesForm, StatusForm
from .models import Admin, Lead, utcnow

admin = Blueprint("admin", __name__, url_prefix="/admin")
DUMMY_HASH = generate_password_hash("not-a-login-credential")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = db.session.get(Admin, session.get("admin_id")) if session.get("admin_id") else None
        if user is None or (current_app.config["PRODUCTION"] and user.username == "dev-admin"):
            return redirect(url_for("admin.login"))
        g.admin = user
        return view(*args, **kwargs)
    return wrapped


@admin.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
@limiter.limit("20 per hour", methods=["POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(Admin).where(Admin.username == form.username.data))
        valid = check_password_hash(user.password_hash if user else DUMMY_HASH, form.password.data)
        development_account = user and user.username == "dev-admin" and current_app.config["PRODUCTION"]
        if user and valid and not development_account:
            lang = session.get("language")
            session.clear()
            if lang:
                session["language"] = lang
            session["admin_id"] = user.id
            session.permanent = True
            return redirect(url_for("admin.dashboard"), code=303)
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html", form=form, page_title="Admin login")


@admin.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("admin.login"), code=303)


@admin.get("")
@login_required
def dashboard():
    counts = dict(db.session.execute(db.select(Lead.status, db.func.count(Lead.id)).group_by(Lead.status)).all())
    return render_template("admin/dashboard.html", counts=counts, total=sum(counts.values()), page_title="Lead dashboard")


@admin.get("/leads")
@login_required
def leads():
    page_number = max(1, request.args.get("page", 1, type=int))
    rows = db.paginate(db.select(Lead).order_by(Lead.created_at.desc(), Lead.id.desc()), page=page_number, per_page=25, error_out=False)
    return render_template("admin/leads.html", rows=rows, page_title="Leads")


def find_lead(public_id):
    return db.first_or_404(db.select(Lead).where(Lead.public_id == public_id))


@admin.get("/leads/<public_id>")
@login_required
def detail(public_id):
    lead = find_lead(public_id)
    return render_template("admin/detail.html", lead=lead, status_form=StatusForm(status=lead.status), notes_form=NotesForm(notes=lead.notes), page_title="Lead detail")


@admin.post("/leads/<public_id>/status")
@login_required
def status(public_id):
    form = StatusForm()
    if not form.validate_on_submit():
        abort(400)
    lead = find_lead(public_id)
    lead.status = form.status.data
    if lead.status == "contacted" and not lead.contacted_at:
        lead.contacted_at = utcnow()
    db.session.commit()
    flash("Status updated.", "success")
    return redirect(url_for("admin.detail", public_id=public_id), code=303)


@admin.post("/leads/<public_id>/notes")
@login_required
def notes(public_id):
    form = NotesForm()
    if not form.validate_on_submit():
        abort(400)
    lead = find_lead(public_id)
    lead.notes = form.notes.data
    db.session.commit()
    flash("Notes updated.", "success")
    return redirect(url_for("admin.detail", public_id=public_id), code=303)
