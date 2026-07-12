# TransitOps

TransitOps is a Django-based smart transport operations platform built for the Odoo Hackathon 2026. It centralizes fleet assets, drivers, trips, maintenance, operational costs, compliance alerts, reporting, and document management.

## Features

- Email-based authentication with role-based access control
- Vehicle and driver registries with finite-state status workflows
- Trip planning, dispatch, completion, cancellation, and route-distance support
- Fuel, expense, maintenance, and operational-cost tracking
- Dashboard KPIs, reports, CSV/PDF exports, and notification commands
- Vehicle document uploads, dark-mode UI, and Tailwind CSS styling

## Technology

- Python 3.12+ and Django 6
- PostgreSQL for production; SQLite is suitable for local development and tests
- Tailwind CSS v4 and Flowbite
- django-fsm-2, django-crispy-forms, django-anymail, WeasyPrint, Celery, and Twilio integrations

## Quick start

### 1. Clone and configure

```bash
git clone <repository-url>
cd Hackathon_2026_transit_ops
cp .env.example .env
```

Update `.env` with a unique `SECRET_KEY` and a database URL. For a simple local SQLite setup, use:

```dotenv
SECRET_KEY=local-development-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
npm install
```

### 3. Prepare the database

```bash
python manage.py migrate
python manage.py seed_groups
python manage.py createsuperuser
```

`seed_groups` creates the four application roles: Fleet Manager, Driver, Safety Officer, and Financial Analyst.

### 4. Run the application

In one terminal, compile CSS while developing:

```bash
npm run dev
```

In another terminal:

```bash
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

## Common commands

```bash
# Run the full test suite
python manage.py test

# Run the trip workflow tests
python manage.py test trips

# Validate Django configuration
python manage.py check

# Build minified CSS for deployment
npm run build

# Run compliance and maintenance alert checks
python manage.py send_alerts
python manage.py send_compliance_alerts
```

## Project layout

```text
accounts/             Authentication and role-based access
core/                 Shared templates, context processors, and commands
dashboard/            KPI dashboard
documents/            Vehicle document management
drivers/              Driver registry and status workflow
finance/              Fuel, expense, and cost tracking
fleet/                Vehicle registry and status workflow
maintenance/          Maintenance records and automation
notifications/        Email/SMS notification services and commands
reports/              Reporting and exports
trips/                Trip lifecycle and dispatch workflow
transit_project/      Django settings, URL configuration, ASGI/WSGI
static/               Tailwind source and generated CSS
docs/                 Product, phase, architecture, and workflow documentation
```

## Documentation

Start with [the documentation index](docs/README.md). It links the product overview, data schema, team workflow, and phase-specific implementation notes.

## Environment variables

The required local variables are documented in [.env.example](.env.example). Optional integration variables include SendGrid, Twilio, and OpenWeatherMap credentials. Do not commit `.env` or production secrets.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, migration, test, and pull-request expectations.

## License

No license has been selected for this repository. All rights are reserved until the project owners add a license file.
