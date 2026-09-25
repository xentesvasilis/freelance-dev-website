"""Local browser QA. All profiles, databases, screenshots and reports stay in ROOT."""
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)
BROWSER_TMP = ROOT / ".cache" / "browser"
BROWSER_TMP.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(BROWSER_TMP)
os.environ["TMP"] = str(BROWSER_TMP)
tempfile.tempdir = str(BROWSER_TMP)

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from app import create_app
from app.extensions import db
from app.models import Admin, Lead


def main():
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    executable = next((path for path in [
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    ] if path.is_file()), None)
    if not executable:
        raise SystemExit("Install Chrome or Edge, or edit the browser path in this local-only harness.")
    report = {"checks": [], "browser_errors": [], "screenshots": []}
    with tempfile.TemporaryDirectory(prefix="qa-", dir=BROWSER_TMP) as directory:
        app = create_app({"TESTING": True, "PRODUCTION": False, "SECRET_KEY": "browser-check-only",
                          "BASE_URL": "http://127.0.0.1:5099", "TRUSTED_HOSTS": None,
                          "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (Path(directory) / "qa.db").as_posix(),
                          "MAIL_ENABLED": False, "CALENDLY_SCHEDULING_URL": "",
                          "SESSION_COOKIE_SECURE": False, "RATELIMIT_ENABLED": False})
        with app.app_context():
            db.create_all()
            admin = Admin(username="browser-admin")
            admin.set_password("browser-test-password-only")
            db.session.add(admin)
            db.session.commit()
        server = make_server("127.0.0.1", 5099, app)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=str(executable), headless=True)
                context = browser.new_context()
                # Block external network. This is local UI verification, not a live provider test.
                context.route("**/*", lambda route: route.continue_() if route.request.url.startswith("http://127.0.0.1:5099") else route.abort())
                page = context.new_page()
                page.on("pageerror", lambda error: report["browser_errors"].append(str(error)))
                base = "http://127.0.0.1:5099"
                page.goto(base)
                assert page.locator(".language-gate").is_visible()
                page.locator('.language-gate button[value="en"]').click()
                assert page.locator(".language-gate").count() == 0
                report["checks"].append("First-visit language selection and session persistence")
                paths = ["/", "/services", "/industries", "/portfolio", "/pricing", "/process", "/about", "/contact", "/book-call", "/privacy", "/terms"]
                for language in ("en", "el"):
                    for width in (1440, 768, 390, 320):
                        page.set_viewport_size({"width": width, "height": 1000 if width > 700 else 844})
                        for path in paths:
                            response = page.goto(base + path + "?lang=" + language)
                            assert response.status == 200, (path, language, width)
                            assert page.locator("h1").count() == 1
                            overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                            if overflow:
                                offenders = page.evaluate("Array.from(document.querySelectorAll('body *')).filter(e => e.getBoundingClientRect().right > innerWidth + 1).map(e => e.tagName + '.' + e.className).slice(0, 12)")
                                raise AssertionError(f"Horizontal overflow: {path} {language} {width}: {offenders}")
                            if path in ("/", "/pricing", "/contact") and width in (1440, 390):
                                name = f"{path.strip('/') or 'home'}-{language}-{width}.png"
                                page.screenshot(path=str(ARTIFACTS / name), full_page=True)
                                report["screenshots"].append(name)
                        report["checks"].append(f"11 pages, {language}, {width}px: render and overflow checks")
                page.set_viewport_size({"width": 390, "height": 844})
                page.goto(base + "/?lang=en")
                page.get_by_role("button", name="Menu").click()
                assert page.locator("#primary-nav").is_visible()
                page.locator('#primary-nav a[href="/services"]').focus()
                page.keyboard.press("Escape")
                assert not page.locator("#primary-nav").is_visible()
                assert page.locator(".menu-toggle").evaluate("e => e === document.activeElement")
                report["checks"].append("Mobile navigation and Escape keyboard focus")
                page.goto(base + "/contact?lang=en")
                page.get_by_role("button", name="Send project brief").click()
                assert page.get_by_role("alert").is_visible()
                page.locator("#name").fill("Browser Test Person")
                page.locator("#email").fill("browser@example.com")
                page.locator("#industry").select_option("consulting")
                page.locator("#budget").select_option("1000-2000")
                page.get_by_label("New website", exact=True).check()
                page.locator("#description").fill("A professional consulting website with an enquiry workflow.")
                page.locator("#timeframe").select_option("flexible")
                page.locator("#privacy_accept").check()
                page.get_by_role("button", name="Send project brief").click()
                assert page.url.endswith("/book-call")
                assert "your brief has been saved" in page.locator(".notice").inner_text()
                report["checks"].append("Real-browser CSRF-protected lead submission and booking redirect")
                page.goto(base + "/admin/login")
                page.locator("#username").fill("browser-admin")
                page.locator("#password").fill("browser-test-password-only")
                page.get_by_role("button", name="Log in", exact=True).click()
                page.get_by_role("link", name="Review leads").click()
                page.get_by_role("link", name="Browser Test Person").click()
                page.locator("#status").select_option("qualified")
                page.get_by_role("button", name="Update status").click()
                page.locator("#notes").fill("Local browser QA only.")
                page.get_by_role("button", name="Save notes").click()
                with app.app_context():
                    lead = db.session.scalar(db.select(Lead))
                    assert lead.status == "qualified" and lead.notes == "Local browser QA only."
                    assert lead.email_status == "disabled"
                page.get_by_role("button", name="Log out").click()
                assert page.url.endswith("/admin/login")
                report["checks"].append("Admin login, lead view, status, notes and POST logout")
                assert not report["browser_errors"], report["browser_errors"]
                browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
    report["result"] = "PASS"
    (ARTIFACTS / "browser-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
