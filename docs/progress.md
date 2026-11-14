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
