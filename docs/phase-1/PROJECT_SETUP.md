# Project Setup

## Goal

Initialize the Django project with the correct structure, database, settings split, and seed data so every developer starts from an identical baseline.

## Scope

- Django project and app scaffolding
- Dependency installation (`requirements.txt`)
- PostgreSQL connection
- Settings split (`base` / `local` / `production`)
- `.env` configuration via `django-environ`
- Management command to seed RBAC groups and a superuser
- `requirements.txt` pinned for reproducibility

## Responsibilities

**Owner:** One developer (Phase 1 lead). Merge to `main` before any feature branch is cut.

## Django App

`core` — shared utilities, context processors, management commands.  
`accounts` — created here but detailed in `AUTHENTICATION.md`.

## Files to Create / Modify

```
transitops/                         # Django project root
├── settings/
│   ├── __init__.py
│   ├── base.py                     # All shared settings
│   ├── local.py                    # DEBUG=True, local DB overrides
│   └── production.py               # Production guards (stub only in Phase 1)
├── urls.py
├── wsgi.py
└── asgi.py

core/
├── __init__.py
├── apps.py
├── context_processors.py           # Injects user role into every template
└── management/
    └── commands/
        └── seed_groups.py          # Creates RBAC groups + permissions

.env.example
requirements.txt
manage.py
```

## Dependencies

No other phase. This is the root.

**Python packages (pin exact versions in `requirements.txt`):**

```
django>=5.1
psycopg2-binary
django-environ
django-fsm-2
django-crispy-forms
crispy-tailwind
django-anymail
django-import-export
twilio
weasyprint
django-admincharts
django-geojson
django-leaflet
requests
celery
redis
```

## Business Rules

- Use `DJANGO_SETTINGS_MODULE=transitops.settings.local` in `.env` for all local dev.
- `SECRET_KEY`, `DATABASE_URL`, and all API keys must come from `.env`, never hardcoded.
- `DEBUG` must default to `False`; local settings override it.

## Implementation Steps

### 1. Scaffold the project

```bash
django-admin startproject transitops .
python manage.py startapp accounts
python manage.py startapp core
```

### 2. Settings split

`transitops/settings/base.py` — move everything from the generated `settings.py` here. Add:

```python
import environ
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env()

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
DATABASES = {'default': env.db()}  # reads DATABASE_URL

INSTALLED_APPS = [
    # django built-ins ...
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # third-party
    'crispy_forms',
    'crispy_tailwind',
    'import_export',
    'django_fsm',
    'admincharts',
    'django_geojson',
    'django_leaflet',
    # local
    'accounts',
    'core',
    # feature apps added by other developers:
    # 'fleet', 'drivers', 'trips', 'maintenance', 'finance', 'reports'
]

AUTH_USER_MODEL = 'accounts.User'   # must be set before first migration

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
```

`transitops/settings/local.py`:

```python
from .base import *
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
```

### 3. `.env.example`

```
SECRET_KEY=change-me
DEBUG=True
DATABASE_URL=postgres://transitops:password@localhost:5432/transitops_db
OPENWEATHERMAP_API_KEY=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
ANYMAIL_SENDGRID_API_KEY=
```

### 4. PostgreSQL setup (local)

```bash
createdb transitops_db
createuser transitops -P
psql -c "GRANT ALL PRIVILEGES ON DATABASE transitops_db TO transitops;"
```

### 5. Seed management command

`core/management/commands/seed_groups.py`:

```python
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

ROLES = {
    'Fleet Manager': [],    # permissions wired in Phase 2 per model
    'Driver': [],
    'Safety Officer': [],
    'Financial Analyst': [],
}

class Command(BaseCommand):
    help = 'Create RBAC groups for TransitOps'

    def handle(self, *args, **kwargs):
        for role_name in ROLES:
            group, created = Group.objects.get_or_create(name=role_name)
            self.stdout.write(
                f"{'Created' if created else 'Already exists'}: {role_name}"
            )
```

Run: `python manage.py seed_groups`

Permissions per group are assigned in Phase 2 once models exist.

### 6. Core context processor

`core/context_processors.py` — injects the user's primary role name into every template as `{{ user_role }}`:

```python
def user_role(request):
    if request.user.is_authenticated:
        group = request.user.groups.first()
        return {'user_role': group.name if group else 'Admin'}
    return {'user_role': None}
```

Register in `base.py` under `TEMPLATES[0]['OPTIONS']['context_processors']`.

### 7. Run initial migrations

```bash
python manage.py makemigrations accounts
python manage.py makemigrations
python manage.py migrate
python manage.py seed_groups
python manage.py createsuperuser
```

## Success Scenario

```bash
git clone <repo>
cp .env.example .env          # fill in DB credentials
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_groups
python manage.py runserver
# → http://localhost:8000/login/ renders without errors
```

## Definition of Done

- [ ] `python manage.py migrate` is clean on a fresh PostgreSQL DB
- [ ] `seed_groups` creates exactly four groups: Fleet Manager, Driver, Safety Officer, Financial Analyst
- [ ] `AUTH_USER_MODEL = 'accounts.User'` is set before any migration
- [ ] No secrets in source code; all from `.env`
- [ ] `requirements.txt` is committed and all installs succeed via `pip install -r requirements.txt`
- [ ] `core` app is registered; context processor is wired

## AI Instructions

- `AUTH_USER_MODEL` must be set in `base.py` before generating any migration. If it is missing, migrations will use the default `auth.User` and cannot be changed later without destroying the database.
- Always read `DATABASE_URL` from env — never hardcode credentials.
- The `seed_groups` command must use `get_or_create` so it is idempotent and safe to re-run.
- Do not assign model-level permissions in this command — they are added in Phase 2 after models exist.
- The `core` app has no models. Its only jobs are context processors and management commands.
- Feature apps (`fleet`, `drivers`, `trips`, `maintenance`, `finance`, `reports`) are registered in `INSTALLED_APPS` as stubs with a comment; other developers add them when they create those apps.
