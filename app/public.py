from datetime import datetime, timezone
from urllib.parse import urlencode

from flask import Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from . import mail
from .content import META, tr
from .extensions import db, limiter
from .forms import LeadForm
from .models import Lead, PortfolioProject

public = Blueprint("public", __name__)
PAGES = ("home", "services", "industries", "portfolio", "pricing", "process", "about", "book-call", "contact", "privacy", "terms")


def page(template, name, **kwargs):
    return render_template(template, page_name=name, meta_description=tr(META[name]), **kwargs)


@public.post("/language")
def set_language():
    language = request.form.get("language")
    if language not in ("el", "en"):
        abort(400)
    target = request.form.get("next", "/")
    # Exact local path allowlist; never trust Host, referrer, or arbitrary next URLs.
    permitted = {"/" if p == "home" else "/" + p for p in PAGES}
    if target not in permitted:
        target = "/"
    session["language"] = language
    return redirect(target + "?" + urlencode({"lang": language}), code=303)


@public.get("/")
def home():
    return page("home.html", "home")


@public.get("/services")
def services():
    return page("services.html", "services")


@public.get("/industries")
def industries():
    return page("industries.html", "industries")


@public.get("/portfolio")
def portfolio():
    projects = db.session.scalars(db.select(PortfolioProject).where(PortfolioProject.published.is_(True)).order_by(PortfolioProject.sort_order, PortfolioProject.id)).all()
    return page("portfolio.html", "portfolio", projects=projects)


@public.get("/pricing")
def pricing():
    return page("pricing.html", "pricing")


@public.get("/process")
def process():
    return page("process.html", "process")


@public.get("/about")
def about():
    return page("about.html", "about")


@public.route("/contact", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
@limiter.limit("2 per minute", methods=["POST"])
def contact():
    form = LeadForm()
    if form.validate_on_submit():
        lead = Lead(name=form.name.data, email=form.email.data, phone=form.phone.data,
                    company=form.company.data, industry=form.industry.data,
                    requirements_json=list(dict.fromkeys(form.requirements.data)), budget_range=form.budget.data,
                    description=form.description.data, timeframe=form.timeframe.data, language=g.lang)
        db.session.add(lead)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.error("Lead persistence failed; submission not saved.")
            abort(503)
        # Only an opaque identifier goes into the signed (not encrypted) browser session.
        session["booking_lead"] = lead.public_id
        session["booking_until"] = int(datetime.now(timezone.utc).timestamp()) + 1800
        try:
            lead.email_status = mail.notify_lead(lead)
        except Exception:
            lead.email_status = "failed"
            current_app.logger.warning("Lead email notification failed; saved lead retained.")
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.warning("Notification state could not be updated; saved lead retained.")
        flash(tr("lead_success"), "success")
        return redirect(url_for("public.book_call"), code=303)
    return page("contact.html", "contact", form=form), (422 if request.method == "POST" else 200)


@public.get("/book-call")
def book_call():
    prefill = {}
    if session.get("booking_until", 0) > datetime.now(timezone.utc).timestamp():
        lead = db.session.scalar(db.select(Lead).where(Lead.public_id == session.get("booking_lead")))
        if lead:
            prefill = {"name": lead.name, "email": lead.email}
    else:
        session.pop("booking_lead", None)
        session.pop("booking_until", None)
    return page("book_call.html", "book-call", calendly_url=current_app.config["CALENDLY_SCHEDULING_URL"], prefill=prefill)


@public.get("/privacy")
def privacy():
    from .legal import LEGAL
    return page("legal.html", "privacy", sections=LEGAL["privacy"])


@public.get("/terms")
def terms():
    from .legal import LEGAL
    return page("legal.html", "terms", sections=LEGAL["terms"])


@public.get("/sitemap.xml")
def sitemap():
    return Response(render_template("sitemap.xml", pages=PAGES), mimetype="application/xml")


@public.get("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /admin\nDisallow: /book-call\nSitemap: " + current_app.config["BASE_URL"] + "/sitemap.xml\n", mimetype="text/plain")
