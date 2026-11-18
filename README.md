# Course Registration System

A server-rendered Django application for one final, level-specific course
registration per student.

## Implemented features

- Public signup and login/logout with Django authentication.
- Level-specific course review and one final multi-course registration.
- Read-only submitted registrations for students.
- Django admin course management and student/registration review.
- Delegated staff registration corrections through `core.change_registration`,
  with required reasons and read-only audit snapshots.
- Database and application validation that protect supported levels,
  duplicate submissions, registered courses, and submitted student levels.

## Technology

- Python 3.14 and Django 5.2 LTS
- Django templates, HTML, CSS, and minimal vanilla JavaScript
- SQLite for local development; PostgreSQL for deployment
- Gunicorn and WhiteNoise
- GitHub Actions and Render

## Folder map

- `config/`: Django settings, URL routing, and WSGI/ASGI entry points.
- `core/`: models, forms, views, admin, migrations, tests, templates, and CSS.
- `docs/`: requirements, architecture, functional guide, deployment, testing,
  and preparation records.
- `.github/workflows/`: PostgreSQL-backed GitHub Actions tests.
- `render.yaml`: selected Free Render web and PostgreSQL blueprint.

## How the application fits together

`config/urls.py` sends public, authentication, student, and admin requests to
`core/views.py` or Django admin. Views use Django forms in `core/forms.py` for
input validation. `core/models.py` enforces relationships and database rules.
Templates render the returned context, while `core/static/core/site.css`
provides shared styling. The database is SQLite locally and PostgreSQL in
production. Submitted registrations, items, correction audit records, and
student/course relationships are tested in `core/tests.py`.

## Essential local setup

Run from the project directory in Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

$env:DJANGO_SECRET_KEY = (& python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
$env:DATABASE_ENGINE = "sqlite"

python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The public routes are:

- `/accounts/signup/` and `/accounts/login/`
- `/accounts/logout/` using POST
- `/student/` for the authenticated student's dashboard
- `/admin/` for active staff users
- `/healthz/` for generic database readiness

The virtual environment and environment variables are local-only; `.env.example`
lists variable names but is not loaded automatically.

## Tests

Run the complete Django suite with:

```powershell
python manage.py test --verbosity 2
```

Tests use an isolated Django test database. The suite verifies authentication,
CSRF, level filtering, final submissions, locking, protected history, and
audited admin corrections. A PostgreSQL-only concurrent-submission test is
skipped when the configured test database is SQLite.

## Known limitations

- Registration reset is not implemented.
- Student account deletion is blocked when registration history exists.
- PostgreSQL concurrency, live CI, and live Render behavior remain unverified
  until their respective services run.
- Free Render resources have no managed backups and an assessment database
  expires; see the deployment guide.
- No separate frontend framework or REST API is used.
- A final registration cannot be changed through the student interface.

## Detailed documentation

- [Local development](docs/local-development.md)
- [Functional guide](docs/functional-guide.md)
- [Requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Test plan](docs/test-plan.md)
- [Test results](docs/test-results.md)
- [Documentation/code audit](docs/documentation-code-audit.md)
- [Render deployment](docs/deployment.md)
