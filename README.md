# Course Registration System

A server-rendered Django application. The project foundation uses Django 5.2 LTS,
SQLite for local development, and PostgreSQL for production.

## Requirements

- Windows PowerShell
- Python 3.14.10 or a later Python 3.14 patch release
- Git

Install the supported Python runtime if needed:

```powershell
winget install --id Python.Python.3.14 --exact
```

## Local setup

Run these commands from the project folder in PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Generate a development key directly into the current shell environment.
$env:DJANGO_SECRET_KEY = (& python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
$env:DATABASE_ENGINE = "sqlite"

python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open <http://127.0.0.1:8000/> to view the starter homepage. Stop the development
server with `Ctrl+C`. The environment variables last only for the current
PowerShell session; generate a new local key when opening another session.

To create a local administrator, run `python manage.py createsuperuser` after
migrations and enter the account details interactively in PowerShell. Then sign
in at <http://127.0.0.1:8000/admin/>. Do not put administrator credentials in
source files or documentation.

## Check migrations and model tests

With the development environment activated and the local environment variables
set as shown above, run these commands from the project folder:

```powershell
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py check
python manage.py test core.tests
```

The migration check fails if model changes still need a migration. The model
tests exercise saved records and database constraints as well as model-level
registration rules.

Database constraints enforce unique course codes, supported profile/course
levels, one profile per user, one registration per student, and no duplicate
course within a registration. Course deletion is protected while referenced.
Course/student level compatibility and level changes that affect existing
registrations require application-level validation; the model save paths check
these rules, but bulk updates and raw SQL bypass model validation. A registration
must also contain at least one course, which cannot be expressed as a portable
row-level database constraint because its items are stored in a separate table.
The eventual submission flow must reject an empty selection and save the
registration and its items atomically.

Authorized staff can create, search, and filter courses and review all student
profiles, including those without registrations. They can inspect submission
status, time, and selected courses. Submitted registrations are read-only; a
course used in a registration cannot be deleted or assigned an incompatible
level.

If PowerShell blocks virtual-environment activation, use the environment's
Python directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Set the same environment variables in that PowerShell session before running
these commands.

## Production configuration

Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and PostgreSQL connection
variables in the hosting provider's environment configuration. Set
`DJANGO_DEBUG=False` and `DATABASE_ENGINE=postgresql`. The application refuses
to start without a secret key, valid production hosts, and a configured
PostgreSQL database; it has no production secret or SQLite fallback.
`.env.example` documents the required variable names and contains placeholders
only. It is not loaded automatically.

## Selected versions

- Python 3.14.10 (supported by Django 5.2.8 and later)
- Django 5.2.19 (LTS)
- psycopg 3.3.9 (PostgreSQL driver)

The version choices follow the official
[Django 5.2 release notes](https://docs.djangoproject.com/en/5.2/releases/5.2/).
