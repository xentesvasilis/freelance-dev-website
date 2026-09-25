# Verification — 24 September 2026

## Results

| Check | Result |
| --- | --- |
| Complete pytest suite | **80 passed**, 17.99 seconds, no warnings reported |
| `compileall` | Passed for app, tests, migrations, scripts and WSGI entry point |
| `pip check` | No broken requirements found |
| Empty SQLite migration | Upgrade → schema comparison → downgrade to base → upgrade passed |
| Local application database | Upgraded to `784018745121` (head); no schema drift |
| Jinja `url_for` scan | All literal endpoints resolve; dynamic navigation and rendered internal links tested |
| Route map | Printed and inspected; documented in PROJECT_MAP.md |
| Package prices | Exactly €980 / €1,700 / €3,000 in both languages on home and pricing |
| Monthly maintenance | Exactly €79 / €99 / €119 in both languages |
| Browser layout | 11 public pages × 2 languages × 4 widths (1440, 768, 390, 320px); no horizontal overflow |
| Browser interaction | Language selection, mobile menu/Escape focus, validation, lead submission, redirect, admin login/status/notes/logout passed |
| Browser JavaScript | No page errors during the tested flows |
| Secret-file inspection | No `.env` created; secret placeholders blank; no private-key/API-token patterns found in reviewed source |

Browser screenshots and machine-readable results are in [artifacts/browser-report.json](artifacts/browser-report.json). Example previews: [desktop home](artifacts/home-en-1440.png), [Greek mobile contact](artifacts/contact-el-390.png), [Greek mobile pricing](artifacts/pricing-el-390.png).

## Implemented scope

All 11 required public pages, bilingual session selection, centralized copy/pricing, a protected admin dashboard and lead list/details, status/notes forms, three SQLAlchemy models, initial Alembic migration, SMTP notification service, optional Calendly inline embed, development/admin/mail CLI commands, responsive assets and SEO endpoints.

Models: `Admin`, `Lead`, `PortfolioProject`. Source/documentation/configuration files are mapped in [PROJECT_MAP.md](PROJECT_MAP.md); setup and configuration are in [README.md](README.md).

Security verification covers CSRF, rejected unauthorized mutations, hashing, login/contact throttling, invalid choice/length/email validation, header injection, escaped HTML, safe redirects, opaque lead references, production configuration guards, blocked development-admin login in production and redacted SQL parameters. Lead-save ordering is checked with an independent database connection before the email mock runs. SMTP failure leaves the committed lead and a normal success page.

SEO includes unique bilingual titles/descriptions, canonical URLs, language alternates, Open Graph metadata, accurate Person JSON-LD, semantic headings, robots.txt and a localized XML sitemap. No analytics tracker is installed.

## Integration status and limits

- **Calendly:** implemented with explicit-load inline embedding and session-bound, expiring name/email prefill. Event URL is blank. Real provider rendering/booking has not been exercised.
- **Email:** implemented and mocked successfully, including failure behavior and smoke-test CLI. Disabled by default; no live SMTP connection or message was sent.
- **Payments:** described as an offered capability; no payment processing is installed on this marketing site.
- **Database:** SQLite verified locally. PostgreSQL-compatible models and driver are present; a live PostgreSQL instance was not used.
- **Deployment:** not performed. Local browser QA used an isolated temporary database and closed its server afterwards.
- **Accessibility:** semantic forms, visible focus, keyboard menu behavior, responsive layout and reduced motion checked. This is not a formal assistive-technology audit.

## Manual configuration still required

1. Private stable signing key, production domain/base URL, trusted hosts, database and shared rate-limit storage.
2. Real Calendly scheduling URL and private SMTP app password; explicitly enable mail and run the harmless smoke test.
3. Final business/legal identity, tax wording, retention/deletion policy, processor details and legal review of the marked drafts.
4. Production admin credentials, hosting/HTTPS/proxy configuration, backup/restore plan, monitoring and real integration checks in staging.

Next recommended step: owner review of the bilingual copy and package scope, followed by privately configured staging acceptance tests for the real Calendly and email workflows.
