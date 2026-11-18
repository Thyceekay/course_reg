# Architecture

## Overview
This project uses Django as the main application framework. The system is structured around a small number of core concerns: authentication, course management, and student registration. The design favors Django's built-in model, form, view, template, authentication, and admin features so the project stays simple and consistent with the assignment requirements.

## Stack decisions
- Python with Django stable release
- SQLite for local development
- PostgreSQL for deployment
- Render for hosting
- GitHub for version control and submission
- Django templates, HTML, CSS, and vanilla JavaScript only

## Core domain model
- User: Django built-in User extended with full name and fixed student level; admin is a standard user with elevated permissions using Django auth groups or explicit admin checks.
- Course: unique code, title, and level. Each course belongs to one supported academic level.
- Registration: stores the relationship between a student and the final selected courses, plus submission status and timestamp.

## Suggested schema relationships
- User to Registration: one user can have zero or one final registration record; a registration belongs to exactly one student.
- Registration to Course: many-to-many relationship between the registration and course records for the selected courses.
- Course to Level: each course is assigned exactly one level value.

## Key constraints
- Course code must be unique.
- Student username must be unique.
- Supported levels: 100, 200, 300, 400, 500.
- Students can only see courses for their own level.
- A final registration must include at least one selected course.
- A student may have only one final registration record in the current cycle.
- Students cannot edit submitted registrations. Authorized staff can make
  reasoned, same-level corrections through the dedicated admin workflow, which
  preserves the submission time and records before/after snapshots.
- Student level is fixed after submission.
- Deleting a student account cannot cascade-delete its registration history.
- Registered courses cannot be deleted or have their level changed in a way that breaks submitted registrations.
- Public account creation must never create admin users.

## Permission model
- Anonymous users: can view public login/signup pages only.
- Students: can sign up, log in, log out, view level-specific courses, submit registration, and view their saved registration.
- Admins: can log in securely, create/update course data as needed, view all
  students and their final submitted registrations, and correct registrations
  with the required model permission.
- Server-side validation is mandatory for all permission checks and business rules; templates and client-side code must only support UX, not security.

## Security notes
- Use Django's authentication and permission system rather than custom session logic.
- Enforce access checks in views and model validation.
- Use form validation and model constraints to prevent invalid data before it reaches the database.
- Do not expose admin privileges via public signup.

## Deployment plan
- Local environment: SQLite for development and test stability.
- Production environment: PostgreSQL on Render.
- Keep deployment configuration environment-based and separate from source code secrets.
- Store secrets in environment variables, never in repository files.
