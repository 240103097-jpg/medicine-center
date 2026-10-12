# Technology Stack and Architecture

## Selected Stack
- Language: Python
- Web framework: Django
- Database: SQLite for local development and the assignment demo
- Frontend: Django templates, HTML and CSS
- Tests: Django's built-in test framework

## Rationale
Django provides authentication, database models, form validation
and an administration interface.

SQLite simplifies setup for a small demonstration application.
Django templates avoid maintaining a separate frontend application.

## Alternatives Considered
- FastAPI with React: requires more integration work for
  authentication, administration and the frontend.
- Spring Boot with Thymeleaf: suitable for Java development,
  but Python was selected for this project.

## Architecture
The browser sends requests to Django.
Django validates input, checks permissions and reads or writes
data in SQLite. It returns rendered HTML pages.

## Main Components
- Accounts: patient registration and email-based login.
- Doctors: doctor profiles and specialties.
- Scheduling: 30-minute appointment slots.
- Appointments: booking, cancellation and completion.
- Administration: Django admin for authorized staff.

## Key Constraints
- Use a custom user model with a unique email for login.
- Configure the user model before the first database migration.
- Use timezone-aware dates and Asia/Almaty for displayed times.
- Enforce booking and access rules on the server.
- Use database constraints and transactions to prevent
  duplicate active bookings.
- Preserve cancelled appointments as history.
- Do not commit secrets or the local database to GitHub.
