# Private project CRM

This phase extends the existing authenticated admin area. The public website, requirements form, pricing, lead emails, Calendly booking, SEO and deployment configuration keep their existing responsibilities. No deployment, cloud migration, real email or booking was performed for this change.

## Lead and project lifecycles

A visitor's form submission remains a **Lead**: new → contacted → qualified, then explicitly won, lost or archived as appropriate. These are the existing lead statuses; project progress has its own record and never rewrites the original submission.

A **ProjectCase** is private operational data. Its main path is proposal → proposal_sent → accepted → in_development → testing → delivered → maintenance. An admin can explicitly choose any listed status, including reopening a cancelled case. There are no automatic status transitions, background jobs or client-facing status emails.

| Status | Meaning |
| --- | --- |
| proposal | Scope/quote being prepared |
| proposal_sent | Proposal shared with the prospective client |
| accepted | Client has accepted the project |
| in_development | Implementation has begun |
| waiting_for_client | Work awaits input or a decision from the client |
| testing | Quality checks and acceptance testing |
| delivered | Delivery completed |
| maintenance | Ongoing maintenance phase |
| on_hold | Work explicitly paused |
| cancelled | Project closed without completion; only an explicit admin change reopens it |

Status and priority labels are available in Greek and English. Priorities are low, normal, high and urgent. Side states do not automatically remember/restore a preceding state; choose the desired state explicitly.

## Convert a Lead

Open an authenticated Lead detail page. Check the confirmation explaining that a private project will be created and the Lead's status will remain unchanged, then select **Convert to Project / Μετατροπή σε Project**.

Conversion copies name, email, phone, company, industry and the original description into a new ProjectCase, initially at proposal/normal priority. Title defaults to `{Company or Client Name} – Project`. Lead notes, notification state, consent metadata, timestamps and original submission remain untouched. Conversion does **not** mark the Lead won; use the existing Lead status action explicitly if appropriate.

A Lead can have at most one ProjectCase. The database enforces unique non-null lead_id. PostgreSQL row locking serializes conversion and a unique-constraint recovery handles a competing conversion. Repeated confirmed POSTs redirect to the same project. Converted Lead pages display an **Open project** link instead of another conversion form. The project links back to its source Lead using that Lead's random public ID.

## Manual creation and editing

Use **Admin → Projects → New project**, or `/admin/projects/new`, for referrals, phone/email clients or Calendly-only contacts. No synthetic Lead or booking automation is created.

Required fields: title, client name, valid email, summary, status and priority. Phone, company, industry, package, quote, internal notes and target dates may be left blank. Package suggestions are Professional Website, Business Automation, Custom Digital Office and Custom, but arbitrary package names are supported.

Enter a quote in euros without grouping separators, e.g. `980`, `1700`, `3000` or `1700.50`. Blank means unquoted, and zero is a valid quote. Negative, non-finite, exponential, comma-formatted or more-than-two-decimal inputs are rejected. The maximum is EUR 21,474,836.47, the signed 32-bit integer-cents limit. Parsing uses Decimal, storage uses integer cents, and display uses integer arithmetic: €980, €1,700, €3,000 or €1,700.50. Currency is fixed to EUR in this phase. This is an internal quote field, not accounting/invoicing/payment processing.

The detail page shows project/client information, scope, source, internal notes and milestone/target dates. Use the quick status form or expand **Edit project** to update fields. Target delivery must be on or after target start if both are set. Invalid forms retain entered values and show errors without saving partial edits. No delete endpoint is included.

## Timestamps and dashboard

The first explicit assignment of accepted, in_development, testing, delivered or maintenance stamps accepted_at, development_started_at, testing_started_at, delivered_at or maintenance_started_at respectively. Moving away and back preserves the original value. Creating a manual record in an advanced status stamps that status only; missing earlier milestones are not invented. Ordinary updates retain created_at and update updated_at. UTC is used for stored/displayed timestamps; target dates are date-only. SQLite returns naive datetime representations while PostgreSQL stores timezone-aware timestamps.

Existing Lead metrics remain. Project metrics include:

- Active projects: every status except delivered, maintenance and cancelled; proposals and paused/waiting work are included.
- Proposals: proposal plus proposal_sent.
- Separate in-development, testing, delivered and maintenance counts.

**Projects requiring attention** shows up to ten active cases that are waiting_for_client, on_hold, overdue or due within seven days (inclusive, based on today's UTC date). Earliest target delivery comes first; undated waiting/paused projects follow. Delivered, maintenance and cancelled cases are excluded. This is a dashboard query only, with no scheduler or notification.

The list is paginated at 25 rows, sorted by latest updated time with a deterministic internal tie-breaker. Status, industry and priority filters combine with literal case-insensitive substring search across title, client name, company and email. SQL LIKE wildcard characters are escaped. This is simple database search, not full-text infrastructure; SQLite's Unicode case folding is more limited than PostgreSQL's locale-dependent behavior.

## Privacy and portfolio boundary

ProjectCase is independent of **PortfolioProject**, the public case-study model. No project status, including delivered, publishes anything or creates a portfolio record. This phase intentionally has no publishing CTA or automation. Any future publication needs a separate explicit editorial/privacy decision.

All CRM routes use the existing database-backed admin authorization. Mutations require POST and CSRF; sequential IDs never appear in route parameters, links or editable form fields. Random public_id values use `secrets.token_urlsafe(32)` and database uniqueness. Fields are allowlisted so submitted IDs, source Lead, currency and timestamps cannot be overwritten. Text is bounded, validated and escaped by Jinja. Database constraints protect status, priority, quote, currency, date ordering and source uniqueness. Failure logs contain generic project-save/conversion messages, not submitted data or SQL exception details.

Admin responses retain no-store and noindex headers. CRM data is not read by public routes, sitemap, portfolio or structured data. Authenticated navigation is rendered only after authorization. Internal notes remain private admin data and are not emailed. Calendly and existing Gmail configuration/lead notifications are unchanged. Project edits use ordinary last-save-wins semantics for editable content; there is no comments/history system or optimistic edit-conflict UI in this phase.

## Routes

| Route | Methods | Action |
| --- | --- | --- |
| `/admin/projects` | GET | Search/filter/paginate projects |
| `/admin/projects/new` | GET, POST | Manual creation form/save |
| `/admin/projects/<public_id>` | GET | Detail, timeline and edit forms |
| `/admin/projects/<public_id>/edit` | POST | Validated field update |
| `/admin/projects/<public_id>/status` | POST | Explicit status update |
| `/admin/leads/<public_id>/convert` | POST | Confirmed idempotent Lead conversion |

## Migration and later release

New Alembic revision **c8a4e291d630**, based on **784018745121**, creates only project_case, its constraints and indexes. Admin, Lead and PortfolioProject tables/data are preserved. The nullable unique Lead foreign key uses ON DELETE SET NULL; there is no Lead deletion feature in this change. Public IDs and timestamps have application defaults; direct external SQL insertion must supply required application-managed fields.

Before a separately authorized release, verify the current database revision and backup/restore arrangements. Use the existing Railway pre-deploy migration procedure:

```sh
python -m flask --app wsgi db upgrade
```

Then verify:

```sh
python -m flask --app wsgi db current
python -m flask --app wsgi db check
```

Expected head: `c8a4e291d630`, with no schema drift. Migrate before serving the new admin code: the new dashboard queries project_case. The upgrade is additive and compatible with the previous application. Do not stamp head, seed development users, run create_all or reset the database. Downgrade explicitly drops project_case and loses its private records; prefer application rollback with the additive table retained, and never downgrade a populated system without a reviewed backup/data plan.

Local verification includes fresh SQLite migrations, upgrade from a populated prior schema with before/after record comparisons, schema drift checks, test-only downgrade preservation and PostgreSQL incremental migration SQL generation. These checks do not contact Railway or claim that a cloud migration has been executed.

## Final local verification

- Full pytest: **168 passed in 26.87 seconds** (118 existing tests plus 50 CRM/migration cases).
- compileall: passed for app, migrations, scripts, tests, wsgi.py, run.py and gunicorn.conf.py.
- pip check: no broken requirements.
- Fresh SQLite upgrade/check/downgrade/re-upgrade: passed against a temporary database.
- Populated prior-schema upgrade: passed; all original Admin/Lead/PortfolioProject records preserved.
- Incremental PostgreSQL-compatible migration SQL: passed; new table/indexes/constraints only.
- Existing template url_for scan, route checks, public bilingual/SEO/pricing, lead notification and Calendly tests: passed.
- All network/SMTP access in automated tests blocked or mocked; no live Railway/Gmail/Calendly request.

The live cloud database has not been migrated. The existing local live-staging runner's expected revision was updated for this migration, but its Docker integration run was not repeated in this phase.
