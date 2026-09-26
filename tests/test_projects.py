from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor

import pytest
from bs4 import BeautifulSoup
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db
from app.models import Admin, Lead, PortfolioProject, ProjectCase, PROJECT_MILESTONES, utcnow


@pytest.fixture
def project_data():
    return dict(title="Client portal", client_name="Maria Example", client_email="maria@example.com",
                client_phone="+30 2100000000", company="Example Practice", industry="healthcare",
                project_summary="A private client project with Greek Ελληνικά and English.",
                internal_notes="PRIVATE_INTERNAL_MARKER", package_name="Custom scope",
                quoted_price="1700.50", status="proposal", priority="normal",
                target_start_date="2027-01-01", target_delivery_date="2027-02-01")


@pytest.fixture
def project_url(app, admin_client, project_data):
    response = admin_client.post("/admin/projects/new", data=project_data)
    assert response.status_code == 303
    return response.headers["Location"]


@pytest.fixture
def lead_id(app, admin_client, lead_data):
    assert admin_client.post("/contact", data=lead_data).status_code == 303
    with app.app_context():
        return db.session.scalar(db.select(Lead.public_id))


def test_model_defaults_ids_and_prices(app):
    with app.app_context():
        first = ProjectCase(title="A", client_name="A", client_email="a@example.com", project_summary="A", quoted_price_cents=98000)
        second = ProjectCase(title="B", client_name="B", client_email="b@example.com", project_summary="B")
        db.session.add_all([first, second])
        db.session.commit()
        assert first.public_id != second.public_id
        assert len(first.public_id) >= 43 and not first.public_id.isdigit()
        assert first.status == "proposal" and first.priority == "normal" and first.currency == "EUR"
        assert first.lead_id is None and second.lead_id is None
        assert first.created_at and first.updated_at
        assert first.quoted_price_display == "€980"
        first.quoted_price_cents = 170000
        assert first.quoted_price_display == "€1,700"
        first.quoted_price_cents = 300000
        assert first.quoted_price_display == "€3,000"
        assert second.quoted_price_display == "—"


@pytest.mark.parametrize("path,method", [
    ("/admin/projects", "get"), ("/admin/projects/new", "get"), ("/admin/projects/new", "post"),
    ("/admin/projects/unknown", "get"), ("/admin/projects/unknown/edit", "post"),
    ("/admin/projects/unknown/status", "post"), ("/admin/leads/unknown/convert", "post"),
])
def test_every_project_route_requires_auth(client, path, method):
    response = getattr(client, method)(path)
    assert response.status_code == 302 and response.headers["Location"].endswith("/admin/login")


def test_manual_project_create_list_detail(app, admin_client, project_url):
    for path in ("/admin/projects", project_url):
        response = admin_client.get(path)
        assert response.status_code == 200
        assert b"Client portal" in response.data
        assert "€1,700.50" in response.text
        assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
        assert response.headers["Cache-Control"] == "no-store"
    with app.app_context():
        project = db.session.scalar(db.select(ProjectCase))
        assert project.quoted_price_cents == 170050 and isinstance(project.quoted_price_cents, int)
        assert project.lead_id is None
        assert project.package_name == "Custom scope"
        assert project_url.endswith(project.public_id)
        assert db.session.scalar(db.select(db.func.count(PortfolioProject.id))) == 0
    assert admin_client.get("/admin/projects/1").status_code == 404
    assert b"PRIVATE_INTERNAL_MARKER" not in admin_client.get("/admin/projects").data


@pytest.mark.parametrize("field,value", [
    ("title", " "), ("title", "x" * 201), ("client_email", "not-an-email"),
    ("client_phone", "x" * 41), ("status", "published"), ("priority", "invalid"),
    ("project_summary", ""), ("project_summary", "x\x00y"), ("internal_notes", "x" * 10001),
    ("quoted_price", "-1"), ("quoted_price", "1.001"), ("quoted_price", "NaN"),
    ("quoted_price", "Infinity"), ("quoted_price", "1e3"), ("quoted_price", "1,700"),
    ("quoted_price", "21474836.48"), ("target_delivery_date", "2026-01-01"),
    ("target_start_date", "not-a-date"),
])
def test_invalid_form_is_rejected(app, admin_client, project_data, field, value):
    response = admin_client.post("/admin/projects/new", data={**project_data, field: value})
    assert response.status_code == 422
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ProjectCase.id))) == 0


@pytest.mark.parametrize("value,cents", [("0", 0), ("0.29", 29), ("", None), ("21474836.47", 2147483647)])
def test_money_exact_boundaries(app, admin_client, project_data, value, cents):
    assert admin_client.post("/admin/projects/new", data={**project_data, "quoted_price": value}).status_code == 303
    with app.app_context():
        assert db.session.scalar(db.select(ProjectCase.quoted_price_cents)) == cents


def test_conversion_confirmed_idempotent_preserves_lead(app, admin_client, lead_id):
    with app.app_context():
        lead = db.session.scalar(db.select(Lead))
        before = {column.name: getattr(lead, column.name) for column in Lead.__table__.columns}
    path = f"/admin/leads/{lead_id}"
    detail = admin_client.get(path)
    assert b"Convert to Project" in detail.data and b'name="confirm"' in detail.data
    assert admin_client.post(path + "/convert").status_code == 400
    first = admin_client.post(path + "/convert", data={"confirm": "y"})
    second = admin_client.post(path + "/convert", data={"confirm": "y"})
    assert first.status_code == second.status_code == 303
    assert first.headers["Location"] == second.headers["Location"]
    assert path in admin_client.get(first.headers["Location"]).text
    detail = admin_client.get(path)
    assert b"Open project" in detail.data and b"Convert to Project" not in detail.data
    with app.app_context():
        lead = db.session.scalar(db.select(Lead))
        assert before == {column.name: getattr(lead, column.name) for column in Lead.__table__.columns}
        assert db.session.scalar(db.select(db.func.count(ProjectCase.id))) == 1
        project = db.session.scalar(db.select(ProjectCase))
        assert project.lead_id == lead.id and project.status == "proposal"
        assert project.title == f"{lead.company} – Project"
        assert (project.client_name, project.client_email, project.client_phone, project.company, project.industry, project.project_summary) == (lead.name, lead.email, lead.phone, lead.company, lead.industry, lead.description)
        assert project.internal_notes is None
        assert db.session.scalar(db.select(db.func.count(PortfolioProject.id))) == 0


def test_concurrent_conversion_unique(app, lead_id):
    with app.app_context():
        admin_id = db.session.scalar(db.select(Admin.id))
    def convert(_):
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["admin_id"] = admin_id
            response = client.post(f"/admin/leads/{lead_id}/convert", data={"confirm": "y"})
            return response.status_code, response.headers.get("Location")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(convert, range(2)))
    assert results[0] == results[1] and results[0][0] == 303
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ProjectCase.id))) == 1


@pytest.mark.parametrize("status,field", list(PROJECT_MILESTONES.items()))
def test_status_milestone_preserved(app, admin_client, project_url, status, field):
    with app.app_context():
        original_created = db.session.scalar(db.select(ProjectCase.created_at))
        original_updated = db.session.scalar(db.select(ProjectCase.updated_at))
    assert admin_client.post(project_url + "/status", data={"status": status}).status_code == 303
    with app.app_context():
        project = db.session.scalar(db.select(ProjectCase))
        first = getattr(project, field)
        assert first is not None and project.status == status
        assert project.updated_at >= original_updated
        assert project.created_at == original_created
    assert admin_client.post(project_url + "/status", data={"status": "on_hold"}).status_code == 303
    assert admin_client.post(project_url + "/status", data={"status": status}).status_code == 303
    with app.app_context():
        assert getattr(db.session.scalar(db.select(ProjectCase)), field) == first


def test_edit_and_explicit_reopen(app, admin_client, project_url, project_data):
    changed = {**project_data, "status": "accepted", "priority": "urgent", "quoted_price": "0.29",
               "package_name": "My bespoke package", "project_summary": "Changed scope", "internal_notes": "Changed notes",
               "target_start_date": "", "target_delivery_date": "", "lead_id": "123", "currency": "USD", "accepted_at": "1900-01-01"}
    assert admin_client.post(project_url + "/edit", data=changed).status_code == 303
    with app.app_context():
        project = db.session.scalar(db.select(ProjectCase))
        assert project.accepted_at.year != 1900 and project.currency == "EUR" and project.lead_id is None
        assert project.quoted_price_cents == 29 and project.priority == "urgent"
        assert project.package_name == changed["package_name"] and project.internal_notes == "Changed notes"
        assert project.target_start_date is None and project.target_delivery_date is None
    assert admin_client.post(project_url + "/edit", data={**changed, "quoted_price": "-1"}).status_code == 422
    assert admin_client.post(project_url + "/status", data={"status": "invalid"}).status_code == 400
    for status in ("cancelled", "proposal_sent", "waiting_for_client"):
        assert admin_client.post(project_url + "/status", data={"status": status}).status_code == 303


def test_creation_in_advanced_status(app, admin_client, project_data):
    assert admin_client.post("/admin/projects/new", data={**project_data, "status": "delivered"}).status_code == 303
    with app.app_context():
        project = db.session.scalar(db.select(ProjectCase))
        assert project.delivered_at and not project.accepted_at


def test_csrf_all_mutations(app, admin_client, project_url, project_data, lead_id):
    app.config["WTF_CSRF_ENABLED"] = True
    for path, data in [("/admin/projects/new", project_data), (project_url + "/edit", project_data),
                       (project_url + "/status", {"status": "accepted"}),
                       (f"/admin/leads/{lead_id}/convert", {"confirm": "y"})]:
        assert admin_client.post(path, data=data).status_code == 400
        assert admin_client.post(path, data={**data, "csrf_token": "invalid"}).status_code == 400
        page = admin_client.get(project_url)
        token = BeautifulSoup(page.data, "html.parser").find("input", attrs={"name": "csrf_token"})["value"]
        assert admin_client.post(path, data={**data, "csrf_token": token}).status_code == 303


def test_mutation_gets_not_allowed(admin_client, project_url, lead_id):
    for path in (project_url + "/edit", project_url + "/status", f"/admin/leads/{lead_id}/convert"):
        assert admin_client.get(path).status_code == 405


def test_search_filters_and_default_sort(admin_client, project_data):
    first = admin_client.post("/admin/projects/new", data=project_data).headers["Location"]
    other = {**project_data, "title": "Zebra project", "client_name": "Nikos Unique", "company": "Other Co",
             "client_email": "unique@example.com", "industry": "legal", "status": "testing", "priority": "high"}
    second = admin_client.post("/admin/projects/new", data=other).headers["Location"]
    page = admin_client.get("/admin/projects").text
    assert page.index(second) < page.index(first)
    for query in ("q=nikos", "q=zebra", "q=Other+Co", "q=unique%40example.com", "status=testing", "industry=legal", "priority=high", "status=testing&industry=legal&priority=high"):
        page = admin_client.get("/admin/projects?" + query).text
        assert second in page and first not in page
    assert second not in admin_client.get("/admin/projects?q=%25").text
    assert admin_client.get("/admin/projects?status=invalid").status_code == 400


def test_dashboard_counts_and_attention(app, admin_client, project_data):
    today = utcnow().date()
    for status in ("proposal", "proposal_sent", "accepted", "in_development", "testing", "delivered", "maintenance", "cancelled", "on_hold", "waiting_for_client"):
        admin_client.post("/admin/projects/new", data={**project_data, "title": "Metric " + status, "status": status,
                          "target_start_date": "", "target_delivery_date": str(today - timedelta(days=1))})
    response = admin_client.get("/admin")
    soup = BeautifulSoup(response.data, "html.parser")
    assert soup.select_one('[data-metric="active"]').text == "7"
    assert soup.select_one('[data-metric="proposals"]').text == "2"
    for status in ("in_development", "testing", "delivered", "maintenance"):
        assert soup.select_one(f'[data-metric="{status}"]').text == "1"
    attention = soup.select_one(".project-attention").text
    assert "Metric on_hold" in attention and "Metric waiting_for_client" in attention and "Overdue" in attention
    assert "Metric cancelled" not in attention and "Metric delivered" not in attention and "Metric maintenance" not in attention
    assert "Total leads" in response.text


def test_privacy_escaping_public_flows(app, admin_client, project_data, caplog):
    payload = {**project_data, "title": "PRIVATE_PROJECT_MARKER", "internal_notes": '<script>alert("PRIVATE_NOTE")</script>'}
    location = admin_client.post("/admin/projects/new", data=payload).headers["Location"]
    detail = admin_client.get(location).text
    assert "&lt;script&gt;" in detail and payload["internal_notes"] not in detail
    assert "PRIVATE_NOTE" not in caplog.text
    app.config["CALENDLY_SCHEDULING_URL"] = "https://calendly.com/synthetic/staging"
    for path in ("/", "/?lang=el", "/?lang=en", "/portfolio", "/pricing", "/book-call", "/sitemap.xml", "/robots.txt"):
        response = admin_client.get(path)
        assert response.status_code == 200
        assert "PRIVATE_PROJECT_MARKER" not in response.text and "PRIVATE_NOTE" not in response.text
        assert "/admin/projects" not in response.text
    assert "Μετατροπή σε Project" in admin_client.get("/admin/projects/new?lang=el").text or "Νέο project" in admin_client.get("/admin/projects/new?lang=el").text


def test_database_constraints_and_one_lead(app, admin_client, lead_id):
    admin_client.post(f"/admin/leads/{lead_id}/convert", data={"confirm": "y"})
    with app.app_context():
        project = db.session.scalar(db.select(ProjectCase))
        for column, value in (("priority", "invalid"), ("quoted_price_cents", -1), ("currency", "USD"), ("status", "invalid")):
            with pytest.raises(IntegrityError):
                db.session.execute(db.update(ProjectCase).values({column: value}))
                db.session.commit()
            db.session.rollback()
        duplicate = ProjectCase(lead_id=project.lead_id, title="Duplicate", client_name="A", client_email="a@example.com", project_summary="A")
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_failed_save_redacts_private_details(app, admin_client, project_data, monkeypatch, caplog):
    def fail_commit():
        raise SQLAlchemyError("PRIVATE_INTERNAL_MARKER with credentials and query values")
    monkeypatch.setattr(db.session, "commit", fail_commit)
    response = admin_client.post("/admin/projects/new", data=project_data)
    assert response.status_code == 503
    assert "Project save failed" in caplog.text
    assert "PRIVATE_INTERNAL_MARKER" not in caplog.text and "credentials" not in caplog.text
    assert "PRIVATE_INTERNAL_MARKER" not in response.text
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(ProjectCase.id))) == 0


def test_attention_upcoming_and_pagination(app, admin_client, project_data):
    today = utcnow().date()
    with app.app_context():
        for number in range(27):
            db.session.add(ProjectCase(title=f"Page project {number}", client_name="Client", client_email="a@example.com",
                                       project_summary="Synthetic scope", industry="legal", priority="high"))
        db.session.add(ProjectCase(title="Due soon", client_name="Client", client_email="a@example.com", project_summary="Scope",
                                   target_delivery_date=today + timedelta(days=7)))
        db.session.add(ProjectCase(title="Not due soon", client_name="Client", client_email="a@example.com", project_summary="Scope",
                                   target_delivery_date=today + timedelta(days=8)))
        db.session.commit()
    page = BeautifulSoup(admin_client.get("/admin/projects?industry=legal&priority=high").data, "html.parser")
    assert len(page.select("tbody tr")) == 25
    next_link = page.select_one('nav[aria-label="Pagination"] a')["href"]
    assert "industry=legal" in next_link and "priority=high" in next_link
    assert len(BeautifulSoup(admin_client.get(next_link).data, "html.parser").select("tbody tr")) == 2
    attention = BeautifulSoup(admin_client.get("/admin").data, "html.parser").select_one(".project-attention").text
    assert "Due soon" in attention and "Not due soon" not in attention and "Due within 7 days" in attention
