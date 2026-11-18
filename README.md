# Course Reg System

This project lets students register for courses available at their level and return later to view their selections. Administrators can create courses, assign them to levels, and see what each student registered for.

Built it with Django, using its authentication and admin tools to keep the application straightforward.

## What you can do

**Students**
- Create an account with a name, username, level, and password.
- Browse courses available for their level.
- Select courses, review their choices, and submit.
- Log back in to view their saved registration.

**Administrators**
- Create courses and assign them to student levels.
- View students, including those who have not registered.
- Review each student's submitted courses.
- Correct a registration when permitted, with a reason and a record of the changes.

Students cannot change their choices after final submission.

## Built with

- Python and Django
- HTML, CSS, and Django templates
- SQLite for local development
- PostgreSQL for the Render deployment

## Run the project locally

You will need Python 3.14 and Git. The commands below use Windows PowerShell.

### 1. Download the project and install dependencies

```powershell
git clone https://github.com/Thyceekay/course_reg.git
cd course_reg

py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. Set up the local environment

Run these commands in the same terminal:

```powershell
$env:DJANGO_SECRET_KEY = (& python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
$env:DATABASE_ENGINE = "sqlite"
```

These settings apply to the current terminal session. Repeat this step when opening a new terminal. The project does not automatically load `.env` files.

### 3. Prepare the database and start the application

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py runserver
```

Follow the prompts to choose your administrator credentials.

Open:
- Application: http://127.0.0.1:8000/
- Administration: http://127.0.0.1:8000/admin/

Local accounts and registrations remain in `db.sqlite3` when you stop the server.

## Run the tests

With the environment configured and static files collected, run:

```powershell
python manage.py test --verbosity 2
```

The tests cover account access, course eligibility, submissions, and admin corrections. They use a separate test database. The PostgreSQL concurrency test is skipped when running with SQLite.

## Project structure

| Location | What it contains |
|---|---|
| `config/` | Application settings and URL routes |
| `core/models.py` | Students, courses, registrations, and their relationships |
| `core/forms.py` | Signup and course-selection validation |
| `core/views.py` | Student pages and registration handling |
| `core/admin.py` | Course management and registration review |
| `core/templates/` | HTML pages |
| `core/static/` | Site styling |
| `core/migrations/` | Database changes |
| `docs/` | Setup, design, and deployment notes |
| `.github/workflows/` | Automated checks |
| `render.yaml` | Render deployment configuration |
