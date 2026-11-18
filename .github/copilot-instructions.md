# Copilot Instructions

## Project Working Instructions
- Read relevant project documents before making changes.
- Work on only the requested milestone.
- Inspect existing code before editing.
- Preserve unrelated changes.
- Prefer Django's built-in features over extra dependencies.
- Validate permissions and business rules on the server.
- Never store or print secrets.
- Never weaken a test merely to make it pass.
- Never claim a command or test ran unless it actually ran.
- Update progress after each milestone.
- Do not deploy, push, delete data, or rewrite Git history unless explicitly instructed.

## Stack
- Python with Django stable release
- Django templates, HTML, CSS, minimal vanilla JavaScript
- SQLite for local development
- PostgreSQL for deployment
- Render for hosting
- GitHub for source control and submission
- Django built-in auth and admin

## Key business rules
- Admin secure login
- Course creation with unique code, title, and student level
- View all students including unregistered ones
- View each student's submitted courses
- Student account with unique username, full name, level, password
- Login/logout, level-specific course view, multi-course submission
- One registration cycle, one final registration per student
- At least one course required
- Students cannot edit submitted registrations
- Student level locked after submission
- Admin corrections preserve registration consistency
- Public signup never grants administrator permissions
- Protect registered courses from deletion or level changes

## Constraints
- Supported levels: 100, 200, 300, 400, 500
- One level per course
- One final registration per student
- Student level locked after submission
- No separate frontend framework or REST API
- Out of scope: payments, timetables, prerequisites, credit limits, email notifications, PDF exports, multiple academic sessions
