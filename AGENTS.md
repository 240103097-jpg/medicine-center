# Agent Instructions

## Project
Medicine Center is a Django web application for booking
in-person medical appointments.

Read these documents before planning or implementation:
- _docs/plan.md
- _docs/architecture.md
- _docs/process.md

## Backlog
- GitHub Issues are the only active backlog.
- _docs/tasks.md is retained as the initial planning record.
- Work on one issue at a time, respecting dependencies.
- Read acceptance criteria before implementation and closure.

## Roles
Follow the document for your assigned role:
- PM: _docs/team/pm.md
- Engineer: _docs/team/software-engineer.md
- QA: _docs/team/qa-engineer.md

Use _docs/task-template.md when refining an issue.

## Development Commands
The bootstrap task must establish and verify these commands:
- python -m pip install -r requirements.txt
- python manage.py migrate
- python manage.py check
- python manage.py test
- python manage.py runserver
- python manage.py createsuperuser

Run commands from the repository root with the virtual
environment activated. On systems where needed, use python3
instead of python.

## Rules
- Follow the agreed specification and architecture.
- Keep the interface in English.
- Use Asia/Almaty for displayed appointment times.
- Enforce permissions and booking rules on the server.
- Never commit secrets, virtual environments or local databases.
- Commit meaningful changes and reference the relevant issue.
- Do not use automatic issue-closing keywords before QA PASS.
- Never claim tests passed unless they were actually run.
- Record implementation and QA evidence in the issue.
- Engineers do not close issues.
- QA reports findings without modifying application code.
- The orchestrator closes an issue only after QA PASS.
