# Release and Demo Checklist

## Goal
Establish a structured deployment check sequence and a step-by-step live demonstration workflow to guarantee successful production launches and high-fidelity presentations.

## Scope
- Production settings audit (security keys, debug mode configuration).
- Static assets compilation and database migration rules.
- Seed data commands execution.
- Step-by-step presentation scenario (Demo Checklist).

## Responsibilities
- **Release Engineer**: Coordinate environment configurations, execute database migrations, verify static files.
- **Presenter**: Walk through the demo script sequence during stakeholder reviews.

## Django App(s)
Project-level configuration (`transit_project`)

## Files to Create / Modify
```
transit_project/
  settings.py         # Audit for production readiness
docs/
  phase-6/
    RELEASE.md        # This checklist registry
```

## Dependencies
- Complete and passing test runner execution (Phase 6 `TESTING.md` validation).
- Access to production hosting environment (local production setup, AWS, or Heroku).

## Business Rules
1. **Security Isolation**: `DEBUG` setting must remain `False` in production. Any database execution must utilize secure environment parameters.
2. **Deterministic Seeding**: Running the seeding commands must create a standard, uncorrupted base dataset consisting of groups, permissions, and test accounts.
3. **Demo Resilience**: The demonstration workflow must work deterministically. Avoid using random inputs during the live demo to prevent math check failures.

## Implementation Steps

### Step 1 — Production Settings Verification
Verify setting flags before deploying:
```python
# transit_project/settings.py
import os

DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "True") == "True"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### Step 2 — Production Launch Checklist
Execute these commands sequentially on target hosting environments:
1. **Pull codebase updates**:
   ```bash
   git pull origin main
   ```
2. **Apply migrations**:
   ```bash
   python manage.py migrate
   ```
3. **Compile static assets**:
   ```bash
   python manage.py collectstatic --noinput
   ```
4. **Seed base structures**:
   ```bash
   python manage.py seed_groups
   python manage.py create_demo_users
   ```

### Step 3 — Presentation Demo Script (Demo Checklist)
Follow this exact narrative path during demo presentations:
- **Step 1: System Entry**: Log in as a Fleet Manager. Highlight the base layout navbar and the live KPI dashboard cards.
- **Step 2: Asset Setup**: Register a new vehicle:
  - Registration: `VAN-05`
  - Model: `Mercedes Sprinter`
  - Type: `Cargo Van`
  - Maximum Load Capacity: `500` kg
  - Status: `Available`
- **Step 3: Crew Setup**: Register a new driver:
  - Name: `Alex`
  - License Number: `LIC-9988`
  - Expiry Date: Set to one year in the future.
  - Status: `Available`
- **Step 4: Dispatch Request**: Create a new Trip:
  - Source: `Delhi`
  - Destination: `Noida`
  - Weight: `450` kg (The system automatically validates that `450` kg ≤ `500` kg capacity limit).
  - planned_distance: Leaflet routing engine auto-calculates distance and displays the road path.
- **Step 5: Trip Dispatched**: Transition the trip status to `Dispatched`.
  - Show that both `VAN-05` vehicle and driver `Alex` automatically transition to `On Trip` status.
- **Step 6: Double-Booking Prevention**: Attempt to schedule another concurrent trip using `VAN-05`. Observe that the platform blocks selection, showing that the vehicle is currently unavailable.
- **Step 7: Trip Completion**: Complete the trip:
  - Record the final odometer.
  - Log `50` liters of fuel used.
  - Confirm both vehicle and driver return to `Available` status.
- **Step 8: Maintenance Outage**: Create a Maintenance Log (e.g., Oil Change, Cost: ₹2,500).
  - Observe vehicle status automatically transition to `In Shop`.
  - Confirm it is hidden from the trip dispatch lists.
- **Step 9: Financial Review**: Navigate to the Reports screen:
  - Verify that the ROI chart, fuel cost aggregation, and efficiency charts update.
  - Export the financial analytics page to CSV and verify file output formatting.
  - Toggle Dark Mode and show UI visual responsiveness.

## Success Scenario
1. Release engineer completes deployment steps on target server.
2. Seeding runs with zero database conflicts.
3. Presenter performs the 9-step demo script.
4. All validations pass, and charts display correctly on both light and dark layouts.

## Definition of Done
- [ ] Production flags (DEBUG=False, Allowed Hosts) verified.
- [ ] Database migrations execute cleanly.
- [ ] Seeding CLI command is fully functional.
- [ ] All 9 steps of the demo script execute without manual database changes.
- [ ] Assets load over standard web protocols with zero styling breakage.

## AI Instructions
- Maintain absolute separation of production secrets from git check-ins. Put all sensitive passwords and API keys inside server environment variable sheets.
- Include database transaction wrappers (`transaction.atomic`) on seeding CLI commands so that half-executed seed runs roll back cleanly in case of errors.
- Ensure that the styling assets are collected to directories accessible by production web servers (e.g. Nginx or WhiteNoise).
