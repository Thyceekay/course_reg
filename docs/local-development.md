# Local development

This guide covers a clean Windows PowerShell setup. Detailed production
configuration is in [deployment.md](deployment.md).

## Requirements

- Windows PowerShell
- Python 3.14.10 or a later Python 3.14 patch release
- Git

Install Python if needed:

```powershell
winget install --id Python.Python.3.14 --exact
```

## Create and install the environment

Run these commands from the project directory:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell activation is blocked, invoke the virtual-environment Python
directly with `.\.venv\Scripts\python.exe`.

## Configure SQLite development settings

Set these variables in the current PowerShell session:

```powershell
$env:DJANGO_SECRET_KEY = (& python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
$env:DATABASE_ENGINE = "sqlite"
```

The settings require a secret key and do not load `.env` automatically.
Environment variables last only for the current terminal session.

## Migrate and create an administrator

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py runserver
```

Stop the server with `Ctrl+C`. Sign in to `http://127.0.0.1:8000/admin/`
using the interactive administrator account. Public signup creates normal
student accounts only and never grants staff or superuser status.

## Routes and behavior

- `/` displays the public homepage.
- `/accounts/signup/` creates a user and `StudentProfile`.
- `/accounts/login/` signs a student or staff user into Django sessions.
- `/accounts/logout/` requires POST and clears the session.
- `/student/` shows level-matched courses or the immutable saved registration.
- `/admin/` provides Django admin course, student, registration, and audit
  review pages.
- `/healthz/` performs a database read and returns a generic status.

## Tests and consistency checks

Run:

```powershell
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py check
python manage.py test --verbosity 2
python -m pip check
```

Django creates and destroys an isolated test database. PostgreSQL-only
concurrency tests are skipped on SQLite. Do not run tests against a production
database.

## Static files

Static assets are collected into `staticfiles/` for WhiteNoise:

```powershell
python manage.py collectstatic --noinput
```

`staticfiles/` is generated and must not be committed. `.gitignore` excludes
local databases, virtual environments, caches, and environment files.
