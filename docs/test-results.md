# Release Candidate Test Results

## Latest free deployment preparation and history fixes

**Run date:** 2026-11-17
**Environment:** Python 3.14.10, Django 5.2.19, SQLite test database

- The focused registration-model and admin regression suites passed 24 tests.
  The full suite passed 52 of 53 tests; the PostgreSQL-only concurrency test
  was skipped on SQLite.
- `manage.py check`, `makemigrations --check --dry-run`, Python compilation,
  `pip check`, `git diff --check`, and Render/CI YAML validation passed.
- `manage.py check --deploy` completed with two expected HSTS warnings:
  `security.W005` and `security.W021`. Static collection succeeded, and a
  production-mode HTTPS test-client request received HTTP 200 for a
  WhiteNoise-served stylesheet.
- Regression coverage now verifies authorized corrections, same-level and
  non-empty course validation, required reason, before/after audit snapshots,
  original submission-time preservation, correction rollback, and protection
  of registered student history from direct and admin account deletion.
- The Free Render Blueprint uses supported Free plans and runs migrations
  before Gunicorn at startup. Its YAML and documented commands were checked
  locally, but no Render resource or deployment was created.
- GitHub Actions now collects static files, runs Django and migration checks,
  targets the PostgreSQL concurrency test explicitly, and runs the full suite
  against its PostgreSQL service. The latest inspected run failed during
  teardown of the dedicated concurrency test; details and the worker-connection
  fix are recorded below.
- `.env`, `.venv`, and `db.sqlite3` are ignored and not Git-tracked. No tracked
  secret/credential filenames or common private-key, access-token, and
  credentialed-PostgreSQL-URL patterns were found. There is no configured Git
  remote; nothing was staged, committed, or pushed.

**Still unverified:** the GitHub workflow has not passed after the worker
connection fix. The dedicated PostgreSQL concurrency test passed before the
fix but its test-database teardown failed; the full PostgreSQL suite was skipped
by workflow sequencing. No live Render database, TLS/HTTPS behavior, Free-tier
service behavior, or live superuser creation was tested. No dependency
vulnerability scan was run. `pip check` is not a vulnerability scan. The
historical BR-08 and deployment findings below describe the earlier 2026-11-15
snapshot and are superseded by the current status above.

## PostgreSQL concurrency connection cleanup

- Inspected the complete GitHub Actions run log. Django checks and migration
  consistency completed. The dedicated PostgreSQL concurrency test passed
  (`Ran 1 test`, `OK`), then Django failed to drop its test database because
  two worker-thread database sessions remained open. The subsequent full-suite
  step was skipped; no earlier failing step or test assertion failure was
  present. `check --deploy` emitted W005/W008/W021 warnings but exited
  successfully; W008 follows from CI's HTTPS-redirect override.
- The database URL configures persistent connections with `CONN_MAX_AGE=600`.
  The worker's `close_old_connections()` call in `finally` does not close
  healthy persistent connections. The test now calls thread-local
  `connections.close_all()` in `finally`, including request/assertion failure
  paths.
- Local PostgreSQL was unavailable (no local server/client/container runtime;
  port 5432 refused connections). PostgreSQL verification is therefore not
  claimed. The GitHub workflow must verify the fix after pushing.
- After the fix, the local SQLite full suite discovered 53 tests: 52 passed
  and the PostgreSQL-only concurrency test was skipped.

## GitHub publication preparation (2026-11-18)

- Added a documentation-versus-source audit at
  `docs/documentation-code-audit.md`.
- Added concise module, class/function, template, and configuration comments
  where they explain purpose or non-obvious permissions and validation.
- Corrected test-plan account-deletion wording: deletion of a registered
  student is blocked, not implemented as preservation by a reset workflow.
- The full local debug SQLite suite discovered 53 tests, passed 52, and skipped
  one PostgreSQL-only concurrency test.
- Migration consistency, Django system checks, static collection,
  dependency checks, YAML parsing, and `git diff --check` passed.
- A non-debug SQLite test attempt was rejected by the settings as intended;
  SQLite is not a supported production/test configuration outside debug mode.
- A direct test-client check under non-debug settings returned HTTP 301 until
  CI's test-only `DJANGO_SECURE_SSL_REDIRECT=false` override was added.
  No PostgreSQL server or live GitHub workflow was available for verification.

## Historical release-candidate baseline (2026-11-15)

**Environment:** Python 3.14.10, Django 5.2.19, SQLite test database

## Summary

The SQLite release-candidate checks passed. The full Django suite found 45
tests: 44 passed and the PostgreSQL-only concurrency test was skipped because
no PostgreSQL server is available locally.

An admin login redirect defect was found and fixed: an admin signing in without
a `next` URL was sent to the student dashboard and received a 403. The default
login redirect now goes to Django admin, while the student login explicitly
continues to go to the student dashboard.

This is not a complete release sign-off. PostgreSQL concurrency behavior and
dependency vulnerability status remain unverified, and BR-08 is not
implemented as written: the application has no staff correction workflow.

## What ran

| Check | Result |
|---|---|
| `manage.py check` | Passed; no system-check issues. |
| `manage.py test --verbosity 2` | Passed: 45 discovered, 44 passed, 1 PostgreSQL-only test skipped. |
| `manage.py makemigrations --check --dry-run` | Passed; no model changes require migrations. |
| `manage.py migrate --check` | Passed; no unapplied migrations. |
| `manage.py showmigrations --plan` | All listed migrations applied in the local SQLite database. |
| `python -m compileall -q config core` | Passed. |
| `python -m pip check` | Passed; no broken requirements. This is not a vulnerability scan. |
| `git diff --check` | Passed. |
| Focused regression tests | Passed: admin login/student redirect behavior and CSRF enforcement for registration submission and admin course creation. |
| Browser end-to-end smoke checks | Passed using the integrated Playwright browser and a temporary isolated SQLite database with synthetic data. Admin login, course creation, and student-registration inspection worked. A student signed up, reviewed and submitted two courses, logged out/in, and saw the saved registration. A query targeting another student's profile did not reveal that student's name or course. The temporary database was removed. |

No persistent Playwright test suite was added. The project has no Playwright
package/runtime or JavaScript test manifest; adding and maintaining a separate
browser-test toolchain was not practical for this run. The browser journeys
above were exercised interactively and are not a repeatable repository test.

## What did not run

- **PostgreSQL-backed tests:** `psycopg` is installed, but no PostgreSQL service
  or `psql`/`postgres` executable is available, no local server is listening
  on port 5432, and no PostgreSQL connection variables are configured. The
  test runner used SQLite and skipped
  `PostgreSQLConcurrentRegistrationTests.test_concurrent_submissions_create_one_registration_and_item`.
- **Dependency vulnerability scan:** `pip-audit` is not installed. `pip check`
  only verifies dependency consistency and does not check published
  vulnerabilities. No other local vulnerability scanner was available.
- **Render deployment:** no deployment was attempted. The repository has no
  `render.yaml` or `Procfile`; Render is documented as the hosting target, not
  verified by a deployment.
- **GitHub submission:** this worktree has no configured Git remote. Local Git
  status and changes were inspected; no push or submission was attempted.
- **Automated Playwright suite:** no checked-in browser suite was run; only the
  interactive browser scenarios above were executed.

## Remaining defects and verification gates

1. **BR-08 / staff corrections:** no staff workflow exists for correcting a
   submitted registration. Admin registration records are read-only, and the
   `RegistrationAudit` schema is not a correction workflow. Consequently,
   correction consistency cannot be tested and BR-08 remains unmet as written.
   Existing project documentation calls corrections out of scope; that scope
   conflicts with the requirement and must be resolved before claiming full
   requirement completion.
2. **PostgreSQL concurrency:** run the skipped test against an isolated
   PostgreSQL test database before release sign-off.
3. **Vulnerability status:** run an approved dependency vulnerability scanner
   when one is available.
4. **Repeatable browser automation:** add a checked-in Playwright suite and its
   test-only dependency/setup if browser automation is required in CI.
5. **Hosting/source submission:** validate Render configuration and GitHub
   submission when those release activities are authorized.

## Requirement coverage

| ID | Existing automated test or manual check | RC status |
|---|---|---|
| FR-01 | `AuthenticationFlowTests.test_admin_login_accepts_staff_credentials_and_rejects_invalid_password`; interactive Playwright admin login | Covered; redirect defect fixed. |
| FR-02 | `AdminWorkflowTests.test_admin_can_create_search_and_filter_courses_without_bulk_actions`; `RegistrationModelTests.test_duplicate_course_code_is_rejected_by_database`; Playwright course creation | Covered. |
| FR-03 | `AdminWorkflowTests.test_admin_lists_registered_and_unregistered_students_and_searches_them`; Playwright admin student list | Covered. |
| FR-04 | `AdminWorkflowTests.test_admin_lists_registered_and_unregistered_students_and_searches_them`; `AdminWorkflowTests.test_submitted_registration_is_read_only_in_admin`; Playwright registration inspection | Covered. |
| FR-05 | `AuthenticationFlowTests.test_signup_creates_profile_hashes_password_and_signs_student_in`, plus invalid and duplicate signup tests; Playwright signup | Covered. |
| FR-06 | `AuthenticationFlowTests.test_valid_credentials_log_student_in`, `test_incorrect_password_does_not_authenticate`, and `test_logout_requires_post_and_ends_the_session` | Covered. |
| FR-07 | `StudentRegistrationFlowTests.test_dashboard_lists_only_student_level_courses_with_labelled_checkboxes` and `test_nonexistent_malformed_and_wrong_level_ids_are_rejected` | Covered. |
| FR-08 | `StudentRegistrationFlowTests.test_valid_submission_is_reviewed_saved_once_and_survives_relogin`, `test_empty_selection_is_rejected`, and invalid/duplicate selection tests; Playwright multi-course submission | Covered. |
| FR-09 | `StudentRegistrationFlowTests.test_valid_submission_is_reviewed_saved_once_and_survives_relogin`; Playwright logout/login return visit | Covered. |
| BR-01 | `RegistrationModelTests.test_course_level_must_be_supported_by_database` and `test_student_level_must_be_supported_by_database`; signup level choices were inspected in the browser | Covered for valid UI choices and rejected unsupported values. |
| BR-02 | `RegistrationModelTests.test_registration_item_rejects_course_at_another_level` and `test_registered_course_level_cannot_change_to_mismatch_student` | Covered. |
| BR-03 | `RegistrationModelTests.test_student_can_have_only_one_registration`; schema inspection confirms one registration record per student and no academic-session model. The one-cycle rule is an explicit system assumption. | Covered by current single-cycle design. |
| BR-04 | `RegistrationModelTests.test_student_can_have_only_one_registration`; submission/repeat-request coverage in `StudentRegistrationFlowTests.test_valid_submission_is_reviewed_saved_once_and_survives_relogin` | Covered. |
| BR-05 | `StudentRegistrationFlowTests.test_empty_selection_is_rejected`; `CourseSelectionErrorAccessibilityTests.test_empty_selection_error_is_associated_with_checkbox_group` | Covered. |
| BR-06 | `StudentRegistrationFlowTests.test_valid_submission_is_reviewed_saved_once_and_survives_relogin`; `AdminWorkflowTests.test_submitted_registration_is_read_only_in_admin` | Covered. |
| BR-07 | `RegistrationModelTests.test_student_level_cannot_change_after_registration`; `AdminWorkflowTests.test_student_level_is_read_only_after_submission_even_on_tampered_post` | Covered. |
| BR-08 | `RegistrationAuditModelTests.test_migration_fields_persist` verifies audit data storage only. Admin inspection confirms registrations are read-only and no correction workflow exists. | **Not met:** correction behavior and consistency cannot be exercised. |
| BR-09 | `AuthenticationFlowTests.test_signup_ignores_submitted_privileged_fields` | Covered. |
| BR-10 | `RegistrationModelTests.test_registered_course_cannot_be_deleted`, `test_registered_course_level_cannot_change_to_mismatch_student`, and `AdminWorkflowTests.test_admin_cannot_delete_or_invalidate_a_registered_course` | Covered. |
| NFR-01 | `.venv` reports Python 3.14.10 and Django 5.2.19; `manage.py check` and the full test suite pass. | Verified locally. |
| NFR-02 | Source inspection and browser checks confirm Django templates, HTML, and CSS with no separate frontend framework. | Verified locally. |
| NFR-03 | SQLite is configured for debug/local use; all automated tests ran with an isolated SQLite test database. | Verified locally. |
| NFR-04 | PostgreSQL settings and `psycopg` are present; no PostgreSQL server was available for migration or test execution. | Configuration only; backend behavior unverified. |
| NFR-05 | Render is documented as the hosting target; no Render deployment/configuration file was found and no deployment was run. | Not runtime-verified. |
| NFR-06 | The workspace is a local Git repository; no remote is configured. | Local version control verified; GitHub submission unverified. |
| NFR-07 | Tests cover Django authentication, admin login, model permissions, and course/student administration. | Covered. |
| NFR-08 | Source inspection confirms there is no separate frontend framework or REST API. | Verified locally. |

## Next milestone

The next incomplete verification milestone in the progress log is running the
concurrent-registration test against PostgreSQL. Before full release
acceptance, also resolve the BR-08 scope conflict and complete the available
vulnerability, hosting, and submission checks.
