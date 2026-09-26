# Production environment inventory

Inspected against application code and Flask CLI usage on 26 September 2026. All examples are formats/placeholders, never current values. Store secrets in the hosting secret manager, not Git or command arguments.

| Variable | Purpose / production requirement | Secret? | Example FORMAT only | Source |
| --- | --- | --- | --- | --- |
| `FLASK_ENV` | Set production before importing app | No | `production` | Release configuration |
| `FLASK_DEBUG` | Must be disabled; enabled values rejected | No | `0` | Release configuration |
| `SECRET_KEY` | Session/CSRF signing, required, 32+ characters | Yes | `<random-private-value>` | Generate separately per environment; secret manager |
| `DATABASE_URL` | Required production PostgreSQL connection | Yes | `postgresql+psycopg://<user>:<encoded-password>@<host>:<port>/<database>?sslmode=verify-full` | Database provider / secret manager; configure provider CA as needed |
| `RATELIMIT_STORAGE_URI` | Required shared Redis; redis/rediss only in production | Yes when authenticated | `rediss://<user>:<encoded-password>@<host>:<port>/<db>` | Redis provider / secret manager |
| `BASE_URL` | Public HTTPS origin, no path/query; canonical/sitemap source | No | `https://<canonical-hostname>` | Domain configuration |
| `TRUSTED_HOSTS` | Comma-separated allowed hostnames including BASE_URL host | No | `<canonical-host>,<other-host>` | Domain/proxy configuration |
| `MAIL_ENABLED` | true for intended production notification workflow | No | `true` or `false` | Release configuration |
| `MAIL_HOST` | SMTP hostname | No | `<smtp-hostname>` | Mail provider |
| `MAIL_PORT` | SMTP port, integer 1–65535 | No | `<smtp-port>` | Mail provider; Gmail STARTTLS normally 587 |
| `MAIL_USE_TLS` | STARTTLS; port 465 uses implicit TLS; false allowed only on 465 | No | `true` | Mail provider/security configuration |
| `MAIL_ADDRESS` | SMTP login, From and To address | Account identifier | `<mailbox>@<domain>` | Owner's mail account |
| `MAIL_APP_PASSWORD` | Required when enabled; never normal account password | Yes | `<provider-issued-app-password>` | Gmail account security / secret manager |
| `CALENDLY_SCHEDULING_URL` | HTTPS calendly.com event; blank shows alternatives | No | `https://calendly.com/<account>/<event>` | Owner's event |
| `FLASK_SKIP_DOTENV` | Flask CLI setting: prevent automatic local dotenv loading | No | `1` | Production command environment |

There is **no REDIS_URL variable used by this app**. Set RATELIMIT_STORAGE_URI. Production explicitly disables in-memory fallback and error swallowing; Redis failure returns an error. Flask config keys such as RATELIMIT_ENABLED are not exposed as environment settings by the application.

Inject FLASK_ENV=production before startup and FLASK_SKIP_DOTENV=1 for CLI commands. The factory then skips its `.env` load. Local development permits ignored `.env`, an environment-supplied signing key and SQLite default when DATABASE_URL is blank. Never copy local credentials/databases to production. URL-encode credentials in connection URLs.

`LOCAL_STAGING_DB_PASSWORD` is a local Compose tooling variable, **not a production application variable**. It lives in ignored `.env.local-staging`, generated with `python scripts/staging_verify.py --prepare`. The runner creates a fresh signing key and temporary database URL in memory, with mail disabled and Calendly blank. It does not read the real `.env`.

Run `python -m flask --app wsgi create-admin`: interactive email, then hidden password and confirmation. Email is stored in the existing username column and used as the login username. Existing usernames still work. No schema change or automatic admin creation occurs. Password command-line arguments are unsupported.
