# Staging checklist

No deployment performed. Complete staging verification before separately authorizing production deployment.

## Current local verification status

Verified on 26 September 2026: Docker 29.8.0 and Compose v5.5.1 with Docker Desktop Linux containers under WSL 2. Both services became healthy; live PostgreSQL migrations/integration, Redis rate limiting and temporary loopback HTTP startup passed. Containers were removed using the documented teardown. See [STAGING_VERIFICATION.md](STAGING_VERIFICATION.md) for final results and remaining pre-launch checks.

## Disposable local PostgreSQL/Redis verification

Run from `C:\Freelance_Dev_Website`:

```powershell
docker --version
docker compose version
docker info --format '{{.ServerVersion}}'
.\.venv\Scripts\python.exe scripts\staging_verify.py --prepare
docker compose --env-file .env.local-staging -f compose.local-staging.yaml up -d --wait
.\.venv\Scripts\python.exe scripts\staging_verify.py
docker compose --env-file .env.local-staging -f compose.local-staging.yaml down
```

Always pass the explicit --env-file so Compose does not load the real `.env`. Do not print credentials or run `docker compose config`. The local-only password is fresh, ignored by Git and never reused from production/development. Official postgres:17-alpine and redis:7.4-alpine version lines were selected; image pulls and Compose startup were verified locally.

Services bind only to 127.0.0.1 on PostgreSQL port 55432 and Redis port 56379. Container data uses ephemeral tmpfs; stopping/recreating services loses staging data. No host data mounts or development SQLite access. Redis is unauthenticated and unencrypted for this loopback-only disposable setup; do not deploy this Compose file remotely. Actual staging/production requires protected authenticated services and appropriate TLS.

The runner preserves Windows SYSTEMROOT for PostgreSQL authentication while isolating application environment settings. It also briefly starts a loopback HTTP server, verifies Greek/English pages and admin login, and stops the server. This local HTTP check does not verify TLS or a production WSGI server. The runner creates a uniquely named staging_verify_* PostgreSQL database, executes upgrade/current/check, verifies revision/indexes/constraints, exercises admin/lead/portfolio CRUD, Greek/English Unicode and rollback. It checks real Redis counters/429 responses and injects a Redis error to verify no memory fallback. It runs production Flask through the in-process WSGI test client with HTTPS metadata; this does **not** prove real TLS or production-server behavior. SMTP is blocked and Calendly disabled. It deletes only its own database and Redis key prefix; no shared flush or development database mutation. If interrupted, teardown of these disposable containers removes leftovers. Safe results go to `.test-tmp/staging-live-result.json` after a live attempt. A blocked run is not a pass.

## Exact ordered flow for staging and eventual production

1. **Create staging environment.** Isolate host/account/network and secrets, restrict access/indexing, install requirements in a fresh environment and select a supervised production WSGI server. First complete the disposable local verification above.
2. **Configure PostgreSQL.** Fresh database/user, least privilege, network restrictions, verified TLS. Never copy the development SQLite database. Verify actual provider migration/CRUD/restore behavior.
3. **Configure Redis.** Isolated shared service, authentication/access restrictions and TLS as appropriate. Set RATELIMIT_STORAGE_URI; verify connectivity and shared counters across workers.
4. **Configure environment variables.** Follow PRODUCTION_ENVIRONMENT.md. Explicit production mode, debug off, new private signing key, database/Redis URLs, HTTPS BASE_URL and TRUSTED_HOSTS. Set FLASK_SKIP_DOTENV=1 for CLI. Never log/commit credentials.
5. **Run migrations.** Back up existing staging data if applicable; explicitly run `python -m flask --app wsgi db upgrade`, `db current` and `db check`. Check revision/indexes/constraints. Import must not migrate or seed.
6. **Create production-style admin.** Run `python -m flask --app wsgi create-admin`. Enter email and a unique 16–256-character password at the hidden confirmation prompt. Use email in the login username field. Verify duplicate/default-password rejection. Seed-dev remains blocked in production.
7. **Verify HTTPS.** Configure certificate, DNS, HTTP redirects and private WSGI binding. Configure trusted proxy scheme/client-IP handling for the actual topology; verify secure CSRF and distinct rate-limit buckets. Do not trust arbitrary forwarded headers.
8. **Verify BASE_URL.** Canonical HTTPS origin, no path/query, matching allowed hostname. Verify domain redirects and absence of localhost URLs.
9. **Verify Greek site.** Navigation, titles, text, pricing, validation and stored Greek Unicode.
10. **Verify English site.** Repeat all pages/flows; verify language switch and English metadata.
11. **Submit test lead.** Synthetic identifiable data via HTTPS form with CSRF; verify success redirect.
12. **Verify lead in admin.** Content/language, notes/status updates, logout, unauthorized rejection and CSRF. Verify passwords are hashed without displaying values/hashes.
13. **Verify Gmail notification.** Manually configure/enable mail and confirm receipt for a synthetic enquiry. Optional explicit `python -m flask --app wsgi mail-smoke-test` sends real mail; never automate it in tests. Check failed/pending status and persistence despite mail failure.
14. **Verify Calendly.** Manually test actual event, direct booking and post-lead prefill; inspect mobile behavior/CSP in real browser. Automated tests must not contact Calendly.
15. **Verify rate limiting.** Check 429 on contact/login, per-client proxy behavior and shared worker counters. In isolated staging, verify Redis outage fails rather than silently falling back to memory.
16. **Verify sitemap and robots.txt.** Correct BASE_URL, localized URLs, canonical/hreflang/OG/JSON-LD. Restrict/noindex staging at the host: current public robots behavior is for the eventual public site, not staging access protection.
17. **Verify secure cookies.** Actual HTTPS responses: Secure, HttpOnly, SameSite=Lax. Valid CSRF succeeds, absent/invalid tokens fail.
18. **Verify error pages.** Safely check custom 403/404/500, redacted logs, debug disabled and alerts for database/Redis/mail failures. No private traceback/content exposure.
19. **Verify backup setup.** Encrypted scheduled backups, restricted access, agreed retention/RPO/RTO and documented isolated restore. Plan secure configuration recovery, monitoring and operational ownership.

Before public launch, complete all bilingual legal placeholders and approve the privacy notice/version. After staging passes, review and commit intended changes, obtain separate deployment authorization and repeat this sequence with fresh production resources. No push or deployment is included in this verification.
