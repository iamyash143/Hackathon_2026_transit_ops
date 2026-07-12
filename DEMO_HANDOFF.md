# TransitOps Demo Handoff

Use this sheet to share the local demo with a teammate and record a walkthrough video.

## 1. Start The App

From the project folder:

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Local URL:

```text
http://127.0.0.1:8000/
```

If sharing on the same Wi-Fi:

```bash
ipconfig getifaddr en0
python manage.py runserver 0.0.0.0:8000
```

Friend opens:

```text
http://YOUR_MAC_IP:8000/login/
```

Add the IP to `.env` before sharing:

```dotenv
ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_MAC_IP
```

Restart `runserver` after editing `.env`.

## 2. Demo Accounts

All demo accounts use the same password:

```text
DemoPass2026!
```

| Role | Email | What To Show |
| --- | --- | --- |
| Admin | `admin@transitops.local` | Admin access and full data overview |
| Fleet Manager | `manager@transitops.local` | Main demo account for dashboard, vehicles, drivers, trips, maintenance |
| Driver | `driver@transitops.local` | Restricted role view |
| Safety Officer | `safety@transitops.local` | Safety and compliance-focused access |
| Financial Analyst | `finance@transitops.local` | Finance, reports, and cost visibility |

Important: Django stores hashed passwords, so the original password cannot be read from the database. To reset demo accounts:

```bash
python manage.py seed_demo_data
```

Or set a new shared password:

```bash
python manage.py seed_demo_data --password NewDemoPassword123!
```

## 3. Video Flow

Recommended recording account:

```text
manager@transitops.local
DemoPass2026!
```

### Opening

1. Open `http://127.0.0.1:8000/`.
2. Show that it redirects into the app.
3. Login as Fleet Manager.
4. Briefly introduce TransitOps as a smart transport operations platform for fleet, drivers, trips, maintenance, finance, reports, and alerts.

### Dashboard

1. Open Dashboard.
2. Show KPI cards and operational overview.
3. Mention that the dashboard is driven by seeded vehicles, trips, maintenance logs, fuel logs, and expenses.

### Vehicles

1. Open Vehicles.
2. Show the seeded fleet:
   - Pune Linehaul 12T
   - Bengaluru Urban Van
   - Delhi Shuttle Coach
   - Mumbai Refrigerated 8T
   - Jaipur Spare Pickup
3. Open one vehicle detail page.
4. Point out status, odometer, capacity, acquisition cost, and operational cost metrics.

### Drivers

1. Open Drivers.
2. Show driver statuses and safety scores.
3. Highlight:
   - One driver has an expiring-soon license.
   - One driver has an expired license and is suspended.
4. Explain that driver eligibility is checked before trip dispatch.

### Trips

1. Open Trips.
2. Show completed trips and an active/dispatched trip.
3. Open a trip detail page.
4. Explain the trip lifecycle:
   - Draft
   - Dispatched
   - Completed
   - Cancelled
5. Mention that dispatch updates vehicle and driver availability.

### Maintenance

1. Open Maintenance.
2. Show the closed preventive service entry.
3. Show the open maintenance entry for the Delhi Shuttle Coach.
4. Explain that open maintenance moves a vehicle into the shop.

### Finance

1. Open Finance.
2. Show fuel logs.
3. Show expense logs.
4. Explain how costs feed reports and vehicle operational metrics.

### Reports

1. Open Reports.
2. Show overview/export options if available.
3. Mention CSV/PDF reporting support for operations review.

### Role-Based Access

1. Logout.
2. Login as `driver@transitops.local`.
3. Show that the user has a more restricted experience.
4. Logout and return to Fleet Manager if needed.

## 4. Suggested Voiceover

TransitOps is a Django-based smart transport operations platform. It centralizes fleet assets, driver compliance, trip dispatch, maintenance, finance logs, and reporting in one role-based system.

For the demo, we seeded realistic transport data: five vehicles, four drivers, active and completed trips, maintenance records, fuel logs, and expense logs. The Fleet Manager can monitor operations from the dashboard, inspect fleet and driver readiness, dispatch trips, and track maintenance impact.

The system also supports role-based access. Managers, drivers, safety officers, and financial analysts each see workflows relevant to their responsibilities. This keeps operations controlled while still giving every team member the data they need.

## 5. Troubleshooting

If the browser shows `Page not found (404)`:

```text
Use /login/ or /dashboard/
```

If Django says a table does not exist:

```bash
python manage.py migrate
python manage.py seed_demo_data
```

If login fails:

```bash
python manage.py seed_demo_data
```

If friend cannot open the shared URL:

1. Make sure both devices are on the same Wi-Fi.
2. Run server with `0.0.0.0:8000`.
3. Add your Mac IP to `ALLOWED_HOSTS`.
4. Restart the Django server.
5. Check macOS firewall settings if still blocked.

## 6. Quick Links

```text
/login/
/dashboard/
/vehicles/
/drivers/
/trips/
/maintenance/
/finance/
/reports/
/admin/
```
