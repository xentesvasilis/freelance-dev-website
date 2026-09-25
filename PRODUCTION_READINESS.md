# Production readiness audit

Audit date: 25 September 2026. Scope: this project only. No deployment, production database mutation, live SMTP or Calendly calls were performed. Real `.env` was not modified. Existing live integrations were reported working by the owner; this audit does not independently certify them.

## TEST RESULT

Final full pytest: **89 passed in 18.61 seconds**. `pip check`: **No broken requirements found**. `compileall` over app, migrations, tests, scripts, wsgi.py and run.py: **passed**. Fresh SQLite migration upgrade/check/downgrade/re-upgrade, PostgreSQL offline migration SQL, template endpoint scan, rendered internal links/static assets and route method scan: **passed within the full suite**.

Automated tests use temporary SQLite databases and isolated environment values. Socket connections and real SMTP are blocked; SMTP success/failure is mocked. Existing tests cover bilingual pages, pricing, persistence, validation, CSRF, admin authorization, rate limits, mail failures, links, static references and template endpoints. Added tests cover production guards, PostgreSQL offline migration SQL, no network connection on factory creation, safe error logging, production SEO URLs, route methods and development-session rejection. A credential-pattern scan of application/migration/script Python source also found no private-key blocks or tested credential patterns; this is not an exhaustive secret-history scan.

## SECURITY STATUS

Production configuration now rejects debug flags and attempts to enable `app.debug`. `SECRET_KEY` has no generated/default fallback; it must be supplied through environment (local `.env` is supported). Production enforces Secure/HttpOnly/SameSite=Lax cookies, CSRF, rate limiting and generic exception responses. Tests can explicitly provide isolated keys. Environment mode and boolean values are validated; missing production database/shared limiter configuration prevents startup.

SQLAlchemy parameterizes queries; SQL parameters are hidden in exceptions. Jinja autoescaping and JSON serialization protect templates/structured data; email HTML escapes submitted fields. Form single-line validation rejects control characters, and email subject normalization and `EmailMessage` prevent header injection. Login uses Werkzeug password hashing, generic errors, dummy password verification, a cleared session on login and a two-hour permanent session. Redirect targets use an exact local allowlist. Mutations use POST and CSRF. Admin routes query the current user on every request; development accounts are denied even for existing sessions in production.

Custom 403/404/500 (and 400/413/429/503) pages exist. Failed initial lead persistence returns 503; mail failure retains the lead. Production unexpected-error logs record exception class and endpoint only, omitting exception messages/tracebacks that could contain private data. Migration logging preserves existing loggers. Warnings/errors cover persistence and notification failures. Host logging/APM needs equivalent redaction and restricted retention.

`.gitignore` now excludes `.env`, `.env.*` including `.env.txt`, private key files, databases, logs, caches and artifacts; only `.env.example` is allowed. Private environment secret values were compared locally against 53 source/project files: **zero matches**. No values were printed. Known dummy/test/development credentials remain intentionally documented and are prohibited for production. No `.git` repository exists in this directory, so tracked files and history cannot be certified. Ignore rules do not prevent an intentional `git add -f`; inspect the future staged release and run a secret scanner including history before publishing. Never deploy `.env.txt` or development artifacts.

## DATABASE STATUS

SQLite is the local default when `DATABASE_URL` is blank; explicit URLs override it. Production requires `DATABASE_URL` and PostgreSQL/psycopg, with no SQLite fallback. `postgres://` and `postgresql://` normalize to `postgresql+psycopg://`. Models use portable JSON, datetime, boolean and SQLAlchemy types. Alembic owns schema changes; importing the app neither creates tables nor migrates/seeds data. Fresh SQLite upgrade, schema drift check, downgrade and re-upgrade are tested.

## POSTGRESQL READINESS

Psycopg is installed. Factory creation and PostgreSQL offline migration SQL are tested without connecting to a database. Connection pre-ping, 300-second recycle, ten-second PostgreSQL connect timeout and hidden SQL parameters are configured. Network/TLS/CA options belong in `DATABASE_URL`; verified TLS must be configured for the actual provider. A live PostgreSQL migration, CRUD, privilege/TLS and backup-restore test remains a staging blocker; offline SQL does not prove those behaviors. Budget connections across workers (default pool plus overflow: 15 per worker).

## ENVIRONMENT VARIABLES REQUIRED

| Variable | Production expectation |
| --- | --- |
| `FLASK_ENV` | `production`, explicitly injected before startup |
| `FLASK_DEBUG` | `0`; debug flags are rejected |
| `SECRET_KEY` | Private random value, at least 32 characters |
| `DATABASE_URL` | PostgreSQL psycopg URL with provider-appropriate TLS |
| `BASE_URL` | Public HTTPS origin without path/query |
| `TRUSTED_HOSTS` | Allowed hostname list including canonical hostname |
| `RATELIMIT_STORAGE_URI` | Shared protected `redis://` or `rediss://` backend |
| `MAIL_ENABLED` | `true` for the intended notification workflow |
| `MAIL_HOST`, `MAIL_PORT`, `MAIL_USE_TLS` | Gmail: smtp.gmail.com, 587, true |
| `MAIL_ADDRESS`, `MAIL_APP_PASSWORD` | Account address and private app password |
| `CALENDLY_SCHEDULING_URL` | Actual HTTPS calendly.com event URL |
| `FLASK_SKIP_DOTENV` | `1` for production Flask CLI commands |

Mail and Calendly may deliberately be disabled, but that would not satisfy the intended launch workflow. Enabled mail validates address without DNS lookup, credentials, host, port and encryption. `.env.example` contains only blank secrets/placeholders. Generate production secrets independently; never reuse test keys or print credentials in commands/logs.

## PRODUCTION START COMMAND

Linux, installed virtual environment and injected production configuration:

```sh
gunicorn --workers 2 --bind 127.0.0.1:8000 --timeout 60 --error-logfile - wsgi:app
```

Gunicorn has a Linux-compatible platform-marked requirement; it was not executed on this Windows audit host. Waitress is installed for Windows (`.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 wsgi:app`). `run.py` provides local Windows development support and refuses production mode. Neither start command supplies DNS, TLS, process supervision or trusted proxy configuration.

## LEGAL PLACEHOLDERS

All five explicit placeholder groups in `app/legal.py` require completion in **both English and Greek**:

1. Privacy / Who handles your enquiry: registered business identity and legally required business contact details.
2. Privacy / Email and service providers: actual hosting provider, processor agreements, processing locations, international transfers and safeguards.
3. Privacy / Optional Calendly booking: actual plan, agreement, transfers and cookie settings.
4. Privacy / Retention: periods for unanswered enquiries, closed leads, email copies, access logs and backup rotation; documented review/deletion process. Archiving does not erase records; no automatic deletion exists.
5. Terms / Draft terms: legal business identity, tax treatment, governing law, dispute arrangements and mandatory consumer disclosures.

Also approve the proposed processing basis and actual provider/cookie behavior, finalize both draft notices and dates, and update `Lead.privacy_version` from `2026-09-draft` when the approved notice is published. Confirm tax wording against pricing. No legal identity, address, tax status, retention period or governing law was invented by this audit. These are content completion tasks, not a legal compliance certification.

## SEO STATUS

Bilingual pages have unique titles/descriptions, canonical links, el/en/x-default hreflang, Open Graph title/description/type/URL/locale and Person JSON-LD. Canonical/hreflang/OG/structured data derive from `BASE_URL`; production-origin regression checks exclude localhost. Sitemap has 20 localized entries, excludes admin/booking, and uses `BASE_URL`; robots points to that sitemap and disallows admin/booking. Admin/booking responses also carry noindex. No dedicated social preview image is configured (optional). Internal links, anchors, static assets and literal template endpoints are checked; dynamic navigation is covered by rendering. External destinations and Google indexing were not contacted/verified.

## ADMIN STATUS

No prominent/public admin navigation links. Authentication gates dashboard/leads/detail; POST+CSRF gates mutations/logout. Passwords are hashed, login throttled and development credentials never created automatically. `seed-dev` refuses production, `create-admin` uses a hidden prompt, and reserved development credentials cannot authenticate in production. Create the first real admin after explicit migrations in a fresh database.

## DEPLOYMENT BLOCKERS

- Complete and approve all bilingual legal/business placeholders and privacy version.
- Provision the actual host/domain/HTTPS, PostgreSQL and shared Redis; inject fresh secrets.
- Verify trusted proxy client-IP and HTTPS scheme handling against the actual topology. Current app intentionally trusts no forwarded headers; incorrect proxy setup can group rate limits or break secure CSRF. Restrict direct WSGI access.
- Run live PostgreSQL migration/CRUD/restore checks and Linux WSGI smoke tests in staging.
- Verify Gmail/Calendly and the complete lead/admin flow on staging under production HTTPS/CSP.
- Inspect the actual release Git index/history for secrets and run a current dependency vulnerability advisory scan. `pip check` is compatibility verification, not a vulnerability audit. Requirements use version ranges; retain an exact tested release dependency snapshot.
- Establish and exercise backups, monitoring, log retention and operational ownership.

## MANUAL ACTIONS BEFORE GO-LIVE

Follow all 13 items in README's PRODUCTION DEPLOYMENT CHECKLIST, including explicit migrations, secure admin creation, domain/HTTPS, integration smoke tests, backups and monitoring. No deployment has been performed or authorized by this audit.

Reference guidance checked: [Flask deployment](https://flask.palletsprojects.com/en/stable/deploying/), [Flask configuration](https://flask.palletsprojects.com/en/stable/config/), [trusted proxies](https://flask.palletsprojects.com/en/stable/deploying/proxy_fix/), [SQLAlchemy pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html).
