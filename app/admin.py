from functools import wraps
from datetime import timedelta
from decimal import Decimal

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .extensions import db, limiter
from .forms import LoginForm, NotesForm, StatusForm
from .models import Admin, Lead, ProjectCase, PROJECT_STATUSES, PROJECT_PRIORITIES, PROJECT_MILESTONES, utcnow
from .project_forms import ConvertProjectForm, ProjectForm, ProjectStatusForm
from .crm import crm_label

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
    projects = dict(db.session.execute(db.select(ProjectCase.status, db.func.count(ProjectCase.id)).group_by(ProjectCase.status)).all())
    today = utcnow().date()
    upcoming = today + timedelta(days=7)
    attention = db.session.scalars(db.select(ProjectCase).where(
        ProjectCase.status.notin_(("delivered", "maintenance", "cancelled")),
        db.or_(ProjectCase.status.in_(("waiting_for_client", "on_hold")), ProjectCase.target_delivery_date <= upcoming)
    ).order_by(ProjectCase.target_delivery_date.asc().nullslast(), ProjectCase.updated_at.desc()).limit(10)).all()
    return render_template("admin/dashboard.html", counts=counts, total=sum(counts.values()),
                           project_counts=projects, active_projects=sum(v for k, v in projects.items() if k not in ("delivered", "maintenance", "cancelled")),
                           attention=attention, today=today, page_title="Dashboard")


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
    return render_template("admin/detail.html", lead=lead, status_form=StatusForm(status=lead.status), notes_form=NotesForm(notes=lead.notes),
                           conversion_form=ConvertProjectForm(), project=lead.project_case, page_title="Lead detail")


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


@admin.context_processor
def project_labels():
    return {"crm": crm_label, "project_statuses": PROJECT_STATUSES, "project_priorities": PROJECT_PRIORITIES,
            "project_milestones": PROJECT_MILESTONES}


def commit_project():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.error("Project save failed")
        abort(503)


def find_project(public_id, lock=False):
    query = db.select(ProjectCase).where(ProjectCase.public_id == public_id)
    return db.first_or_404(query.with_for_update() if lock else query)


def apply_project_form(project, form):
    # Explicit allowlist: no submitted IDs, currency, source or timestamps.
    for name in ("title", "client_name", "client_email", "client_phone", "company", "industry", "project_summary",
                 "internal_notes", "package_name", "priority", "target_start_date", "target_delivery_date"):
        setattr(project, name, getattr(form, name).data or None)
    project.quoted_price_cents = form.price_cents
    project.status = form.status.data


@admin.post("/leads/<public_id>/convert")
@login_required
def convert_project(public_id):
    form = ConvertProjectForm()
    if not form.validate_on_submit():
        abort(400)
    # Serializes conversion on PostgreSQL; the unique FK is the final race guard.
    lead = db.first_or_404(db.select(Lead).where(Lead.public_id == public_id).with_for_update())
    project = db.session.scalar(db.select(ProjectCase).where(ProjectCase.lead_id == lead.id))
    if project is None:
        project = ProjectCase(lead_id=lead.id, title=f"{lead.company or lead.name} – Project",
                              client_name=lead.name, client_email=lead.email, client_phone=lead.phone,
                              company=lead.company, industry=lead.industry, project_summary=lead.description,
                              status="proposal", priority="normal")
        db.session.add(project)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            project = db.session.scalar(db.select(ProjectCase).join(Lead).where(Lead.public_id == public_id))
            if project is None:
                current_app.logger.error("Project conversion failed")
                abort(503)
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.error("Project conversion failed")
            abort(503)
    return redirect(url_for("admin.project_detail", public_id=project.public_id), code=303)


@admin.get("/projects")
@login_required
def projects():
    filters = {name: request.args.get(name, "").strip() for name in ("status", "industry", "priority", "q")}
    if ((filters["status"] and filters["status"] not in PROJECT_STATUSES) or
            (filters["priority"] and filters["priority"] not in PROJECT_PRIORITIES) or
            len(filters["industry"]) > 120 or len(filters["q"]) > 200):
        abort(400)
    query = db.select(ProjectCase)
    for name in ("status", "industry", "priority"):
        if filters[name]:
            query = query.where(getattr(ProjectCase, name) == filters[name])
    if filters["q"]:
        # Literal substring search; SQLAlchemy escapes LIKE wildcards and binds values.
        query = query.where(db.or_(*(getattr(ProjectCase, field).icontains(filters["q"], autoescape=True)
                                   for field in ("title", "client_name", "company", "client_email"))))
    rows = db.paginate(query.order_by(ProjectCase.updated_at.desc(), ProjectCase.id.desc()),
                       page=max(1, request.args.get("page", 1, type=int)), per_page=25, error_out=False)
    industries = db.session.scalars(db.select(ProjectCase.industry).where(ProjectCase.industry.is_not(None)).distinct().order_by(ProjectCase.industry)).all()
    return render_template("admin/projects.html", rows=rows, filters=filters, industries=industries, page_title=crm_label("Projects"))


@admin.route("/projects/new", methods=["GET", "POST"])
@login_required
def project_new():
    form = ProjectForm(status="proposal", priority="normal")
    if form.validate_on_submit():
        project = ProjectCase()
        apply_project_form(project, form)
        db.session.add(project)
        commit_project()
        return redirect(url_for("admin.project_detail", public_id=project.public_id), code=303)
    return render_template("admin/project_form.html", form=form, project=None, page_title=crm_label("New project")), (422 if request.method == "POST" else 200)


@admin.get("/projects/<public_id>")
@login_required
def project_detail(public_id):
    project = find_project(public_id)
    price = format(Decimal(project.quoted_price_cents) / 100, ".2f") if project.quoted_price_cents is not None else ""
    return render_template("admin/project_detail.html", project=project,
                           form=ProjectForm(obj=project, quoted_price=price),
                           status_form=ProjectStatusForm(status=project.status), page_title=crm_label("Project detail"))


@admin.post("/projects/<public_id>/edit")
@login_required
def project_edit(public_id):
    project = find_project(public_id, lock=True)
    form = ProjectForm()
    if not form.validate_on_submit():
        return render_template("admin/project_form.html", form=form, project=project, page_title=crm_label("Edit project")), 422
    apply_project_form(project, form)
    commit_project()
    flash(crm_label("Project saved."), "success")
    return redirect(url_for("admin.project_detail", public_id=public_id), code=303)


@admin.post("/projects/<public_id>/status")
@login_required
def project_status(public_id):
    form = ProjectStatusForm()
    if not form.validate_on_submit():
        abort(400)
    project = find_project(public_id, lock=True)
    project.status = form.status.data
    commit_project()
    flash(crm_label("Status updated."), "success")
    return redirect(url_for("admin.project_detail", public_id=public_id), code=303)
