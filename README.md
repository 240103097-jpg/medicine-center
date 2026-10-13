# Medicine Center

Django application for booking in-person medical appointments. Includes patient registration, email sign-in and POST-only sign-out, plus
the project, custom user model, Django admin and home page. Doctor profiles can be added and edited by authorized staff in Django admin,
and browsed publicly at `/doctors/`. Appointment workflows belong to subsequent issues.

## Local setup

Use **Python 3.13** (tested with 3.13.0) and Django 5.2 LTS. Run all commands
from the repository root. Use `python3` to create the environment where needed;
after activation, `python` refers to the environment interpreter.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate` instead.
Provide the required local secret before any Django command:

```sh
export DJANGO_SECRET_KEY="$(python -c 'from secrets import token_urlsafe; print(token_urlsafe(64))')"
```

This generates a private value without printing it. Keep it throughout a server
session. In a new terminal, activate and configure it again. Rotating the secret
invalidates login sessions but preserves saved accounts. Never commit secrets.
No `.env` loader is used. `DJANGO_DEBUG` defaults to `1`; this configuration is
for local development, not production deployment.

```sh
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

The custom user model is configured before the initial migration. SQLite data
is stored in ignored `db.sqlite3`. Dates are timezone-aware, the display timezone
is `Asia/Almaty` and the interface is English. Rerunning migrations is safe.

## Initial administrator and server

With the environment activated and secret configured, run:

```sh
python manage.py createsuperuser
python manage.py runserver
```

Enter the administrator's email and a strong private password at the prompts.
Password input is hidden and Django stores a hash. Open
<http://127.0.0.1:8000/> for the home page and
<http://127.0.0.1:8000/admin/> to sign in using the administrator email and
password. Anonymous visitors and ordinary users cannot access protected admin
pages. Stop with Ctrl+C and restart with the same server command; accounts
persist in the local database.

Run `python manage.py test` after changes. Tests cover the home page, email
uniqueness and authentication, password hashing, user permissions and admin
access. `.gitignore` excludes environments, local databases and secret files.

## Patient accounts

Use the home navigation to register with first name, last name, email and a
confirmed password. All four Django password validators apply. New email
addresses are trimmed and lowercase; login and duplicate checks ignore case.
Registration creates an ordinary patient and redirects to sign-in. Sign-in
returns home unless a safe same-host next destination is supplied. Sign-out
uses a CSRF-protected POST form and returns home.

## Doctors

A doctor requires a name and specialty (1–200 characters each) and a plain-text
description (1–5,000 characters). Surrounding whitespace is trimmed. Internal
spaces and description line breaks are preserved. Use the Doctors section in
Django admin to add or edit profiles. Staff need the corresponding add/change
permissions; view permission permits reading only. Public list and profile
pages are available without signing in.

## Appointment slots

Authorized staff can add/edit 30-minute slots in Django admin. Enter times in
Asia/Almaty; end times are derived. Starts must be in the future and same-doctor
intervals cannot overlap. Adjacent intervals are allowed. Doctor profiles show
future slots in Asia/Almaty. Booking is added by the next issue.

SQLite uses IMMEDIATE transactions to serialize slot validation and writes.
Tests use an ignored file-backed test database so concurrent connections exercise
SQLite writer locking. For isolated verification set `DJANGO_DATABASE_PATH` and
`DJANGO_TEST_DATABASE_PATH` to separate temporary SQLite paths.
