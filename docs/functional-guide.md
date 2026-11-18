# Functional Guide

This guide describes the application as it is implemented now. Students can
browse level-matched courses, review and submit one final registration, and
return later to view it. Staff can manage courses and review students and
submitted registrations in admin.

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
  that can sign in to Django admin. Enter credentials interactively; do not
  store them in source code or documentation.

## 2. Users, staff status, superuser status, and permissions

**Status: Partial.** Django authentication and admin access checks are enabled;
there is no application user-management workflow for course or registration
records.

- **Purpose:** Distinguish ordinary student accounts from accounts allowed into
  Django admin and from accounts granted particular model actions.
- **Where / who:** Django users are managed through Django admin where the
  signed-in administrator has the required permissions. Students create their
  own account at `/accounts/signup/`. Only a staff user can enter `/admin/`.
- **Actions and fields:** Staff with the relevant model permissions can create
  and search/filter courses, view all student profiles (including profiles
  without registrations), and search students by name or username. The profile
  list and detail show the student's level, submission status and time, and
  selected courses. Registration records are view-only. The public signup form
  accepts username, full name, level, and password fields only; it does not
  accept or apply privilege fields.
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
| Active staff account | Home and login | No; a student profile is required | Yes, subject to model permissions | Per granted core-model permissions; registration corrections require `change_registration` |
| Active superuser | Home and login | No; a student profile is required | Yes; Django superuser permissions | Manage courses, review all students and submissions, and make audited registration corrections |

The application has no student/staff role model beyond Django's user flags and
the `StudentProfile` relationship. A user created with `createsuperuser` is
for administration, not student signup.

## 3. Groups and when to use them

**Status: Partial.** Django groups and permissions are installed, but the
application defines no custom groups or group-based business rules. Core-model
permissions now control access to course and student-review screens.

- **Purpose:** Bundle Django permissions for staff who need a consistent set of
  allowed admin actions.
- **Where / who:** In `/admin/`, use Django's Groups page if the current
  administrator has the appropriate `auth` permissions. A superuser can manage
  groups.
- **Actions and fields:** A group has a name and a set of Django permissions.
  Add users to the group to grant those permissions to them.
- **Restrictions and validation:** Groups do not grant staff status. A user
  still needs to be active and marked as staff to enter admin. Course,
  student-profile, and registration screens require their respective model
  permissions. Registration records are read-only, and student levels become
  read-only in admin after submission.
- **Distinction from student levels:** A **group** is an authorization
  mechanism. A **student level** is the student's academic level (100, 200,
  300, 400, or 500) stored on `StudentProfile`. Levels do not grant Django
  permissions and are not groups.
- **Prerequisites / next step:** An administrator with group-management
  permissions must create a group and assign the intended Django permissions.
  No custom role names are required by the current application.
- **Example:** A course-management group can bundle the course permissions
  staff need; assigning a student to a "Level 200" group is not how the
  current level field works.

## 4. Course creation and level assignment

**Status: Implemented in Django admin.**

- **Purpose:** Store the course code, title, and one academic level for student
  course selection.
- **Where / who:** Staff with course permissions use `/admin/`. Django admin
  exposes course creation and management in [core/admin.py](../core/admin.py).
- **Actions and fields:** The model fields are `code` (maximum 32 characters),
  `title` (maximum 200 characters), and `level` (100, 200, 300, 400, or 500).
- **Restrictions and validation:** Codes are trimmed, uppercased, and unique.
  The database restricts levels to the supported choices. A course referenced
  by a registration item cannot be deleted; a level change that would make an
  existing registration inconsistent is rejected by model validation in admin.
  Bulk actions are disabled.
- **Prerequisites / next step:** Students see courses matching their stored
  level on the dashboard at `/student/`.
- **Example:** An authorized administrator can create `CS101`, title it
  “Introduction to Computing”, and assign level 100.

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
  public signup. After signup or login, the dashboard displays eligible courses
  or the student's saved registration.
- **Example:** Sign up with username `avery`, a full name, level 200, and a
  password that passes validation; the dashboard then displays the name and
  level.

## 6. Course browsing and selection

**Status: Implemented.**

- **Purpose:** Let a student find courses assigned to their level and choose
  courses for registration. Students use `/student/`, where the server filters courses using the
  authenticated student's stored profile level.
- **Actions and fields:** Each available course is shown as a labelled
  checkbox with its code and title. Students may select one or more courses.
  An informative message appears when no courses are available for their level.
- **Restrictions and validation:** Browser-supplied student IDs and levels are
  not used. Submitted course IDs are validated against database records at the
  student's level.
- **Next step:** Select courses and choose **Review selected courses** before
  the final submission.
- **Example:** A level-200 student sees level-200 courses only; level-100 and
  other-level courses are not offered.

## 7. Final registration submission

**Status: Implemented.**

- **Purpose:** Persist a student's final course choices as one registration
  with one or more registration items.
- **Where / who:** Authenticated students submit at `/student/`.
- **Actions and fields:** Students review the selected courses, then explicitly
  confirm the final submission. The server creates a `Registration` and one
  `RegistrationItem` per selected course in one database transaction.
- **Restrictions and validation:** A one-to-one relationship allows at most
  one `Registration` per student. A database constraint prevents the same
  course appearing twice in one registration. The form rejects empty,
  malformed, nonexistent, duplicate, and wrong-level course IDs. The final transaction
  locks the student's profile and selected eligible course rows; the database's
  one-to-one constraint is the final safeguard against duplicate submissions.
  Repeated submissions redirect to the saved registration and do not edit it.
- **Finality:** The review page explains that submission is final. After
  submission, students cannot edit their choices.
- **Example:** A level-100 student selecting two level-100 courses creates one
  `Registration` with two items and receives a redirect to the saved view.

## 8. Student viewing of submitted courses

**Status: Implemented.**

- **Purpose:** Allow a student to confirm a saved final registration on a later
  visit.
- **Where / who:** Students view the saved registration on `/student/`.
- **Actions and fields:** The page shows all submitted course codes and titles,
  together with the submission timestamp.
- **Restrictions and validation:** The registration is looked up through the
  authenticated student's profile, not a browser-supplied ID. The persistent
  record remains available after logout and a later login.
- **Example:** After signing in again, a student returns to `/student/` and sees
  the same saved courses and submission time.

## 9. Admin review and correction of registrations

**Status: Implemented for review and audited course corrections.**

- **Purpose:** Let authorized staff manage courses and review all students and
  their submissions.
- **Where / who:** Staff sign in at `/admin/`. The admin site is Django's
  built-in site; [core/admin.py](../core/admin.py) registers courses, student
  profiles, and submitted registrations.
- **Actions and fields:** Staff with the relevant permissions can create and
  search/filter courses, search students by name or username, see all student
  profiles (including those without registrations), and inspect each
  submission's level, status, time, and selected courses. Staff with the
  `change_registration` permission can open the dedicated correction form.
- **Restrictions and validation:** Admin access requires an active staff user;
  individual Django model permissions control available actions. Bulk actions
  are disabled. Students with a submitted registration have a read-only level;
  ordinary registration add/change/delete pages remain unavailable. A
  correction requires at least one course at the student's current level and a
  non-empty reason; the server rechecks course eligibility and applies the
  replacement atomically. The original submission time is preserved.
- **Audit and history:** Each successful correction records the acting
  administrator, reason, timestamp, target, original submission time, and
  before/after course snapshots. Audit records are read-only in admin.
  Deleting a student account with a submitted registration is protected so
  account deletion cannot cascade away that registration or its items.
- **Prerequisites / next step:** Create an active staff/superuser account as
  described in section 1, then grant the least required model permissions to
  staff groups or accounts. Review corrections in the read-only Registration
  Audits screen.
- **Example:** An authorized administrator replaces a mistaken course with
  another course at the student's level and records why. The student continues
  to see the corrected course list, the original submission time remains
  unchanged, and the audit retains both course lists and the administrator.

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

- Payments, timetables, prerequisites, credit limits, email notifications,
  PDF exports, and multiple academic sessions.

## Test evidence

The [progress log](./progress.md) records the historical authentication and
admin test results as well as the latest registration-workflow validation.
The PostgreSQL concurrency test is included but requires a PostgreSQL test
database to execute; the local SQLite run skips it.

Tests in [core/tests.py](../core/tests.py) support the implemented behavior:

- `HomepageTests` checks the public homepage.
- `AuthenticationFlowTests` checks signup, password hashing and validation,
  duplicate usernames, ignored privilege fields, login, anonymous dashboard
  access, student denial from admin, dashboard profile isolation, CSRF, and
  POST-only logout.
- `RegistrationModelTests` checks persistence relationships, uniqueness,
  supported levels, course/profile consistency, and protection of registered
  courses and student registration history.
- `AdminWorkflowTests` verifies course creation/search/filtering, student
  review and search (including students without registrations), read-only
  registration pages, authorized corrections and their audit records,
  correction validation/rollback, permissions, and course/student deletion
  protections.
- `StudentRegistrationFlowTests` covers level-specific lists and empty states,
  review and successful multi-course submission, empty and tampered selections,
  repeated requests, transaction rollback, and ownership.
- `PostgreSQLConcurrentRegistrationTests` verifies competing submissions when
  run against PostgreSQL; it is skipped on SQLite.
