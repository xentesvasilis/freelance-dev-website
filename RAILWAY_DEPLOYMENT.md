# First Railway staging deployment preparation

Prepared 26 September 2026. **No deployment or Railway account access performed.** Existing Flask/SQLAlchemy/Alembic/Redis architecture retained. Real `.env` and development SQLite must never be uploaded, copied into Railway variables, or used for cloud migrations. All values below are instructions or placeholders.

## Repository and service setup

Use one GitHub-backed Flask web service, one Railway PostgreSQL service and one Railway Redis service in the same isolated staging environment. No web-service volume, Docker deployment, extra worker service or second application is required. Use one web replica initially.

Railpack detects `requirements.txt`; `.python-version` selects Python 3.12 (matching local testing; patch release can vary). Existing dependencies already include Linux Gunicorn, psycopg binary and Redis support. No dependency additions were needed. Do not use `run.py` or the Flask development server in Railway. [Railpack Python documentation](https://railpack.com/languages/python).

This preparation uses dashboard deployment settings plus `gunicorn.conf.py`. No duplicate Procfile, Railway JSON/TOML or Nixpacks config was added. Railway's current config-as-code reference marks legacy Railway JSON/TOML configuration deprecated; do not introduce it for this first deployment. [Configuration reference](https://docs.railway.com/config-as-code/reference).

After separate deployment authorization, review/commit/push the intended files, create an isolated Railway staging project/environment, add PostgreSQL and Redis, and connect the reviewed GitHub branch to a web service. Configure variables/settings before allowing a deployment to proceed. GitHub connection or subsequent pushes may trigger deployment: keep automatic deployment disabled until configuration is reviewed. Never connect production resources.

## Exact deployment settings

| Setting | Value |
| --- | --- |
| Root directory | Repository root |
| Builder | Railpack, Python detection |
| Start command | `gunicorn wsgi:app` |
| Pre-deploy command | `python -m flask --app wsgi db upgrade` |
| Health check path | `/health` |
| Health check timeout | 120 seconds |
| Web replicas | 1 initially |
| Public ingress | Railway HTTPS domain; no public TCP proxy for web socket |

`wsgi.py` exports `app = create_app()`. Gunicorn automatically reads root `gunicorn.conf.py`: bind `0.0.0.0:$PORT`, one gthread worker, two threads, timeout 60 seconds, graceful timeout 30 seconds, keepalive 5 seconds, no preload. PORT defaults to 8000 only outside Railway. These are conservative initial settings; inspect actual memory and latency before scaling. The worker timeout is not a strict per-request deadline for gthread. Error output goes to stderr and minimal access records to stdout. [Gunicorn settings](https://docs.gunicorn.org/en/stable/settings.html).

`GET /health` and HEAD are unauthenticated process-liveness checks returning only `{"status":"ok"}`. They do not query PostgreSQL/Redis, mutate sessions or consume rate-limit counters. No public diagnostics/readiness endpoint was added. Database readiness is separately checked by migrations and smoke tests. Railway probes use Host `healthcheck.railway.app`, which must be allowed. Its deployment health check does not provide ongoing monitoring. [Railway health checks](https://docs.railway.com/deployments/healthchecks).

## Environment inventory

Configure these on the **web service**. Values marked secret belong in Railway's variable UI/secret controls, never Git, command arguments, screenshots or logs. Service names in reference expressions are examples: select the actual service with Railway's reference picker. References avoid copying credentials. [Railway variables](https://docs.railway.com/variables).

| NAME | SECRET YES/NO | PURPOSE / exact staging setting | WHERE VALUE COMES FROM |
| --- | --- | --- | --- |
| FLASK_ENV | No | `production`; activates existing production guards before import | Set explicitly |
| FLASK_DEBUG | No | `0`; debug is prohibited | Set explicitly |
| FLASK_SKIP_DOTENV | No | `1`; prevents Flask CLI dotenv loading | Set explicitly |
| SECRET_KEY | Yes | Session/CSRF signing, fresh random 32+ characters | Generate privately for staging; never reuse local/test key |
| DATABASE_URL | Yes | PostgreSQL connection; use a service reference, with TLS policy below | Railway PostgreSQL DATABASE_URL via `${{Postgres.DATABASE_URL}}` |
| REDIS_URL | Yes | Shared Redis limiter backend | Railway Redis REDIS_URL via `${{Redis.REDIS_URL}}` |
| BASE_URL | No | Exact `https://<generated-staging-domain>` origin, no path/query | Railway web Networking > Generate Domain |
| TRUSTED_HOSTS | No | `<generated-staging-domain>,healthcheck.railway.app`; hostnames only, no wildcard | Generated hostname plus Railway probe host |
| TRUST_RAILWAY_PROXY | No | `true` only for the edge-only ingress described below; default false | Explicit reviewed ingress setting |
| MAIL_ENABLED | No | `true` to send; `false` disables notifications without credentials | Deployment choice |
| MAIL_PROVIDER | No | Explicit `resend` for Railway Trial/Free/Hobby; `smtp` for local or SMTP-capable hosting | Set explicitly; never inferred from credentials |
| MAIL_ADDRESS | Account identifier | `xentesvasilis@gmail.com` notification recipient | Set explicitly on the Railway web service |
| RESEND_API_KEY | Yes | Required for enabled Resend; HTTPS bearer credential, never logged | Resend dashboard, stored as Railway secret |
| RESEND_FROM_ADDRESS | No | Verified sender identity; e.g. `Website Leads <onboarding@resend.dev>` for initial testing or a verified domain sender | Resend sender/domain configuration |
| MAIL_HOST | No | SMTP alternative only; `smtp.gmail.com` | Mail provider |
| MAIL_PORT | No | SMTP alternative only; `587` STARTTLS or `465` implicit TLS | Mail provider |
| MAIL_USE_TLS | No | SMTP alternative only; `true` for STARTTLS | Mail provider |
| MAIL_APP_PASSWORD | Yes | SMTP alternative only; Gmail App Password | Mail account security / Railway secret |
| CALENDLY_SCHEDULING_URL | No | Blank initially; later HTTPS calendly.com event URL | Owner's selected staging/test event |
| PORT | No | Gunicorn listener; normally do not set manually | Railway injects this runtime value |

Optional compatibility variable: `RATELIMIT_STORAGE_URI` (secret: **Yes** when credentialed) is the existing explicit Redis override. Leave it **unset on Railway** when using REDIS_URL. Resolution order is nonempty RATELIMIT_STORAGE_URI, then nonempty REDIS_URL, then memory only for development. A stale `memory://` override is rejected in production, even if REDIS_URL is also present. Production never enables memory fallback and never swallows Redis failures. No other limiter/proxy Flask config keys are exposed as environment switches.

## PostgreSQL compatibility and migrations

Railway supplies a PostgreSQL DATABASE_URL. Existing normalization accepts `postgres://`, `postgresql://` and `postgresql+psycopg://`, selecting psycopg 3 and preserving URL-encoded credentials and query parameters. Current `psycopg[binary]>=3.2,<4` supports libpq TLS parameters; no extra driver is required. Railway documents an SSL-enabled PostgreSQL image. [Railway PostgreSQL](https://docs.railway.com/databases/postgresql).

Use the service's private reference rather than public TCP credentials. For staging, require encrypted PostgreSQL transport: if the referenced URL has no query, set the web DATABASE_URL reference expression to `${{Postgres.DATABASE_URL}}?sslmode=require`. If it already has a query, merge the TLS parameter appropriately without copying credentials. Confirm the selected template accepts TLS. `require` encrypts transport but does not establish full hostname/CA verification; use `verify-full` only with the provider's verified CA and matching host configuration. The application does not force TLS or remove provider parameters. Do not silently downgrade on connection failure. Provider TLS behavior remains a manual cloud check.

Railway Redis supplies REDIS_URL; the app now consumes it directly. Use the private referenced URL unchanged. `redis://` is unencrypted at the Redis protocol layer; `rediss://` requires a TLS-capable endpoint and valid certificate trust. Do not change the scheme without checking the selected template. Keep databases private and verify their networking/TLS policy before public go-live. [Railway service reference example](https://docs.railway.com/guides/docker-compose).

The pre-deploy command runs once per deployment in a separate container with service variables/private networking. A nonzero exit blocks that deployment. It is appropriate here because migrations operate on PostgreSQL and need no persistent application filesystem. [Railway pre-deploy commands](https://docs.railway.com/deployments/pre-deploy-command).

```sh
python -m flask --app wsgi db upgrade
```

No migrations, `create_all`, seed or database reset run at Python import or Gunicorn worker startup. Do not run migrations in the build phase: it must not depend on runtime private networking. Current repository head is `c8a4e291d630` (additive private CRM table, following `784018745121`). See PROJECT_CRM.md before releasing the CRM extension. After deployment, in the staging web container:

```sh
python -m flask --app wsgi db current
python -m flask --app wsgi db check
```

Expect head and no new upgrade operations. Serialize releases; do not run competing migrations or automatic downgrades. A failed web rollout does not roll back a successful database migration. Future migrations must remain compatible with the still-running prior release; verify backups before schema changes to nonempty databases.

## HTTPS, BASE_URL and proxy trust

Set BASE_URL to the generated HTTPS origin and TRUSTED_HOSTS to its exact hostname plus the probe hostname. Canonical links, sitemap, hreflang, Open Graph and JSON-LD use BASE_URL; no Railway hostname is hardcoded in application code. Existing secure cookies remain Secure, HttpOnly and SameSite=Lax. Railway provides domain TLS and redirects HTTP at its edge. [Public networking](https://docs.railway.com/networking/public-networking).

There was no existing ProxyFix configuration. Opt-in `TRUST_RAILWAY_PROXY=true` installs a narrow adapter: ProxyFix trusts one rightmost X-Forwarded-Proto value, with x_for=0, x_host=0, x_port=0 and x_prefix=0. It obtains the client IP from a single validated X-Real-IP address. X-Forwarded-For, forwarded host, port and prefix are ignored. Missing/invalid X-Real-IP retains the peer IP. Gunicorn's separate forwarded-header interpretation is disabled to avoid competing policies. These choices follow Railway's documented X-Real-IP and HTTPS scheme headers. [Edge header contract](https://docs.railway.com/networking/public-networking/specs-and-limits).

This is an ingress trust boundary, not header authentication. Enable only when the public path is Railway's HTTPS edge and direct untrusted access to the Gunicorn socket is impossible. Do not add a TCP proxy for the web port; only trusted services may access it over the private network. Do not put another CDN/proxy in front without reviewing the topology. Verify on the actual staging edge that injected X-Real-IP/X-Forwarded-Proto values are replaced and two real clients have separate rate buckets. Local tests verify adapter behavior, not Railway's sanitization. If that verification fails, stop and correct ingress; do not guess hop counts or disable secure cookies/CSRF.

## Lead notification delivery and recovery

Railway Free/Trial/Hobby blocks outbound SMTP. For this live service, configure the web service explicitly with:

| Variable | Value/source |
| --- | --- |
| `MAIL_ENABLED` | `true` |
| `MAIL_PROVIDER` | `resend` |
| `MAIL_ADDRESS` | Notification recipient chosen by the owner |
| `RESEND_API_KEY` | Private API key from Resend, entered only in Railway's secret variable UI |
| `RESEND_FROM_ADDRESS` | Sender configured/verified in Resend; for initial testing `Website Leads <onboarding@resend.dev>` is supported subject to Resend account sending restrictions |

SMTP variables are not required for Resend and can be unset/ignored. The provider never falls back automatically. `MAIL_PROVIDER` defaults to SMTP solely for backwards-compatible local development; production should explicitly set Resend. The HTTPS transport uses Python's standard library, sends a text and escaped HTML body, fixes From to the configured Resend identity and sets Reply-To to the validated client address. `sent` means Resend accepted the API request, not that the recipient's mailbox ultimately received it. Investigate final delivery/bounce state in Resend and Gmail.

The existing Lead notification flow commits the Lead before calling a provider. A failed/disabled API call changes only its notification status; it never deletes the Lead. After adding the variables and deploying the new code, run the provider-selecting CLI smoke test from the web service environment:

```sh
python -m flask --app wsgi mail-smoke-test
```

It sends one harmless real email when enabled, so do this manually after verifying the recipient and sender. The command reports provider and success/failure only; it never prints credentials.

Then recover existing failed notifications individually: **Admin → Leads → open each failed Lead → Retry notification**. Retry sends the existing stored Lead and does not create/update the Lead submission or its status. Never bulk-change `email_status`; it becomes `sent` only after Resend accepts a retry. The retry action is admin-authenticated, POST/CSRF protected, row-locked on PostgreSQL and sends a signed request idempotency key to Resend to prevent duplicate processing of repeated submissions of the same form. Resend keeps idempotency keys for 24 hours. SMTP has no equivalent provider idempotency; a network timeout after remote acceptance can leave an ambiguous result. Even Resend API acceptance is not final mailbox delivery.

SMTP remains available for local development and Railway Pro+ if deliberately selected. Its Gmail STARTTLS/implicit-TLS settings are alternatives, not required Resend variables. No new client-facing project-status mail was added.

CALENDLY_SCHEDULING_URL remains environment-configured and restricted to HTTPS calendly.com URLs. Booking routes/tests do not call Calendly. No Resend or other external provider is contacted by automated tests.

## First admin

After migrations, open an interactive terminal inside the deployed **staging web container**, using the dashboard's copied SSH command or `railway ssh --service <web-service> --environment <staging-environment>` after confirming project selection. Railway SSH runs remotely; `railway run` instead launches locally and should not be used with private-only service URLs. [Railway SSH](https://docs.railway.com/cli/ssh).

```sh
python -m flask --app wsgi create-admin
```

Enter the admin email and a unique 16-256-character password at the hidden confirmation prompts. Use the normalized email as the login username. The existing CLI rejects duplicates/default passwords and stores a password hash. Never run seed-dev in Railway; production rejects it. No admin credentials were created by this task.

## Logging and backups

Gunicorn writes minimal method/status/size/duration access records to stdout and errors to stderr. It omits request URLs/query strings, IP addresses, headers and bodies, avoiding lead identifiers and Calendly prefill details in access logs. Flask's default stream handler writes to stderr; production unexpected-error logging includes exception type/endpoint rather than sensitive exception messages or submitted content. Existing database/mail failure messages are generic. No environment dumps, debug mode, SQL echo or SMTP debug logging should be enabled. Review platform network/build/migration logs separately and restrict access/retention; application redaction does not control Railway's own logs.

No backup system was implemented or claimed. Before go-live, verify the selected Railway plan/template's PostgreSQL backup availability, retention, scheduling, restore process and costs. Perform an isolated restore and check records/migrations, then document RPO/RTO and ownership. Deployment rollback is not database restore. [Railway backups](https://docs.railway.com/volumes/backups).

## Exact post-deployment smoke checklist

Use synthetic submissions only. `/health` is public by design; configure staging access restrictions separately if required. The current public robots behavior permits indexing, so restrict/noindex staging at the host before sharing its URL; robots directives alone are not access control.

1. Application deployment succeeds: build installs existing dependencies, pre-deploy exits 0 and Gunicorn starts with one worker/two threads.
2. `/health` returns HTTP 200 with only status ok, including the configured Railway probe.
3. HTTPS works on the generated domain; HTTP redirects. Verify edge header sanitization and correct HTTPS form/redirect behavior.
4. Secure cookies work: inspect Secure, HttpOnly, SameSite=Lax and successful CSRF-protected form submission over HTTPS.
5. Migrations are current: run `python -m flask --app wsgi db current` and `db check`; confirm head/no drift.
6. Create a production-style admin using the interactive create-admin command; verify login/logout and anonymous admin rejection.
7. Greek public pages work: navigation, text, forms and language switching.
8. English public pages work with the same checks.
9. Submit one clearly synthetic test lead with valid CSRF and consent.
10. Verify that lead in PostgreSQL/admin, including Unicode, status and notes persistence across a web restart.
11. Verify email notification: with MAIL_PROVIDER=resend, explicitly run the harmless provider smoke-test, confirm the test message arrives, submit one synthetic Lead, and check Resend acceptance plus the notification. Check final delivery separately; acceptance is not mailbox delivery.
12. Verify Calendly booking page and direct link using the intended event; do not create an unintended real booking.
13. Verify Redis-backed rate limiting: reach a controlled login/contact 429, verify a second real client has a separate bucket, and ensure forged forwarded headers cannot reset limits. Check shared Redis behavior after web restart; do not flush shared keys.
14. Verify sitemap.xml contains only the staging BASE_URL and correct bilingual URLs.
15. Verify robots.txt references the correct sitemap; confirm separate staging indexing/access policy.
16. Verify a missing route returns the custom 404 with debug off.
17. Inspect application, build and migration logs for errors and expected request statuses.
18. Verify no credentials, connection URLs, App Password or sensitive submission content appear in logs. Inspect privately; never paste secrets into an issue/chat.
19. Verify bilingual legal/business placeholders and privacy wording are approved before public launch.
20. Verify backup/restore plan on the selected Railway plan and complete an isolated restoration exercise before go-live.

## Verification and remaining boundaries

Final local results after Resend/retry changes: **190 passed**, including mocked Resend/SMTP, Lead persistence, retry authorization/CSRF/idempotency, existing CRM/public/Calendly tests, fresh and incremental migrations, production configuration, and template endpoint scans. `compileall` passed for app, migrations, scripts, tests, wsgi.py, run.py and gunicorn.conf.py. `pip check` reported no broken requirements. `git diff --check` passed. No migration was added and no external service was contacted.

Local automated configuration/health/proxy tests supplement the previous live PostgreSQL/Redis verification. All automated sockets, DNS resolution and SMTP and Resend API calls are mocked/blocked; no Railway, Gmail, Resend or Calendly account/API was used. Gunicorn is Linux-only and is not executed in the Windows virtual environment; its configuration is exercised locally, and actual Railpack/Gunicorn startup remains a first cloud deployment check.

Before staging: review/push only intended files after separate authorization, select the Railway project/plan, provision the three services, enter fresh variables/references, generate the domain, configure the exact deployment settings and verify the ingress assumptions. Configure Resend and manually run the harmless email smoke test after verifying the sender and recipient.

Before public go-live: complete the cloud checklist, edge spoofing/multiple-client checks, Resend delivery/Calendly manual checks, TLS/network review, legal approval, backups/restore, monitoring and ownership. Local success is not proof of these cloud checks. Nothing has been deployed by this preparation.
