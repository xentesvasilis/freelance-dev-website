from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db
from app.models import Admin, Lead, PortfolioProject, ProjectCase


def test_upgrade_existing_schema_preserves_all_existing_records(tmp_path):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (tmp_path / "existing.db").as_posix(),
                      "RATELIMIT_ENABLED": False})
    runner = app.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade", "784018745121"]).exit_code == 0
    with app.app_context():
        admin = Admin(username="preserved@example.com")
        admin.set_password("synthetic-migration-password")
        lead = Lead(name="Original Ελληνικά", email="lead@example.com", industry="healthcare", requirements_json=["website"],
                    budget_range="1000-2000", description="Original lead submission", timeframe="month", language="el", notes="Private original note")
        portfolio = PortfolioProject(slug="preserved", title={"en": "Published", "el": "Έργο"},
                                     short_description={"en": "Test"}, description={"en": "Test"}, industry="healthcare",
                                     technologies=["Flask"], features=["Test"], published=True)
        db.session.add_all([admin, lead, portfolio])
        db.session.commit()
        before = {model.__tablename__: [dict(row._mapping) for row in db.session.execute(db.select(model.__table__))]
                  for model in (Admin, Lead, PortfolioProject)}
        assert "project_case" not in inspect(db.engine).get_table_names()
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        for model in (Admin, Lead, PortfolioProject):
            assert before[model.__tablename__] == [dict(row._mapping) for row in db.session.execute(db.select(model.__table__))]
        assert db.session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "c8a4e291d630"
        assert db.session.scalar(db.select(db.func.count(ProjectCase.id))) == 0
        inspector = inspect(db.engine)
        assert {"ix_project_case_status", "ix_project_case_priority", "ix_project_case_industry", "ix_project_case_updated_at", "ix_project_case_target_delivery_date"} == {i["name"] for i in inspector.get_indexes("project_case")}
        assert {tuple(c["column_names"]) for c in inspector.get_unique_constraints("project_case")} == {("public_id",), ("lead_id",)}
        assert inspector.get_foreign_keys("project_case")[0]["referred_table"] == "lead"
    check = runner.invoke(args=["db", "check"])
    assert check.exit_code == 0, check.output
    # Re-running upgrade is harmless; explicit test-only downgrade preserves old tables.
    assert runner.invoke(args=["db", "upgrade"]).exit_code == 0
    assert runner.invoke(args=["db", "downgrade", "784018745121"]).exit_code == 0
    with app.app_context():
        assert "project_case" not in inspect(db.engine).get_table_names()
        assert db.session.scalar(db.select(Lead.description)) == "Original lead submission"
        assert db.session.scalar(db.select(PortfolioProject.published)) is True
        db.session.remove()
        db.engine.dispose()


def test_postgresql_incremental_migration_sql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://synthetic:synthetic@localhost/offline")
    app = create_app({"TESTING": True, "RATELIMIT_ENABLED": False})
    result = app.test_cli_runner().invoke(args=["db", "upgrade", "784018745121:c8a4e291d630", "--sql"])
    assert result.exit_code == 0, result.output
    sql = result.output
    assert "CREATE TABLE project_case" in sql
    assert "TIMESTAMP WITH TIME ZONE" in sql
    assert "UNIQUE (lead_id)" in sql and "FOREIGN KEY(lead_id) REFERENCES lead (id) ON DELETE SET NULL" in sql
    assert "DROP TABLE" not in sql and "ALTER TABLE lead" not in sql
    assert "CREATE TABLE lead" not in sql and "DELETE FROM lead" not in sql
    with app.app_context():
        db.engine.dispose()
