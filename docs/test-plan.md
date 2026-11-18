# Test Plan

## Purpose
This plan verifies the assignment requirements, business rules, and permission boundaries for the Course Registration System. Tests should focus on server-side correctness because the assignment explicitly requires business rules and permissions to be enforced on the server.

## Requirement coverage
- FR-01 to FR-09: authentication, course access, and registration flows
- BR-01 to BR-10: level validation, single-registration rules, immutability, and admin protections
- NFR-01 to NFR-08: stack, deployment, and architecture constraints

## Suggested test categories
### 1. Authentication and access tests
- Admin login succeeds for valid credentials and fails for invalid credentials.
- Student signup creates a normal student account only.
- Public signup never creates an administrator account.
- Students cannot access admin-only screens.
- Unauthenticated users are redirected away from protected pages.

### 2. Course management tests
- Admin can create a valid course with unique code, title, and level.
- Course code uniqueness is enforced.
- Course level must be one of the supported levels.
- Courses are shown only according to their assigned level.

### 3. Registration flow tests
- Student sees only courses matching their level.
- Available courses have labelled code/title checkboxes, and students see an
  informative empty state when their level has no courses.
- Students review selected courses and the finality warning before confirming.
- Student cannot submit an empty selection.
- Student can select multiple valid courses and submit successfully.
- Malformed, nonexistent, duplicate, and wrong-level course IDs are rejected.
- A second or concurrent submission attempt cannot create another registration.
- A failed item insert rolls back the registration and all earlier items.
- Student cannot edit a submitted registration.
- Only the authenticated student's saved registration is displayed after
  returning or logging in again.

### 4. Lockdown and consistency tests
- Student level is locked after submission.
- Admin corrections require the correction permission, a non-empty
  same-level course selection, and a reason; they preserve the original
  submission time and record before/after snapshots.
- Failed corrections roll back course changes and audit writes.
- Deleting a registered student's account is blocked in the model and Django
  admin so the registration and its course items are not removed.
- Registered courses cannot be deleted.
- Registered courses cannot be changed to an invalid or conflicting level.

### 5. Reporting and admin review tests
- Admin can view all students including those with no registration.
- Admin can view each submitted registration and its courses.

## Test execution
Use Django's test runner for automated server-side tests:
- python manage.py test

The concurrency test is PostgreSQL-only. To verify it, configure the local
environment to use PostgreSQL and run:

```powershell
python manage.py test core.tests.PostgreSQLConcurrentRegistrationTests
```

The test uses two independent clients submitting at the same time and asserts
that exactly one registration and its item are persisted.

Also perform manual UI smoke checks for the standard flows:
- admin login
- course creation
- student signup
- student registration submission
- student return visit to view saved registration

## Acceptance criteria
- All required routes and screens work for the expected user types.
- Permission checks are enforced on the server.
- Business rules prevent invalid states and maintain data consistency.
- Test failures indicate real product issues, not intentionally weakened assertions.
- No secrets are stored or printed in logs, terminal output, or documentation.

## Risks and limitations
- Automated tests should not be weakened to satisfy edge cases.
- UI-only validation is not enough; server-side checks are required.
- Without a browser automation tool, visual verification is limited to manual checks.
