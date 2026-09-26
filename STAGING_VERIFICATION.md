# Local staging verification report

Date: 26 September 2026. Scope: `C:\Freelance_Dev_Website` only. Local verification completed; nothing deployed, committed or pushed. No real email or Calendly calls.

## DOCKER STATUS

PASS. Docker CLI and server 29.8.0; Docker Compose v5.5.1. `docker --version`, `docker compose version` and `docker info` succeeded. Docker Desktop runs Linux containers under WSL 2. Initial sandbox access to the Docker pipe was denied; approved Docker access succeeded.

Used the existing `compose.local-staging.yaml` with explicit `--env-file .env.local-staging`. Pulled PostgreSQL 17 Alpine and Redis 7.4 Alpine. The generated local-only credential was never displayed. No real `.env` configuration was loaded.

## POSTGRESQL LIVE STATUS

PASS against PostgreSQL 17.11. The prepared integration runner created an empty, uniquely named `staging_verify_*` database and verified:

- Admin creation/read/update/delete, hashed login and duplicate rejection.
- Lead creation/read/status and notes updates through application routes.
- PortfolioProject creation/read/update/delete and JSON fields.
- Greek and English Unicode round trips.
- Lead status and Admin uniqueness enforcement, lead public-ID uniqueness schema, lead status/created-at indexes.
- Transaction rollback and recovery following constraint violations.

The runner dropped its database. A final query confirmed zero `staging_verify_*` databases remained.

## POSTGRESQL MIGRATION STATUS

PASS. Flask CLI `db upgrade`, `db current` and `db check` ran through Flask's CLI runner against the fresh PostgreSQL database. Alembic current revision: **784018745121 (head)**. Direct SQL confirmed the revision; schema inspection confirmed expected tables, indexes and constraints. Drift check reported **No new upgrade operations detected**.

## REDIS LIVE STATUS

PASS. Live PING, persistent rate-limit counters and cleanup against loopback Redis port 56379, database 15. The runner deleted only its own uniquely prefixed keys; no FLUSHDB/FLUSHALL. Final DBSIZE was zero.

## RATE LIMIT STATUS

PASS. Actual storage was RedisStorage. Login attempts returned four HTTP 200 responses followed by HTTP 429, after the preceding successful login. Redis counter keys were present. Production configuration explicitly disabled in-memory fallback and error swallowing. An injected storage ConnectionError produced HTTP 500, as expected, rather than a successful response using memory. The logged ConnectionError was intentional. This outage check used injection, not a physical Redis shutdown or a multi-worker test.

## APPLICATION STARTUP STATUS

PASS. The production-configured Flask application used the isolated PostgreSQL database and Redis, with debug disabled, mail disabled and Calendly blank. A temporary Werkzeug HTTP server bound only to an ephemeral 127.0.0.1 port served Greek and English home pages and admin login with HTTP 200, then shut down. Requests used the configured staging Host header. In-process checks also passed for admin/lead routes, secure-cookie attributes, sitemap, robots and custom 404.

This verifies local application startup; it does not verify real HTTPS, a reverse proxy or a production WSGI server.

## TEST RESULT

| Check | Final result |
| --- | --- |
| Full pytest | **105 passed in 14.85 seconds** |
| compileall: app, migrations, scripts, tests, wsgi.py, run.py | Passed |
| pip check | No broken requirements found |
| Live PostgreSQL migrations and integration | Passed |
| Live Redis and rate limiting | Passed |
| Temporary loopback HTTP startup | Passed; server stopped |
| Protected file SHA-256 comparison | `.env` and `instance/site.db` unchanged |

Final live runner exited 0. Its seven passed check groups are saved in `.test-tmp/staging-live-result.json` (pytest's configured temporary directory is cleared by future full test runs).

The initial live attempt failed because clearing the environment removed Windows SYSTEMROOT, preventing libpq from generating an authentication nonce. The runner now preserves only that OS setting alongside its explicit isolated application configuration. An elevated diagnostic attempt also encountered a temporary report-file permission error; the final normal workspace runs wrote the report successfully. Both issues are resolved for the verified workflow.

## CONTAINER STATUS

Both containers reached **healthy**, bound only to 127.0.0.1:55432 and 127.0.0.1:56379. No host database mounts; staging data was ephemeral. After successful checks and cleanup verification, the documented Compose `down` removed both containers and their network. Final Compose `ps -a` was empty. Downloaded images remain cached. The temporary HTTP server is stopped.

## FILES CHANGED

Changes during this continuation:

- `scripts/staging_verify.py`: preserve Windows SYSTEMROOT for PostgreSQL authentication; add temporary loopback HTTP startup verification with server shutdown and a narrowly scoped network allowlist.
- `STAGING_VERIFICATION.md`: replace blocked results with this final verified report.
- `STAGING_CHECKLIST.md`: update obsolete Docker blocker and describe verified startup coverage.
- `.env.local-staging`: generated ignored local-only credential file; retained for subsequent local runs.
- `.test-tmp/staging-live-result.json`: ignored final live result; pytest also generated temporary test files and Python bytecode caches.

Earlier uncommitted application, test and documentation changes were already present at the start of this continuation and were preserved. No application source or Compose configuration was changed during this continuation. The temporary checksum baseline was removed after successful comparison; no hashes or secret values were printed.

## BLOCKERS REMAINING

**None for the requested local staging verification.** Separate pre-launch work remains: actual staging WSGI/HTTPS/proxy behavior and multi-worker rate limiting; protected service credentials/TLS; explicitly authorized manual Gmail/Calendly checks; backup/restore exercise; legal/business placeholders and production environment provisioning. These are not claimed as verified here.

## EXACT NEXT STEP

Review this report and the existing changes locally. If proceeding toward a separately authorized staging environment, continue with step 1 of `STAGING_CHECKLIST.md` and its production-server/HTTPS checks. No deployment is authorized or performed by this task.

To repeat only the completed disposable local checks, follow the existing prepare / Compose up / runner / Compose down sequence in that checklist. Always use the explicit staging env file.
