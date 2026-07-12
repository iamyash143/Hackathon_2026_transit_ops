# Phase 4 — Dashboard, Reports, and Exports

## Objective
Provide real-time operational visibility, interactive data visualization, and comprehensive financial reports to support decision-making for Fleet Managers and Financial Analysts. This phase exposes all key performance indicators (KPIs) on a unified dashboard, offers search and filter-driven reports, and enables high-fidelity CSV/PDF exporting of platform data.

## Features Included
- **Dashboard & KPIs**: Centralized landing page displaying real-time metrics (Active Vehicles, Available Vehicles, Vehicles in Maintenance, Active Trips, Pending Trips, Drivers On Duty, and Fleet Utilization %).
- **Reports & Analytics**: Advanced reports showing fuel efficiency, operational costs, and ROI per vehicle using query-time ORM aggregation.
- **CSV & PDF Exporting**: Export functionalities for both tabular reports (CSV) and trip manifests (PDF).

## Dependencies
- **Phase 1 (Foundation)**: Custom User model, Base UI with Tailwind and Flowbite, and RBAC authentication system.
- **Phase 2 (Core Modules)**: Models and CRUD interfaces for `fleet`, `drivers`, `trips`, `maintenance`, and `finance`.
- **Phase 3 (Business Logic)**: Finite State Machine transitions, RBAC enforcement decorators, and core cost calculation utility functions in `reports/metrics.py`.

## Deliverables
- `docs/phase-4/README.md` (This file)
- `docs/phase-4/DASHBOARD.md` (Dashboard view, KPI cards, and Chart.js integration)
- `docs/phase-4/REPORTS.md` (Searchable, filterable, and sortable reports tables with ROI metrics)
- `docs/phase-4/EXPORTS.md` (CSV export endpoints and WeasyPrint PDF layout generation)

## Success Criteria
- Dashboard loads in < 500ms and displays real-time KPI statistics.
- Financial charts render dynamically using HTMX-driven filters without refreshing the full page.
- Fleet Manager can view fleet utilization and vehicle ROI metrics instantly.
- CSV exports contain exact matches of the filtered tables.
- PDF exports produce structured, printable trip manifests.

## Merge Target
`main` (or `develop`) after approval of all deliverables and successful validation of the automated test suite.
