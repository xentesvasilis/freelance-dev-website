import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from jinja2 import nodes

from app.content import CONTENT, META, PACKAGES, TEXT


def test_app_creation(app):
    assert app.name == "app"
    assert not app.debug


@pytest.mark.parametrize("path", ["/", "/services", "/industries", "/portfolio", "/pricing", "/process", "/about", "/contact", "/book-call", "/privacy", "/terms"])
@pytest.mark.parametrize("language", ["en", "el"])
def test_public_pages(client, path, language):
    response = client.get(path + "?lang=" + language)
    assert response.status_code == 200
    soup = BeautifulSoup(response.data, "html.parser")
    assert soup.html["lang"] == language
    assert len(soup.find_all("h1")) == 1
    assert soup.find("meta", attrs={"name": "viewport"})
    assert soup.find("link", rel="canonical")["href"].endswith(path + "?lang=" + language)
    assert soup.find("meta", property="og:title")
    assert soup.find("meta", attrs={"name": "description"})["content"]
    structured = json.loads(soup.find("script", type="application/ld+json").string)
    assert structured["name"] == "Vasilis Xentes"


def test_language_gate_and_selection(client):
    assert b'language-gate' in client.get("/").data
    response = client.post("/language", data={"language": "el", "next": "/services"})
    assert response.status_code == 303
    assert response.location == "/services?lang=el"
    with client.session_transaction() as session:
        assert session["language"] == "el"
    response = client.get("/")
    assert b'language-gate' not in response.data
    assert 'Ιστοσελίδες και web εφαρμογές'.encode() in response.data


def test_invalid_language_and_open_redirect(client):
    assert client.post("/language", data={"language": "xx"}).status_code == 400
    for target in ["https://evil.example/", "//evil.example", "/\\evil.example", "/admin", "/%0d%0a"]:
        response = client.post("/language", data={"language": "en", "next": target})
        assert response.location == "/?lang=en"
    assert b'lang="en"' in client.get("/?lang=xx").data


@pytest.mark.parametrize("lang", ["en", "el"])
@pytest.mark.parametrize("path", ["/pricing", "/"])
def test_exact_prices(client, lang, path):
    soup = BeautifulSoup(client.get(path + "?lang=" + lang).data, "html.parser")
    assert [n.get_text(strip=True) for n in soup.select(".package-price")] == ["€980", "€1,700", "€3,000"]
    assert [n.get_text(strip=True) for n in soup.select(".maintenance-price")] == ["€79" + ("/month" if lang == "en" else "/μήνα"), "€99" + ("/month" if lang == "en" else "/μήνα"), "€119" + ("/month" if lang == "en" else "/μήνα")]
    assert len(soup.select(".price-card")) == 3


def test_contact_links(client):
    for path in ("/", "/contact", "/about"):
        soup = BeautifulSoup(client.get(path).data, "html.parser")
        for link in soup.select('a[href="https://github.com/xentesvasilis/"]'):
            assert link["target"] == "_blank"
            assert {"noopener", "noreferrer"}.issubset(link["rel"])
        assert soup.select('a[href="https://github.com/xentesvasilis/"]')
        assert soup.select('a[href="mailto:xentesvasilis@gmail.com"]')
        assert soup.select('a[href="tel:+306989566911"]')
        assert not soup.select('a[href="/admin"]')


def test_sitemap_and_robots(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    root = ET.fromstring(response.data)
    urls = root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url")
    assert len(urls) == 20
    assert b"/admin" not in response.data
    for node in urls:
        url = node.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text
        assert client.get(url.replace("http://localhost", "")).status_code == 200
    robots = client.get("/robots.txt").text
    assert "Disallow: /admin" in robots
    assert "Sitemap: http://localhost/sitemap.xml" in robots


def test_all_template_url_for_endpoints_exist(app):
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
    for name in app.jinja_env.list_templates():
        source = app.jinja_env.loader.get_source(app.jinja_env, name)[0]
        tree = app.jinja_env.parse(source)
        for call in tree.find_all(nodes.Call):
            if isinstance(call.node, nodes.Name) and call.node.name == "url_for" and call.args and isinstance(call.args[0], nodes.Const):
                assert call.args[0].value in endpoints, (name, call.args[0].value)


def test_public_internal_links_and_assets(client):
    paths = ["/", "/services", "/industries", "/pricing", "/portfolio", "/process", "/about", "/contact", "/book-call", "/privacy", "/terms"]
    for path in paths:
        soup = BeautifulSoup(client.get(path + "?lang=en").data, "html.parser")
        ids = {node["id"] for node in soup.select("[id]")}
        assert len(ids) == len(soup.select("[id]")), path
        for anchor in soup.select("a[href]"):
            href = anchor["href"]
            if href.startswith("#"):
                assert href[1:] in ids
            elif href.startswith("/"):
                response = client.get(href.split("#")[0])
                assert response.status_code == 200, href
                if "#" in href:
                    target = BeautifulSoup(response.data, "html.parser")
                    assert target.find(id=href.split("#")[1]), href
        for asset in soup.select('script[src], link[rel="stylesheet"], link[rel="icon"]'):
            assert client.get(asset.get("src") or asset.get("href")).status_code == 200


def test_bilingual_catalog_complete():
    def check(value):
        if isinstance(value, dict):
            if "en" in value or "el" in value:
                assert set(value) == {"en", "el"}
                assert value["en"] and value["el"]
            else:
                for nested in value.values():
                    check(nested)
        elif isinstance(value, (tuple, list)):
            for nested in value:
                check(nested)
    for value in [TEXT, CONTENT, META, PACKAGES]:
        check(value)


def test_unique_titles_and_descriptions(client):
    for language in ("en", "el"):
        titles, descriptions = [], []
        for key in META:
            path = "/" if key == "home" else "/" + key
            soup = BeautifulSoup(client.get(path + "?lang=" + language).data, "html.parser")
            titles.append(soup.title.text)
            descriptions.append(soup.find("meta", attrs={"name": "description"})["content"])
        assert len(set(titles)) == len(titles)
        assert len(set(descriptions)) == len(descriptions)


def test_mobile_and_accessibility_markup(client):
    soup = BeautifulSoup(client.get("/contact?lang=en").data, "html.parser")
    assert soup.select('a[href="#main"]')
    assert soup.select('button[aria-controls="primary-nav"]')
    for field in soup.select('#project-form input:not([type="hidden"]), #project-form select, #project-form textarea'):
        assert soup.find("label", attrs={"for": field["id"]}), field
    css = Path("app/static/css/site.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in css
    assert "focus-visible" in css
    assert "@media(max-width:700px)" in css


def test_security_headers_and_errors(client):
    response = client.get("/")
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert "SameSite=Lax" in response.headers["Set-Cookie"]
    assert client.get("/missing").status_code == 404


def test_no_secrets_created():
    example = Path(".env.example").read_text()
    assert re.search(r"^SECRET_KEY=$", example, re.M)
    assert re.search(r"^MAIL_APP_PASSWORD=$", example, re.M)
