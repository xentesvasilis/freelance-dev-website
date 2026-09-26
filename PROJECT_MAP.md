# Project map

## Architecture

```text
wsgi.py                        WSGI entry point
app/__init__.py                Factory, environment, headers, error handling
app/extensions.py              SQLAlchemy, Migrate, CSRF, Limiter
app/models.py                  Admin, Lead, ProjectCase, PortfolioProject
app/forms.py                   Localized lead validation and admin forms
app/public.py                  Public pages, language, lead save, booking, SEO
app/admin.py                   Authentication, dashboard, lead workflow and private project CRM
app/mail.py                    Escaped multipart notifications and TLS SMTP
app/cli.py                     seed-dev, create-admin, mail-smoke-test
app/content.py                 EN/EL copy, choices, pricing, SEO descriptions
app/legal.py                   Original bilingual legal drafts and placeholders
app/templates/                Shared Jinja layout, pages, components, admin
app/static/                   Local responsive CSS, JavaScript and SVG favicon
migrations/                   Alembic initial schema plus additive ProjectCase revision
tests/                        Public, lead, security, CLI and migration tests
scripts/browser_check.py      Optional desktop/mobile browser validation
artifacts/                    Local verification screenshots/report
instance/                     Ignored local SQLite DB
.test-tmp/                    Ignored Windows-safe pytest temp DBs
```

## Models

- **Admin:** unique username, salted password hash. No customer accounts.
- **Lead:** internal integer ID; cryptographically random public ID; name/email/optional phone/company; industry; JSON requirements; budget; description; timeframe; language; constrained status; created/updated/contacted timestamps; internal notes; privacy acknowledgement timestamp/version; email delivery status. Timestamps are UTC (SQLite returns naive representations; PostgreSQL supports timezone-aware values).
- **PortfolioProject:** slug, bilingual JSON title/short description/description/features, industry, technologies, future image path, featured/published flags and sort order. Initial technical outline is shared localized content; no fabricated client rows are seeded. Published database entries render after it.

## Routes

| Route | Methods | Purpose |
| --- | --- | --- |
| `/` | GET | Home, services/pricing/process/case-study previews |
| `/services` | GET | Website, automation, custom app and integration categories |
| `/industries` | GET | Five professional-service sectors |
| `/portfolio` | GET | Anonymized technical outline and future published projects |
| `/pricing` | GET | Exactly three packages and maintenance terms |
| `/process` | GET | Discovery → planning → development → testing → launch → maintenance |
| `/about` | GET | Developer background and approach |
| `/contact` | GET, POST | Contact details and minimal lead qualification |
| `/book-call` | GET | Optional Calendly inline booking, expiring prefill |
| `/privacy`, `/terms` | GET | Bilingual legal drafts |
| `/language` | POST | CSRF-protected session language, local redirect allowlist |
| `/sitemap.xml`, `/robots.txt` | GET | Bilingual discovery; admin/booking excluded |
| `/admin/login` | GET, POST | Rate-limited admin authentication |
| `/admin/logout` | POST | Authenticated, CSRF-protected logout |
| `/admin` | GET | Authenticated lead counts |
| `/admin/leads` | GET | Authenticated, paginated lead list |
| `/admin/leads/<public_id>` | GET | Full lead detail and edit forms |
| `/admin/leads/<public_id>/status` | POST | Authorized status change with CSRF |
| `/admin/leads/<public_id>/notes` | POST | Authorized notes change with CSRF |

## External integrations

- **SMTP:** disabled by default. One mailbox is username/sender/recipient. Gmail defaults; STARTTLS/implicit TLS and verification. No live mail during tests.
- **Calendly:** empty event URL by default. Loads on visitor action. Name/email prefill only after an own-session lead within 30 minutes. No API token, webhook, customer accounts or booking-state claims.
- **GitHub:** static, safe new-tab links only. No scraping or repository-readiness claims.
- **Stripe:** described as a service/case-study capability, **not integrated into this marketing site**.
- **Analytics:** structure and metadata only; no analytics script or tracking ID installed.

## Environment groups

- App/data: `SECRET_KEY`, `DATABASE_URL`, `BASE_URL`, `FLASK_ENV`.
- Email: `MAIL_ENABLED`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_ADDRESS`, `MAIL_APP_PASSWORD`.
- Booking: `CALENDLY_SCHEDULING_URL`.
- Production perimeter: `TRUSTED_HOSTS`, `RATELIMIT_STORAGE_URI`.

See `.env.example` (blank secrets) and README for configuration and release guidance. No real `.env` is committed or generated.

## Workflows and decisions

1. Non-blocking first-visit language choice; session persistence; a shared translation catalog. Query language variants support accurate canonical/hreflang URLs.
2. Lead POST → validation → durable commit → attempted email → notification-state commit → success redirect. Email failure never removes the saved lead. No automatic retry queue yet; admin is authoritative.
3. Direct booking or brief → booking; both accountless. Session cookie contains an opaque reference, never name/email or brief contents. Prefill expires in 30 minutes.
4. Admin login clears the previous session, uses password hashes and checked database identity; all mutations require POST/CSRF/authentication. First contact timestamp is preserved.
5. One pricing source renders both homepage and pricing page: €980/€1,700/€3,000 plus €79/€99/€119 monthly maintenance. Scope and external costs are explicit.
6. Restrained green/neutral identity, system-font stack, CSS illustrations, responsive cards, visible focus and reduced-motion support. No external fonts/images needed.
7. Local SQLite migrations; PostgreSQL-compatible types/driver; HTTPS/host/shared-limit guards for production. Production is prepared, not deployed.
8. Legal drafts explicitly identify missing business, processor, retention and tax decisions. No fake claims, testimonials, clients or performance metrics.
9. Test databases and browser artifacts remain within the project root; all SMTP is blocked or mocked in tests.

## Private CRM extension

- `app/models.py`: ProjectCase, status/priority constants, first-milestone timestamps, cents formatting and database constraints.
- `app/project_forms.py`: validated manual/edit/status/conversion forms; Decimal-to-integer-cents conversion.
- `app/crm.py`: Greek/English CRM labels.
- `app/templates/admin/projects.html`, `project_detail.html`, `project_form.html`, `_project_fields.html`: private project UI within the existing admin layout.
- `migrations/versions/c8a4e291d630_add_project_case.py`: additive table/index/constraint migration from 784018745121.
- `tests/test_projects.py`, `tests/test_project_migrations.py`: workflow, concurrency, privacy, money and schema preservation checks.

ProjectCase contains a random public ID, optional unique source Lead reference, client/contact/scope fields, EUR quote in cents, freeform package, constrained status/priority, optional target dates, first-reached milestone timestamps and private notes. It has no publication fields or relationship to PortfolioProject.

| Additional route | Methods | Purpose |
| --- | --- | --- |
| `/admin/projects` | GET | Authenticated list/search/filter |
| `/admin/projects/new` | GET, POST | Manual creation |
| `/admin/projects/<public_id>` | GET | Detail/timeline/edit forms |
| `/admin/projects/<public_id>/edit` | POST | Authorized validated changes |
| `/admin/projects/<public_id>/status` | POST | First-milestone-aware status update |
| `/admin/leads/<public_id>/convert` | POST | Confirmed idempotent private project creation |

The admin dashboard retains Lead metrics and adds project metrics/attention queries. No public route, booking automation or email flow is added. See [PROJECT_CRM.md](PROJECT_CRM.md) for lifecycle and release requirements. The public website is reported live by the owner; this CRM extension remains local and undeployed.
