# Documentation and implementation audit

## Scope and status

This audit compares the Markdown documents in this repository with the
current Python, templates, migrations, settings, CI, Render blueprint, and
tests. It distinguishes historical milestone records from current
documentation.

## Current documentation

### README and local setup

- **Claim:** README.md requires Python 3.14.10 and Django 5.2.19, and local
  setup uses SQLite with `DJANGO_SECRET_KEY`, debug mode, allowed hosts, and
  migrations.
- **Implementation:** config/settings.py requires `DJANGO_SECRET_KEY`,
  defaults `DEBUG=false`, allows localhost defaults only for debug, and permits
  SQLite only with debug enabled.
- **References:** README.md:3-56; config/settings.py:11-34 and 80-105.
- **Status:** Accurate for the current source. The `py -3.14` and
  `.venv\Scripts\Activate.ps1` instructions match the Windows setup; the
  environment does not load `.env`.

### Authentication and permissions

- **Claim:** Students are normal accounts, admin requires active staff, and
  superusers receive all Django permissions.
- **Implementation:** Student signup accepts only username, full name, level,
  and password in core/forms.py and stores no privilege fields. Django admin
  still requires staff and active status. Registration correction permission
  is specifically `core.change_registration`; it is delegated staff
  permission, not superuser-only.
- **References:** README.md:79-91; docs/functional-guide.md:58-107;
  core/forms.py:8-33; core/admin.py:111-114 and 171-174.
- **Status:** Accurate. The application can grant this permission to a staff
  account or a group; superusers inherit it.
- **Correction:** No delegated-role implementation exists outside Django
  permissions/groups. Existing text should continue to call it staff permission
  based, not superuser based.

### Registration correction

- **Claim:** Staff with `change_registration` can correct registrations,
  requiring at least one same-level course and a reason; corrections are
  atomic and audited.
- **Implementation:** RegistrationAdmin.correct_view checks
  `change_registration`; RegistrationCorrectionForm defines courses and reason;
  apply_correction locks and validates rows, replaces items atomically, sets
  `corrected_at`, and writes RegistrationAudit.
- **References:** core/admin.py:122-184 and 186-252; core/forms.py:52-68;
  core/models.py:119-154.
- **Status:** Implemented and covered by admin tests.
- **Missing/obsolete:** Some enum values in RegistrationAudit,
  `REGISTRATION_RESET` and `ACCOUNT_DELETION`, are not created by workflows.
  They describe possible audit actions, but no reset or account-deletion audit
  workflow exists. Do not describe them as implemented features.

### Registration reset and account deletion

- **Claim in the model:** RegistrationAudit.Action has reset and account
  deletion action labels.
- **Implementation:** There is no reset view, form, admin action, or delete
  workflow in core/views.py or core/admin.py. StudentProfile and Registration
  deletion behavior is blocked differently:
  `Registration.student` uses `PROTECT`, and StudentProfileAdmin
  has_delete_permission returns false. Django auth account deletion is
  therefore blocked for a student with registration history; an unregistered
  user can still follow ordinary Django deletion behavior.
- **References:** core/models.py:99-105 and 121-126;
  core/admin.py:43-58 and 118-119; core/tests.py:133-151 and 1095-1108.
- **Status:** Account deletion with history is blocked, not preserved through
  a custom reset/deletion transaction and not audited.
- **Conflict/decision:** docs/test-plan.md previously said deletion "preserves"
  the registration. The code instead rejects/block it. It has been corrected
  to say deletion is blocked. Registration reset policy is still unspecified
  in Course.md and requirements; no implementation should be inferred.

### Final registrations and student locking

- **Claim:** A student can submit at least one level-matched course once,
  cannot edit it, and cannot change level after submission.
- **Implementation:** student_dashboard locks profile/course rows in a
  transaction, validates a ModelMultipleChoiceField queryset and course IDs,
  creates Registration and RegistrationItem rows atomically, and redirects
  repeated POSTs to the saved view. StudentProfile.clean/save blocks level
  changes after Registration exists.
- **References:** core/views.py:48-137; core/forms.py:35-50;
  core/models.py:46-60 and 137-167.
- **Status:** Implemented and tested.

### Protected courses

- **Claim:** Registered courses cannot be deleted or changed to an
  incompatible level.
- **Implementation:** CourseRegistrationItem.course uses `PROTECT`; model
  level validation detects existing registrations with a mismatched level;
  CourseAdmin actions are disabled.
- **References:** core/models.py:59-116 and 170-173;
  core/admin.py:17-21; core/tests.py:163-185.
- **Status:** Implemented.

### Clean checkout and test setup

- **Claim:** The README setup is enough for migration and tests.
- **Implementation:** A clean checkout needs a virtual environment, dependency
  install, generated `DJANGO_SECRET_KEY`, debug true, allowed hosts, and
  `DATABASE_ENGINE=sqlite` before Django commands. The test runner creates an
  isolated test database by Django convention; it does not use db.sqlite3.
- **References:** README.md:24-38; config/settings.py:11-34 and 85-105;
  core/tests.py and core/test_migration_alignment.py.
- **Status:** Accurate; `.env.example` documents variables but settings does
  not load `.env` automatically.
- **Outdated instruction risk:** Earlier progress/test-result text says a local
  SQLite test database can be used under non-debug mode. That is contradicted
  by config/settings.py:94-98, which rejects SQLite outside debug mode.
  Non-debug SQLite checks require a PostgreSQL test database or a test-only
  settings change; no such settings module was added.

### Static collection

- **Claim:** Production collects WhiteNoise manifest static assets.
- **Implementation:** STATIC_ROOT is staticfiles/, and
  CompressedManifestStaticFilesStorage is configured. Render build runs
  `collectstatic --noinput`. CI also runs collection before tests.
- **References:** config/settings.py:168-178; render.yaml:7;
  .github/workflows/ci.yml:31-32.
- **Status:** Implemented. staticfiles/ in the source snapshot is generated
  and ignored by `.gitignore`; the CI/build should regenerate it rather than
  commit it.

### Full test discovery

- **Claim:** `python manage.py test` runs the full suite.
- **Implementation:** Both core/tests.py and
  core/test_migration_alignment.py are Django TestCase modules, so the Django
  default discovery should find 53 tests plus the PostgreSQL-only skip.
- **References:** docs/test-plan.md:54-66; .github/workflows/ci.yml:40-42;
  core/tests.py and core/test_migration_alignment.py.
- **Status:** Implemented. Local debug verification discovered 53 tests and
  skipped 1 PostgreSQL-only test.

### CI under non-debug and HTTPS

- **Claim:** CI runs with `DJANGO_DEBUG=false` and validates deployment checks
  plus the PostgreSQL suite.
- **Implementation:** CI sets non-debug, PostgreSQL, HTTPS hosts, and TLS
  disabled for the ephemeral local database. Settings set
  `SECURE_SSL_REDIRECT=true`, secure cookies, and forwarded-proxy SSL handling.
- **References:** .github/workflows/ci.yml:14-29 and 33-42;
  config/settings.py:185-192.
- **Status/verification:** CI configuration now sets
  `DJANGO_SECURE_SSL_REDIRECT=false` only in the ephemeral test environment,
  while retaining non-debug, PostgreSQL, proxy-SSL, secure-cookie, and HSTS
  settings. No workflow has run and PostgreSQL tests could not run locally
  without a server. The override prevents HTTP test-client redirects so the
  suite can exercise application behavior; production Render leaves the
  redirect enabled by default.

### Free Render configuration

- **Claim:** A single Free web service and Free Postgres database run in Oregon,
  collect static files, migrate at startup, and use Gunicorn.
- **Implementation:** render.yaml uses `plan: free` for both resources,
  `collectstatic`, startup `migrate --noinput`, Gunicorn, a generated secret,
  PostgreSQL URL, and `/healthz/`.
- **References:** docs/deployment.md:1-31; render.yaml:1-38;
  config/settings.py:80-105 and 185-192.
- **Status:** Selected configuration exists. Live resources and deployment
  remain unverified. Free Render's `preDeployCommand` is correctly omitted.
  Repeated startup migrations are a source of operational risk but match the
  free-tier service capabilities.

## Historical milestone records

- `docs/progress.md` contains superseded paid-Render history and later
  free-tier/registration-history milestones. Its paid-Render section is
  explicitly marked superseded.
- `docs/test-results.md` contains a 2026-11-15 historical baseline that reports
  BR-08 as unimplemented. This is historical and contradicted by the later
  2026-11-17/current implementation; it is kept and labeled as history.
- `docs/progress.md` and `docs/test-results.md` should report actual command
  results and must not be used as evidence that PostgreSQL or live Render was
  verified.

## Recommended corrections

1. Corrected test-plan account-deletion wording from preservation to blocking.
2. Keep registration reset as undocumented/unimplemented until the policy is
   decided and a workflow is added.
3. Preserve the delegated staff-permission model; do not document correction
   as superuser-only.
4. Add or verify a test-only HTTPS/non-redirect setup before claiming that CI
   passes under `DJANGO_DEBUG=false`.
5. Do not claim CI, PostgreSQL, or Render success until an actual workflow,
   database, or deployment verifies it.
