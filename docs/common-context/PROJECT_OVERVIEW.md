# PROJECT_OVERVIEW.md

## 1. Business Context

Many logistics and transport companies still run their operations on spreadsheets, paper logbooks, and disconnected communication channels (phone calls, WhatsApp, email). This produces a predictable set of failures:

- **Scheduling conflicts** — the same vehicle or driver gets double-booked because no system enforces availability.
- **Underutilized assets** — vehicles sit idle because no one has visibility into the whole fleet at once.
- **Missed maintenance** — vehicles run past safe service intervals because there is no systematic tracking of odometer or engine hours.
- **Regulatory non-compliance** — drivers are dispatched with expired licenses because no one checked the expiry date.
- **Opaque financials** — fuel costs, maintenance costs, tolls, and fines are scattered across receipts and spreadsheets, making profitability per vehicle nearly impossible to calculate.

**TransitOps** exists to replace this fragmented workflow with a single, centralized, rule-enforcing platform that digitizes the complete lifecycle of transport operations: vehicle registration, driver management, dispatching, maintenance, fuel/expense tracking, and reporting.

The platform's core value proposition is not just data storage — it is **programmatic enforcement of business rules** so that illegal operational states (e.g. dispatching a vehicle that's already on a trip, or assigning a driver with a suspended license) become impossible, not just discouraged.

## 2. Objective

Build an end-to-end transport operations platform that:

1. Digitizes vehicle, driver, dispatch, maintenance, and expense management.
2. Enforces mandatory business rules at the data/model layer, not just in the UI.
3. Provides real operational insight through a KPI dashboard and financial analytics.
4. Supports four distinct user roles, each with a different view of the system and a different permission set.

## 3. Target Users and Roles

TransitOps has exactly **four roles**. Every user in the system belongs to exactly one role (mapped to a Django Group). Role definitions are authoritative here and in `SHARED_CONSTANTS.md`; do not introduce new roles without updating both documents.

### 3.1 Fleet Manager
Oversees fleet assets, maintenance, vehicle lifecycle, and overall operational efficiency.
- Full CRUD on Vehicles, Maintenance Logs, and Reports.
- Read access to Trips.
- Primary consumer of the KPI Dashboard.

### 3.2 Driver
Executes assigned trips, creates trip logs, assigns vehicles, logs fuel consumption, and updates active delivery statuses.
- Read access to their own assigned Trips.
- Update access to Trip status and odometer readings.
- Create access for Fuel Logs and Expense Logs tied to their trips.

### 3.3 Safety Officer
Ensures driver compliance, tracks license validity, monitors safety scores, and issues disciplinary suspensions.
- Full CRUD on Driver records.
- Read access to Vehicles, Trips, and Compliance Reports.

### 3.4 Financial Analyst
Audits operational expenses, evaluates fuel consumption efficiency, tracks maintenance costs, and calculates fleet profitability (ROI).
- Read access to all operational data.
- Full access to Expense Logs, Fuel Logs, and Financial Analytics modules.

See `SHARED_CONSTANTS.md` for the exact CRUD-to-model permission matrix used to configure Django Groups.

## 4. Technology Stack Summary

| Layer | Technology | Rationale |
|---|---|---|
| Backend Framework | Django 5.x | Batteries-included: ORM, auth, admin, forms, migrations — maximizes velocity in a time-boxed build |
| Database | PostgreSQL | Strong relational integrity, native support for constraints and aggregation |
| Frontend Interactivity | HTMX | SPA-like UX without a separate JS frontend/API layer; keeps all logic in Python/Django templates |
| CSS Framework | Tailwind CSS v4 | Utility-first styling, native dark mode support |
| UI Components | Flowbite | Pre-built Tailwind-native components (tables, modals, nav, dashboards) |
| Form Rendering | django-crispy-forms + crispy-tailwind | Auto-generates Tailwind-styled forms from Django Form/ModelForm classes |
| Business Logic / State | django-fsm-2 | Enforces legal state transitions on Vehicle, Driver, and Trip at the model layer |
| Maps & Routing | Leaflet.js + Leaflet Routing Machine + OSRM | Visual route selection and automatic distance calculation |
| Weather Context | OpenWeatherMap API | Real-time weather at trip destination |
| Charts | Chart.js | Dashboard and financial analytics visualizations |
| CSV Export | django-import-export | Mandatory CSV export requirement |
| PDF Export | WeasyPrint | Converts existing Tailwind HTML templates directly into PDF (bonus feature) |
| Email | django-anymail | Unified interface to transactional email providers (license expiry reminders) |
| SMS | Twilio Python Helper Library | High-priority SMS alerts (bonus feature) |

## 5. Core Entities

- **User** — custom, email-based authentication, linked to exactly one Role/Group.
- **Vehicle** — the fleet asset registry.
- **Driver** — one-to-one with User, represents a driving employee.
- **Trip** — the junction entity linking a Driver, a Vehicle, and a route.
- **MaintenanceLog** — service records tied to a Vehicle.
- **FuelLog** — fuel purchase/consumption records tied to a Vehicle and optionally a Trip.
- **ExpenseLog** — ancillary costs (tolls, fines, parking) tied to a Vehicle and optionally a Trip.

Full field-level definitions live in `DATABASE_SCHEMA.md`.

## 6. Functional Requirements

### 6.1 Authentication
- Secure login using email and password (no username field).
- Role-Based Access Control (RBAC) via Django Groups.
- Only authenticated users may access any part of the application beyond the login page.

### 6.2 Dashboard
- KPIs: Active Vehicles, Available Vehicles, Vehicles in Maintenance, Active Trips, Pending Trips, Drivers On Duty, Fleet Utilization (%).
- Filters by vehicle type, status, and region.

### 6.3 Vehicle Registry
- Master list of vehicles: Registration Number (unique), Vehicle Name/Model, Type, Maximum Load Capacity, Odometer, Acquisition Cost, Status.
- Status values: `Available`, `On Trip`, `In Shop`, `Retired`.

### 6.4 Driver Management
- Driver profiles: Name, License Number, License Category, License Expiry Date, Contact Number, Safety Score, Status.
- Status values: `Available`, `On Trip`, `Off Duty`, `Suspended`.

### 6.5 Trip Management
- Create trips by selecting source, destination, an available vehicle, an available driver, cargo weight, and planned distance.
- Trip lifecycle: `Draft` → `Dispatched` → `Completed`, with a divergent path to `Cancelled` from `Dispatched`.

### 6.6 Maintenance
- Create maintenance records for vehicles.
- Adding an open maintenance record automatically switches the vehicle's status to `In Shop`, removing it from the driver's selection pool.

### 6.7 Fuel & Expense Management
- Record fuel logs (liters, cost, date).
- Record other expenses (tolls, fines, parking).
- Automatically compute total operational cost (Fuel + Maintenance) per vehicle.

### 6.8 Reports & Analytics
- Fuel Efficiency = Distance Traveled / Fuel Consumed (liters).
- Fleet Utilization = (Total Operating Hours / Total Available Hours) × 100.
- Operational Cost = Fuel Costs + Maintenance Costs (+ Expenses).
- Vehicle ROI = (Revenue − (Maintenance Costs + Fuel Costs)) / Acquisition Cost.
- CSV export is mandatory; PDF export is a bonus feature.

## 7. Mandatory Business Rules

These rules are **non-negotiable** and must be enforced at the model/business-logic layer (via `django-fsm-2` transitions and model `clean()`/validators), not only in forms or templates:

1. The vehicle registration number must be unique.
2. Retired or In Shop vehicles must never appear in the dispatch selection pool.
3. Drivers with expired licenses or `Suspended` status cannot be assigned to trips.
4. A driver or vehicle already marked `On Trip` cannot be assigned to another trip.
5. Cargo Weight must not exceed the vehicle's maximum load capacity.
6. Dispatching a trip automatically changes both the vehicle and driver status to `On Trip`.
7. Completing a trip automatically changes both the vehicle and driver status back to `Available`.
8. Cancelling a dispatched trip restores the vehicle and driver to `Available`.
9. Creating an active maintenance record automatically changes vehicle status to `In Shop`.
10. Closing maintenance restores the vehicle to `Available` (unless it is flagged Retired).

Full FSM transition specifications live in `PHASE_03_BUSINESS_LOGIC/`.

## 8. Example End-to-End Workflow

1. Register a vehicle `Van-05` with a maximum capacity of 500 kg. Status = `Available`.
2. Register driver `Alex` with a valid driving license.
3. Create a trip with Cargo Weight = 450 kg.
4. System validates that 450 kg ≤ 500 kg and allows dispatch.
5. Vehicle and Driver status automatically become `On Trip`.
6. Complete the trip by entering the final odometer and fuel consumed.
7. System marks both Vehicle and Driver as `Available`.
8. Create a maintenance record (e.g., Oil Change). Vehicle status automatically becomes `In Shop` and is hidden from dispatch.
9. Reports update operational cost and fuel efficiency based on the latest trip and fuel log.

## 9. Mandatory Deliverables

- Responsive web interface
- Authentication with RBAC
- CRUD for Vehicles and Drivers
- Trip Management with validations
- Automatic status transitions
- Maintenance workflow
- Fuel & Expense tracking
- Dashboard with KPIs
- Charts and visual analytics

## 10. Bonus Features

- PDF export of trip manifests / financial reports (WeasyPrint)
- Email reminders for expiring licenses (django-anymail)
- SMS alerts for high-priority events (Twilio)
- Vehicle document management
- Search, filters, and sorting across all list views
- Dark mode (Tailwind native dark mode)
- Geospatial route selection and automatic distance calculation (Leaflet.js + OSRM)
- Real-time weather context on active trips (OpenWeatherMap)
- Algorithmic predictive maintenance alerts (engine-hours-to-mileage conversion, threshold triggers, MTTR/MTBF)

## 11. Success Criteria

The build is considered successful when:

- All mandatory business rules in Section 7 are enforced at the model layer and cannot be bypassed via the Django Admin, a bulk operation, or a malformed request.
- All four roles see an appropriately scoped, permission-correct view of the application.
- The Trip lifecycle FSM cannot enter an illegal state under any code path.
- The Dashboard KPIs and Financial Analytics reflect live, correctly aggregated data — not hardcoded or stale values.
- CSV export works for at least Vehicles, Trips, and Financial records.
- The application is usable end-to-end by a reviewer following the example workflow in Section 8 without encountering an unhandled error.

## 12. Reference Mockup

UI wireframes: https://link.excalidraw.com/l/65VNwvy7c4X/1FHGDNgD2td

This mockup defines layout intent only. Any conflict between the mockup and this document on functional behavior is resolved in favor of this document.
