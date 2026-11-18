# Requirements

## Stable requirement IDs
- FR-01: Admins can securely log in.
- FR-02: Admins can create courses with a unique code, title, and student level.
- FR-03: Admins can view all students, including those who have not registered.
- FR-04: Admins can view each student's submitted courses.
- FR-05: Students can create an account with a unique username, full name, level, and password.
- FR-06: Students can log in and log out.
- FR-07: Students can view only courses assigned to their level.
- FR-08: Students can select one or more courses and submit.
- FR-09: Students can view their saved registration after returning later.

- BR-01: Supported levels are 100, 200, 300, 400, and 500.
- BR-02: One level per course.
- BR-03: One registration cycle exists for the system.
- BR-04: One final registration per student.
- BR-05: At least one course must be selected.
- BR-06: Students cannot edit submitted registrations.
- BR-07: Student level is locked after submission.
- BR-08: Admin corrections must preserve registration consistency.
- BR-09: Public signup must never grant administrator permissions.
- BR-10: Registered courses must be protected from deletion or level changes.

- NFR-01: Use Python and a supported stable Django release.
- NFR-02: Use Django templates, HTML, CSS, and minimal vanilla JavaScript.
- NFR-03: Use SQLite for local development.
- NFR-04: Use PostgreSQL for deployment.
- NFR-05: Use Render for hosting.
- NFR-06: Use GitHub for source control and submission.
- NFR-07: Use Django's built-in authentication and admin interface.
- NFR-08: Do not introduce a separate frontend framework or REST API.

## Assumptions
- Each student belongs to exactly one level at signup and that level remains stable after registration is submitted.
- A registration is a single submission event with no draft editing after final submission.
- One course can be assigned to only one level, and all course filtering is based on that level.
- There is no concept of multiple academic sessions, timetables, or overlapping semesters in version one.
- Course selection is limited to the student's own level and does not consider prerequisite logic.
- There are no payment, email, or PDF export workflows in scope.

## Out of Scope
- Payments
- Timetables
- Prerequisites
- Credit limits
- Email notifications
- PDF exports
- Multiple academic sessions
