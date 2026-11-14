# Functional Guide

This guide describes the application as it is implemented now. A model in the
database is not necessarily a usable screen: course and registration workflows
are not available yet.

## Status key

- **Implemented**: an application page or command is available.
- **Partial**: some supporting Django feature or data model exists, but the
  complete workflow is not available.
- **Planned**: no user-facing implementation exists.

## 1. Initial setup and superuser creation

**Status: Implemented (local setup and Django superuser command).**

- **Purpose:** Install and start the application, create its initial database,
  and create an administrator account.
- **Project instructions:** The local setup follows the project's
  [README](../README.md).
- **Where / who:** Run these commands in Windows PowerShell from the project
  folder. A developer with Python 3.14 and the project files can do this.
- **Actions and fields:** Create the virtual environment, install dependencies,
  set development-only environment variables, migrate, create a superuser, and
  start the server:

  ```powershell
  py -3.14 -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install -r requirements.txt

  $env:DJANGO_SECRET_KEY = (& python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
  $env:DJANGO_DEBUG = "True"
  $env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost"
  $env:DATABASE_ENGINE = "sqlite"

  python manage.py check
  python manage.py migrate
  python manage.py createsuperuser
  python manage.py runserver
  ```

- **Restrictions and validation:** The settings require `DJANGO_SECRET_KEY`.
  Debug mode defaults to local hosts, while non-debug mode requires explicitly
  configured hosts and PostgreSQL settings. SQLite is allowed only with debug
  mode enabled. These environment values last only for the current PowerShell
  session. `createsuperuser` is Django's interactive command; enter credentials
  locally and do not put them in documentation or source control.
- **Prerequisites / next step:** Install the dependencies and apply migrations
  before creating the superuser. Visit `http://127.0.0.1:8000/admin/` after the
  server starts.
- **Example:** Run `python manage.py createsuperuser` to make the first account
  that can sign in to Django admin.

## 2. Users, staff status, superuser status, and permissions

**Status: Partial.** Django authentication and admin access checks are enabled;
there is no application user-management workflow for course or registration
records.

- **Purpose:** Distinguish ordinary student accounts from accounts allowed into
  Django admin and from accounts granted particular model actions.
- **Where / who:** Django users are managed through Django admin where the
  signed-in administrator has the required permissions. Students create their
  own account at `/accounts/signup/`. Only a staff user can enter `/admin/`.
- **Actions and fields:** Django's built-in user has `is_active`, `is_staff`,
  `is_superuser`, direct `user_permissions`, and group memberships. The public
  signup form accepts username, full name, level, and password fields only; it
  does not accept or apply privilege fields.
- **Restrictions and validation:** Django admin requires an active staff user.
  Staff status opens the admin site but does not itself grant every model
  action; the user also needs the relevant `view`, `add`, `change`, or `delete`
  permission. A superuser has all permissions under Django's default auth
  backend. Public student signup creates a normal account, not a staff user or
  superuser.
- **How permissions combine:** A user's direct permissions and permissions
  inherited from all of the user's groups are combined as grants. A permission
  granted by either route is effective; Django has no matching "deny" grant.
  Superuser status bypasses individual permission checks, while the admin's
  active/staff check still applies.
- **Prerequisites / next step:** Create a superuser using the command in
  section 1. A staff account must be active and have the relevant model
  permissions to manage any model exposed in admin.
- **Example:** A non-staff student may sign in to `/student/`, but visiting
  `/admin/` sends them to Django's admin login instead of granting admin access.

### Role-permission matrix

| Account type | Public pages | Student dashboard | Django admin | Course/registration management |
|---|---|---|---|---|
| Anonymous visitor | Home, signup, login | No; login required | No | Not available |
| Student account | Home, login, logout | Own profile only | No | Not available |
| Active staff account | Home and login | No; a student profile is required | Yes, subject to model permissions | Not available for core models |
| Active superuser | Home and login | No; a student profile is required | Yes; Django superuser permissions | Not available for core models |

The application has no student/staff role model beyond Django's user flags and
the `StudentProfile` relationship. A user created with `createsuperuser` is
for administration, not student signup.

## 3. Groups and when to use them

**Status: Partial.** Django groups and permissions are installed, but the
application defines no custom groups or group-based business rules.

- **Purpose:** Bundle Django permissions for staff who need a consistent set of
  allowed admin actions.
- **Where / who:** In `/admin/`, use Django's Groups page if the current
  administrator has the appropriate `auth` permissions. A superuser can manage
  groups.
- **Actions and fields:** A group has a name and a set of Django permissions.
  Add users to the group to grant those permissions to them.
- **Restrictions and validation:** Groups do not grant staff status. A user
  still needs to be active and marked as staff to enter admin. Core course,
  profile, and registration models are not registered in admin, so group
  permissions do not currently create course or registration screens.
- **Distinction from student levels:** A **group** is an authorization
  mechanism. A **student level** is the student's academic level (100, 200,
  300, 400, or 500) stored on `StudentProfile`. Levels do not grant Django
  permissions and are not groups.
- **Prerequisites / next step:** An administrator with group-management
  permissions must create a group and assign the intended Django permissions.
  No custom role names are required by the current application.
- **Example:** A future course-management group could bundle course permissions
  once course administration is implemented; assigning a student to a
  "Level 200" group is not how the current level field works.

## 4. Course creation and level assignment

**Status: Partial.** The `Course` model and validation exist; there is no
course form, view, URL, or admin registration.

- **Purpose:** Store the course code, title, and one academic level for a future
  student course list.
- **Where / who:** No user-facing page or admin screen exists.
  [core/admin.py](../core/admin.py) does not register `Course`. A developer can
  inspect or manipulate model data in Django's shell, but that is not an
  implemented staff workflow.
- **Actions and fields:** The model fields are `code` (maximum 32 characters),
  `title` (maximum 200 characters), and `level` (100, 200, 300, 400, or 500).
- **Restrictions and validation:** Codes are trimmed, uppercased, and unique.
  The database restricts levels to the supported choices. A course referenced
  by a registration item cannot be deleted; a level change that would make an
  existing registration inconsistent is rejected by model validation.
- **Prerequisites / next step:** Course data must exist before students can
  browse or select courses, but the course creation workflow must be
  implemented first.
- **Example (not currently available):** A future administrator could create
  `CS101`, title it “Introduction to Computing”, and assign level 100.

## 5. Student signup, login, and profile

**Status: Implemented.**

- **Purpose:** Let a student create a normal account, authenticate, and view
  their own basic profile.
- **Where / who:** Public signup is `/accounts/signup/`; student login is
  `/accounts/login/`; the protected profile page is `/student/`. The public
  homepage links to signup and login.
- **Actions and fields:** Signup requires a unique username, full name, student
  level, password, and password confirmation. Django's configured password
  validators apply. The full name is stored in the built-in user's `first_name`
  field. Successful signup atomically creates the user and a one-to-one
  `StudentProfile`, signs the student in, and redirects to the dashboard. Login
  uses Django authentication and sessions.
- **Restrictions and validation:** Levels are limited to 100, 200, 300, 400,
  and 500. Invalid or duplicate usernames and invalid passwords show form
  errors. Signup does not expose staff, superuser, group, or permission fields.
  A user without a student profile cannot view `/student/`. Model validation
  prevents changing a student's level after a `Registration` exists.
- **Prerequisites / next step:** No administrator approval is required for
  public signup. After signup or login, the current next step is the profile
  dashboard; course browsing has not been implemented.
- **Example:** Sign up with username `avery`, a full name, level 200, and a
  password that passes validation; the dashboard then displays the name and
  level.

## 6. Course browsing and selection

**Status: Planned.** Course data exists in the model, but course browsing and
selection do not exist.

- **Purpose:** Let a student find courses assigned to their level and choose
  courses for registration.
- **Where / who:** There is no course-list URL, page, or selection form.
  Students cannot currently browse courses in the application.
- **Actions and fields:** No course selection fields or actions are available.
  `Course` stores code, title, and level; the student's level is stored on
  `StudentProfile`.
- **Restrictions and validation:** The model supports only levels 100, 200,
  300, 400, and 500. The model alone does not filter a web page; a future view
  must filter to the signed-in student's level on the server.
- **Prerequisites / next step:** Course records and a level-filtered student
  view are needed before registration submission can be used.
- **Example (planned):** A level-200 student should eventually see only
  level-200 courses; that page is not available yet.

## 7. Final registration submission

**Status: Partial.** Registration models and important consistency constraints
exist; no submission form or workflow exists.

- **Purpose:** Persist a student's final course choices as one registration
  with one or more registration items.
- **Where / who:** No student submission URL or form exists.
- **Actions and fields:** `Registration` links one `StudentProfile` to a
  submission timestamp. Each `RegistrationItem` links that registration to one
  `Course`. One registration can therefore contain multiple items.
- **Restrictions and validation:** A one-to-one relationship allows at most
  one `Registration` per student. A database constraint prevents the same
  course appearing twice in one registration, and model validation checks that
  each course level matches the student's level. The database does not require
  a registration to have any items; the missing submission workflow must
  enforce at least one selected course and save the registration and items
  atomically.
- **Prerequisites / next step:** Course browsing and selection are required.
  The future submit action must validate the selection server-side and reject a
  second registration.
- **Example (planned):** A level-100 student selecting two level-100 courses
  would eventually create one `Registration` and two `RegistrationItem` rows.

## 8. Student viewing of submitted courses

**Status: Planned.** Registration data can be represented in the models, but
students have no page to review it.

- **Purpose:** Allow a student to confirm a saved final registration on a later
  visit.
- **Where / who:** No saved-registration URL or template exists. The current
  `/student/` page displays only the student's name and level.
- **Actions and fields:** There is no action to list submitted courses or
  retrieve registration history through the application.
- **Restrictions and validation:** A future view must use the authenticated
  student's profile when retrieving registration data; it must not trust a
  student ID supplied by the browser. The current dashboard already resolves
  its profile from the signed-in user.
- **Prerequisites / next step:** A final registration must first be implemented
  and saved.
- **Example (planned):** After a successful submission, a student should
  eventually return to a page showing the courses in that registration.

## 9. Admin review of students and registrations

**Status: Partial.** Django admin authentication is available, but student,
course, and registration review screens are not.

- **Purpose:** Intended for authorized staff to manage courses and review all
  students and their submissions.
- **Where / who:** Staff sign in at `/admin/`. The admin site is Django's
  built-in site, but [core/admin.py](../core/admin.py) currently registers no
  application models.
- **Actions and fields:** Django's built-in user and group administration may
  be available to staff with the corresponding permissions. There is no
  application screen for course creation, listing all `StudentProfile`
  records, opening a student's registration, or correcting a registration.
- **Restrictions and validation:** Admin access requires an active staff user;
  individual Django model permissions control available admin actions.
  Course/registration consistency protections are present in model save paths,
  but there is no application admin workflow to perform corrections.
- **Prerequisites / next step:** Create an active staff/superuser account as
  described in section 1. The core model admin registrations and review views
  remain to be implemented.
- **Example:** A student visiting `/admin/` is denied entry; an authorized
  staff member can reach Django admin but cannot yet review course
  registrations there.

## 10. Logout and access restrictions

**Status: Implemented for current pages.**

- **Purpose:** End the session safely and keep student pages private.
- **Where / who:** Logout is `/accounts/logout/`; logout buttons appear on the
  homepage for signed-in users and on the student dashboard. The dashboard is
  `/student/`.
- **Actions and fields:** Logout is a POST request and the forms include CSRF
  tokens. Anonymous visits to the dashboard redirect to login. The dashboard
  gets the profile from the current authenticated user, not from a URL-supplied
  student ID.
- **Restrictions and validation:** A GET request cannot log out. Django's CSRF
  middleware protects form submissions. A student account cannot enter
  `/admin/`; an authenticated account without a student profile receives
  permission denied at `/student/`.
- **Prerequisites / next step:** Sign in before opening the student dashboard.
  Use the admin login at `/admin/` for an active staff account.
- **Example:** Select **Log out** on the dashboard; the POST ends the session
  and returns to the homepage.

## Intentionally unavailable actions

The following actions are not currently available through the application:

- Creating, editing, or managing courses through a staff screen.
- Browsing level-specific courses or selecting courses as a student.
- Submitting, editing, or viewing a final registration.
- Viewing all students or reviewing/correcting their registrations in admin.
- Payments, timetables, prerequisites, credit limits, email notifications,
  PDF exports, and multiple academic sessions.

## Test evidence

The [progress log](./progress.md) records that the authentication milestone's
`manage.py test` run passed 25 tests and that
`python manage.py makemigrations --check --dry-run` reported no changes. This
guide change did not run tests.

Tests in [core/tests.py](../core/tests.py) support the implemented behavior:

- `HomepageTests` checks the public homepage.
- `AuthenticationFlowTests` checks signup, password hashing and validation,
  duplicate usernames, ignored privilege fields, login, anonymous dashboard
  access, student denial from admin, dashboard profile isolation, CSRF, and
  POST-only logout.
- `RegistrationModelTests` checks persistence relationships, uniqueness,
  supported levels, course/profile consistency, and protection of registered
  data. These are model tests; they do not prove that course or registration
  screens exist.
