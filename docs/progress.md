# Progress Log

## Accepted plan and assumptions
- The project will use Django with server-side validation, SQLite for development, and PostgreSQL for deployment.
- Course and registration logic is constrained to one level, one registration cycle, and one final student registration.
- Public signup is limited to student accounts and must never create admin privileges.
- No payment, timetable, or prerequisite logic is included in version one.

## Milestone reporting format
For each implementation milestone, record:
1. What changed and why.
2. Tests and commands actually run.
3. Failures, limitations, or blocked checks.
4. How to verify the feature.
5. The next milestone.

## Current status
- Foundation milestone completed.
- Read `Course.md` and the architecture, requirements, progress, and test-plan documents before implementation.
- Inspected the environment: Windows 10, PowerShell 7.7.0 Core, Python 3.15.2 initially installed, and Git 2.53.0.windows.1. Python 3.15 is not supported by the selected Django release.
- Selected Python 3.14.10, Django 5.2.19 LTS, and psycopg 3.3.9. Django's official 5.2 release notes confirm support for Python 3.14 starting with Django 5.2.8. The selected versions are also recorded in `README.md`.
- Added an isolated virtual environment, pinned application dependencies, environment-based settings, SQLite development configuration, PostgreSQL production configuration, and a minimal Django homepage.
- Added `.gitignore`, a placeholder-only `.env.example`, and Windows PowerShell setup instructions in `README.md`.
- Initialized Git because the workspace was not a repository at the start of this milestone.
- Validation completed: `manage.py check` passed; `manage.py migrate --noinput` applied Django's initial built-in migrations; `manage.py test` passed the homepage test; `pip check` reported no broken requirements; the local development server returned HTTP 200 for the homepage.
- Production configuration checks confirmed that startup is rejected when the secret key or PostgreSQL settings are missing, or when SQLite is selected outside debug mode.
- Limitations: PostgreSQL configuration was validated without connecting to a running PostgreSQL server. No application registration features are included in this foundation milestone.
- Scope: foundation only; no registration features have been implemented.

## Database design and migrations milestone
- Added `StudentProfile` as a one-to-one extension of Django's configured user model, with the supported 100/200/300/400/500 levels.
- Added `Course` with a unique, normalized course code, title, and supported level; `Registration` with one-to-one student ownership and a submitted timestamp; and `RegistrationItem` joining registrations to courses.
- Added database constraints for supported levels, unique course codes, one registration per student, and one occurrence of each course per registration. Course deletion uses `PROTECT`.
- Added model validation to prevent course/student level mismatches, prevent student-level changes after registration, and reject course-level changes that would invalidate existing registrations.
- Added persistence tests covering relationships, uniqueness constraints, level checks, normalization, course deletion protection, and registration consistency.
- Validation completed with the project virtual environment (Python 3.14.10, Django 5.2.19): `manage.py migrate --noinput` applied `core.0001_initial`; `manage.py check` passed with no issues; `manage.py test core.tests` passed all 12 tests; `manage.py makemigrations --check --dry-run` reported no changes. These commands were run with the local `.venv` Python executable.
- Application-level limitations: a database row constraint cannot verify that an item course matches the related registration student's level, nor can it prevent a level update based on related rows. The model save paths validate these rules, but bulk updates or raw SQL can bypass them. A non-empty registration also spans registration and item rows; the submission workflow must enforce at least one selected course and save both atomically.
- Remaining validation: the migration and model tests ran against SQLite; PostgreSQL constraint and migration behavior has not been exercised against a running PostgreSQL server.
- Scope: database design and migrations only; the student registration submission workflow remains unimplemented.
- Next milestone: implement application flows using these models and keep submission validation inside a transaction.

## Authentication and permissions milestone
- Implemented student signup with Django's `UserCreationForm`, configured password validators, unique usernames, password confirmation, supported-level validation, and one full-name field.
- Signup stores the full name on Django's built-in user and atomically creates the user and `StudentProfile`. The form only accepts student account fields; submitted staff, superuser, group, and permission values are ignored.
- Added session-backed login, POST-only logout with CSRF protection, and an authenticated student dashboard that resolves the profile only from the current user. Anonymous dashboard visits go to login; users without a student profile are denied.
- Kept administrative authentication on Django's built-in admin, which requires an active staff account. Added accessible labels and inline validation errors to signup and login forms, with CSRF tokens on state-changing forms.
- Verified the pre-existing baseline before changes: `manage.py test core.tests` passed all 12 model/homepage tests.
- Added 13 authentication tests covering successful signup and login, password hashing, invalid and weak passwords, duplicate usernames, privilege-field injection, empty submissions, anonymous access, student-to-admin denial, student data isolation, POST-only logout, and CSRF enforcement.
- Final validation: `manage.py test` passed all 25 tests; `manage.py makemigrations --check --dry-run` reported no changes; Django's test runner reported no system-check issues; Pylance found no syntax errors in the changed Python files.
- Test settings were temporary process environment values only. The existing `.env` configuration and `db.sqlite3` were not altered; the database file retained its original size and modification time after testing.
- Manual browser verification has not been performed. Course browsing and registration routes do not exist yet; the current student page accesses only the signed-in student's profile, and future record views must continue enforcing ownership.
- Manual verification checklist:
  1. Visit `/accounts/signup/`, create a student account, and confirm the student dashboard shows the submitted name and level.
  2. Sign out, visit `/accounts/login/`, and verify correct credentials log in while an incorrect password displays an error.
  3. Try a duplicate username, unsupported level, mismatched passwords, and a weak password; confirm each shows a validation error and creates no account.
  4. Submit signup fields such as `is_staff`, `is_superuser`, `groups`, or `user_permissions`; confirm the account remains a normal student.
  5. Open `/student/` in a signed-out browser and confirm login is required; sign in as one student and confirm only that student's profile is shown.
  6. Visit `/admin/` as a student and confirm Django does not grant admin access. Verify logout submits a POST form and returns to the homepage.
- Scope: authentication and permissions only; course browsing and registration submission are still unimplemented.
- Next milestone: implement level-specific course browsing and atomic final course registration, enforcing the one-registration and non-empty-selection rules.

## Functional guide documentation milestone
- Created `docs/functional-guide.md` after inspecting the project instructions, requirements, settings, models, forms, views, URLs, admin configuration, templates, and tests.
- Documented setup and superuser creation, Django user/staff/superuser permissions, groups versus student levels, and the implemented signup/login/dashboard/logout workflow.
- Marked course creation, browsing, registration submission and viewing, and admin review according to their current implementation status; documented existing model constraints separately from missing user-facing workflows.
- Reviewed the guide and progress diff for unintended content and
  credential-like values; a targeted scan found no matches, and
  `git diff --check` passed. This documentation-only milestone ran no
  application tests; the guide reports the previously recorded 25-test
  authentication result as historical evidence, not as a new run.
- Remaining work: no course management or student course/registration workflow is available; `Registration` can be empty in the database model, and there are no admin screens for core models.
- Next milestone: implement level-specific course browsing and atomic final registration submission, with server-side ownership and validation.

## Django admin management and review milestone
- Registered `Course`, `StudentProfile`, and `Registration` in Django admin. Course screens support create, search by code/title, and level filtering; student screens show all profiles with name, username, level, submission status/time, and selected courses, and support name/username search.
- Kept registration add/change/delete unavailable and disabled bulk actions. Student levels are read-only after a registration exists. Course deletion remains protected by `PROTECT`, and the existing model validation rejects course-level changes that would invalidate registrations, including through admin forms.
- Documented local interactive superuser creation in `README.md` and the functional guide. Documented a future correction workflow requiring authorization, preservation of the original submission, validation, and an audit trail; no correction path or credentials were added.
- Added six `AdminWorkflowTests` covering course creation/search/filtering, students with and without registrations, permission boundaries, submitted registration immutability, student-level locking, and course deletion/level-change protections. An initial search test exposed overlapping fixture usernames; the test data was made unambiguous and the targeted suite then passed.
- Validation completed: `manage.py test core.tests.AdminWorkflowTests` passed all 6 tests; `manage.py test` passed all 31 tests; `manage.py check` reported no issues; `manage.py makemigrations --check --dry-run` reported no changes; `git diff --check` passed. Local test settings were process-only values; no admin credentials were recorded.
- Manual browser verification was not performed. PostgreSQL behavior was not retested; verification used the configured local SQLite test database.
- Scope: Django admin only. The next incomplete milestone remains student-level course browsing and atomic final registration submission, with server-side ownership and validation.

## Student registration journey milestone
- Implemented the student dashboard course list, filtering courses by the signed-in student's stored level and showing labelled course-code/title checkboxes or an informative empty state.
- Added a server-rendered review step and finality warning, followed by a no-JavaScript POST submission. Student identity and level come from the authenticated user/profile, never from submitted fields.
- The form rejects empty, duplicate, malformed, nonexistent, and wrong-level course IDs. Final submission revalidates eligible course rows inside one transaction, locks the student and selected courses, creates the registration and items atomically, and relies on the existing one-registration database constraint as a final duplicate safeguard. Database integrity failures are handled without exposing database details; successful and repeated POSTs redirect.
- The dashboard displays the saved courses and submission timestamp, derives ownership from the active session, and shows the persistent record after later login. Submitted registrations cannot be edited by students.
- Added eight `StudentRegistrationFlowTests` for eligibility/display, the empty state, multi-course review and submit, empty/tampered/duplicate selections, repeat requests, rollback after an item insert failure, and ownership. Added a PostgreSQL-only concurrent submission test.
- Validation completed: focused registration tests passed all 8 tests; the full `manage.py test` run passed 39 tests with the PostgreSQL-only concurrency test skipped on SQLite (40 tests discovered); `manage.py check` passed; `manage.py makemigrations --check --dry-run` reported no changes; Pylance found no syntax errors in the changed Python files; `git diff --check` passed.
- PostgreSQL concurrency was not executed: the local test database is SQLite and `psql`/`postgres` commands are unavailable. The PostgreSQL-specific test is ready to run against a configured PostgreSQL test database. Manual browser verification was not performed.
- Scope: the student registration journey is implemented. The next incomplete verification milestone is running the concurrency test against PostgreSQL; an audited staff correction workflow remains intentionally out of scope.

## Interface review and accessibility milestone
- Replaced the standalone public, login, signup, and dashboard markup with a shared server-rendered layout and a local stylesheet. Added consistent navigation, typography, spacing, form controls, buttons, responsive panels, success feedback, and a titled empty state without changing business rules or adding JavaScript or UI dependencies.
- Added a skip link, visible keyboard focus, responsive course selection, long-text wrapping, and field-level errors. Course-selection errors are associated with the checkbox fieldset through `aria-describedby` and `aria-invalid`.
- Verified the rendered site with the integrated browser, including home, signup/login, course list, review, submitted registration, empty state, and Django admin. Checked 360px, 768px, and desktop viewport widths; public pages had no horizontal document overflow. At 360px, the admin student-results table remained usable in its horizontally scrollable results region. Keyboard focus reached the skip link with a visible outline. Labels and error associations were checked in the rendered pages.
- Calculated text/focus contrast for the primary interface color pairs; all checked ratios exceeded WCAG AA text contrast thresholds. Browser checks confirmed the local stylesheet returned HTTP 200.
- Validation completed: `manage.py test` passed 41 of 42 tests, with the PostgreSQL-only concurrency test skipped on SQLite; the focused migration-alignment and empty-selection accessibility tests passed; `manage.py makemigrations --check --dry-run` reported no changes; `manage.py migrate --check` found no unapplied migrations; and `manage.py showmigrations --plan` showed all migrations applied. `manage.py check` and `git diff --check` also passed.
- Aligned `core/models.py` with the existing `core.0002_registration_corrected_at_registrationaudit` migration by adding `Registration.corrected_at` and `RegistrationAudit`. The audit schema is not exposed as a correction workflow; student submissions remain immutable and staff corrections remain out of scope.
- Added a persistence test for audit actions and before/after course snapshots. The local SQLite database already recorded migrations `core.0001_initial` and `core.0002_registration_corrected_at_registrationaudit`; no applied migration was rewritten.
- Next incomplete verification milestone: run the concurrent-registration test against PostgreSQL. The audited staff correction workflow remains intentionally unavailable.

## Release-candidate verification milestone
- Reviewed the project instructions, requirements, test plan, progress history, implementation, current Git status, and recent commits. Preserved pre-existing worktree edits.
- Ran the baseline suite before changes: 42 tests discovered, 41 passed, and the PostgreSQL-only concurrency test skipped on SQLite.
- Added regression coverage for staff login, student registration CSRF enforcement, and CSRF-protected admin course creation. The new admin login test exposed a redirect defect: a valid admin logging in without a `next` URL was sent to the student dashboard and denied. Set the default login redirect to the admin index and explicitly retained the student dashboard redirect for student login.
- Final validation: the full `manage.py test --verbosity 2` run passed 44 tests and skipped the one PostgreSQL concurrency test (45 discovered); `manage.py check` passed; `makemigrations --check --dry-run` found no changes; `migrate --check` found no unapplied migrations; `showmigrations --plan` showed all migrations applied; `compileall`, `pip check`, and `git diff --check` passed.
- Used an integrated Playwright browser against a separate temporary SQLite database seeded only with synthetic records. Admin login/course creation/student review, student signup/multi-course review/submission, logout/login return, and cross-student query isolation all passed. The temporary database was removed. No checked-in Playwright suite was added because the project has no Playwright runtime or test manifest.
- Limitations: PostgreSQL binaries/service/port and connection settings were unavailable, so the concurrency test did not run on PostgreSQL. `pip-audit` is not installed; `pip check` is not a vulnerability scan. No Render deployment was attempted, and this worktree has no configured Git remote.
- Requirement review recorded in `docs/test-results.md`: BR-08 remains unmet as written because staff registration corrections are unavailable, despite the project documentation describing that workflow as out of scope. The audit model persistence test does not verify correction consistency.
- Next incomplete verification milestone: run the concurrent-registration test against PostgreSQL and resolve the BR-08 scope conflict before claiming full requirement completion.

## Release review milestone
- Reviewed the requirements, architecture, test plan/results, README, implementation, worktree diff, and recent Git history. Preserved existing unstaged and untracked work; made no application-code changes during this review.
- Reviewed changed and untracked project files for unintended changes and credentials. No apparent real secrets were found: `.env.example` contains placeholders, `.env` is ignored and absent, and password-like strings in `core/tests.py` are synthetic test fixtures.
- Actual checks run: `manage.py test --verbosity 2` passed 44 of 45 tests; the PostgreSQL-only concurrency test was skipped on SQLite. `manage.py check`, `makemigrations --check --dry-run`, `migrate --check`, `compileall`, `pip check`, and `git diff --check` passed. A read-only Django shell check confirmed the default auth User is registered in admin and has a deletion route.
- Confirmed release gaps: BR-08 staff corrections are not implemented; deleting a student User through the default admin cascades to the profile, registration, and registration items. Suspected, not reproduced: model-level level validation may race with concurrent registration on PostgreSQL. The prior interactive browser checks are recorded in `docs/test-results.md`; they were not repeated during this review.
- Remaining verification: PostgreSQL concurrency and migration behavior, Render deployment/HTTPS/static-file behavior, and dependency vulnerability scanning were not verified. `pip check` does not scan for vulnerabilities.
- Next step: resolve BR-08 or formally change scope, prevent student account deletion from erasing registration history, and verify concurrent submissions and admin edits against PostgreSQL before release sign-off.

## Initial Render deployment preparation milestone (superseded)
- Reviewed the current official Render Django, Blueprint, Python runtime, health check, Postgres connection, free-plan, and backup guidance, together with the Django 5.2 deployment checklist and static-files guidance. Chose a paid single-instance web service and paid Basic-1gb Postgres database: Render's free Postgres expires after 30 days and does not provide production recovery features. The Blueprint was added locally only; no resources were provisioned or deployed.
- Added Gunicorn, `dj-database-url`, and WhiteNoise. Production settings accept Render's PostgreSQL connection URL, require PostgreSQL outside debug mode, use secure proxy/HTTPS and cookie settings, derive the Render hostname and CSRF origin from `RENDER_EXTERNAL_HOSTNAME`, collect manifest-hashed static files, and log warnings/errors without Gunicorn access logs.
- Added a database-aware `/healthz/` response that returns only a generic status, with tests for healthy and unavailable database cases.
- Added `render.yaml` with build, paid pre-deploy migration, startup, generated secret, health-check, CI-gated auto-deploy, and Postgres configuration. Added a GitHub Actions workflow for Django/deployment checks, migration consistency, and tests using a PostgreSQL service. No project formatter or linter had been adopted, so none was added to CI.
- Documented the Render commands and environment, interactive initial superuser creation, persistent database and backup considerations, and application/database rollback limitations in `docs/deployment.md`; linked it from `README.md`.
- Validation run before editing: `manage.py test --verbosity 1` found 45 tests; 44 passed and the PostgreSQL-only concurrency test was skipped on SQLite.
- Validation after changes: `manage.py check` passed; `manage.py test --verbosity 2` found 47 tests, with 46 passing and the PostgreSQL-only concurrency test skipped on SQLite; `makemigrations --check --dry-run`, `compileall`, `pip check`, and `git diff --check` passed. Pylance found no syntax errors in the changed Python files. Both YAML files parsed and their deployment/CI structure was checked.
- Production settings were checked with temporary dummy secret/database values. `manage.py check --deploy` completed with two Django warnings (`security.W005` and `security.W021`) because HSTS subdomain and preload directives remain disabled until all subdomains are known HTTPS-only. `collectstatic --noinput` completed, and a production-mode test client retrieved the collected stylesheet through WhiteNoise with HTTP 200.
- Not verified: the GitHub workflow has not run because no Git remote is configured; PostgreSQL-backed CI/concurrency, a live Render deployment, and actual Render HTTPS/database behavior remain unverified. No CI pass or deployment is claimed.
- Next incomplete verification milestone: run the configured test workflow against PostgreSQL on GitHub and verify its concurrency test. Before release sign-off, also resolve the existing BR-08 staff-correction gap and the previously recorded student-deletion/history concern.

## Free Render assessment and registration history milestone
- Rechecked the current official Render Free-plan and Blueprint documentation, Render Postgres connection guidance, and Django 5.2 deployment checklist. Render confirms that Free Postgres has a 1 GB limit, expires after 30 days with a further 14-day upgrade grace period before deletion, and has no backups. Free web services spin down, use ephemeral filesystems, provide no shell or one-off jobs, and cannot scale beyond one instance. Render's Blueprint specification limits `preDeployCommand` to paid web/private/worker services.
- Superseded the paid deployment plan with `plan: free` for both Blueprint resources, removed the unsupported pre-deploy field, and moved `migrate --noinput` before Gunicorn in the start command. Updated deployment guidance for repeated startup migrations, Free-tier limitations, data/export and rollback risks, environment names, and a temporary local PowerShell superuser workflow using an external PostgreSQL URL with `DATABASE_SSL_REQUIRE=true`.
- Updated GitHub Actions to collect manifest static files before admin tests and to run the PostgreSQL concurrency test explicitly, as well as Django checks, migration consistency, and the full PostgreSQL-backed suite. No formatter or linter is configured in the project.
- Implemented the BR-08 correction workflow in `core/admin.py` with registration-change permission, read-only standard admin fields, a required reason and at least one same-level course, transactionally replaced items, preserved `submitted_at`, `corrected_at`, and before/after/actor audit details. Added validation, permission, audit, timestamp, and rollback regression tests.
- Changed `Registration.student` to `PROTECT` and generated `core.0003_protect_registration_history.py`, so user deletion cannot cascade away a registered student's history. Added model- and Django-admin deletion regression tests. The migration was applied only to isolated test databases; no migration was run against the existing local database.
- Updated the functional guide, architecture, test plan, deployment guide, README, test-results, and this progress log. Validated Render and CI YAML using PyYAML; `makemigrations --check --dry-run`, `manage.py check`, `compileall`, `pip check`, and `git diff --check` passed. `manage.py check --deploy` passed with the expected `security.W005` and `security.W021` HSTS warnings; production static collection and an HTTPS WhiteNoise static-file smoke test returned HTTP 200.
- Local test results: the targeted model/admin regression suites passed 24 tests. The full SQLite suite found 53 tests: 52 passed and the PostgreSQL concurrency test was skipped because SQLite is not PostgreSQL.
- Verified `.env`, `.venv`, and `db.sqlite3` are ignored and not Git-tracked; found no tracked secret/credential filenames or common private-key, access-token, and credentialed-PostgreSQL-URL patterns. No Git remote is configured. No files were staged or committed; no GitHub workflow run, PostgreSQL-backed run, Render resource, live connection, deployment, or push occurred.
- Remaining verification: run the PostgreSQL concurrency and complete CI workflow on GitHub after the user supplies the destination repository; verify any actual Render assessment deployment and external superuser setup only when authorized. A dependency vulnerability scan also remains unrun. No CI pass or deployment is claimed.

## GitHub publication preparation milestone
- Compared the Markdown documentation against the current source, migrations,
  settings, templates, tests, CI workflow, and Render blueprint.
- Added docs/documentation-code-audit.md as the current discrepancies record.
  It distinguishes superseded paid-Render and historical BR-08 milestones from
  current implementation.
- Confirmed the source currently delegates registration corrections through
  Django's `core.change_registration` permission; this is not superuser-only.
- Confirmed registration reset has no implementation. Account deletion of a
  registered student is blocked by `PROTECT` and admin permissions, rather than
  preserved by a custom deletion workflow.
- Added concise module and key model/form/view/admin/test documentation.
- Corrected the test-plan deletion description to match the blocking behavior.
- Verification: the debug SQLite suite discovered 53 tests, passed 52, and
  skipped one PostgreSQL-only concurrency test. Migration consistency,
  dependency consistency, and diff checks passed. A CI-like non-debug SQLite
  run is not supported by settings and was rejected because SQLite is
  intentionally prohibited outside debug mode.

## Documentation and local publication preparation milestone
- Reorganized the root README into a concise project overview and moved the
  detailed Windows/PowerShell setup workflow to `docs/local-development.md`.
- Verified `DJANGO_SECURE_SSL_REDIRECT` in settings: without the override,
  non-debug production mode resolves it to true; the GitHub Actions workflow
  sets it to false only for its PostgreSQL test job.
- Reviewed the worktree for accidentally staged or untracked databases,
  virtual environments, caches, static output, real environment files, private
  keys, and credentialed URLs. Generated and local-only paths remain excluded.
- Remaining verification requires a GitHub PostgreSQL workflow run and an
  authorized live Render deployment; neither was performed.

## PostgreSQL concurrency worker cleanup
- Inspected the complete GitHub Actions run log for the dedicated PostgreSQL
  concurrency step. Django checks and migration checks completed, the
  concurrency test itself reported `Ran 1 test` / `OK`, and failure occurred
  during Django test-database teardown when `DROP DATABASE` found two remaining
  worker sessions. The full-suite CI step was skipped after that failure.
  `check --deploy` emitted W005/W008/W021 warnings but exited successfully;
  W008 is caused by CI's HTTPS-redirect override.
- `DATABASE_URL` configures `CONN_MAX_AGE=600`; the worker's old
  `close_old_connections()` call in `finally` could retain those healthy
  persistent connections. Replaced it with thread-local
  `connections.close_all()` in the worker's `finally` block, and close
  pre-existing worker connections before issuing the request.
- Local PostgreSQL verification was not run: no PostgreSQL client/server or
  container runtime was available and localhost:5432 was not accepting
  connections. After the fix, the SQLite full suite discovered 53 tests: 52
  passed and the PostgreSQL-only concurrency test was skipped.
- GitHub Actions must rerun the isolated PostgreSQL concurrency test and full
  suite after this commit is pushed. No push or deployment was performed.
