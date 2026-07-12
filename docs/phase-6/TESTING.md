# Testing, Integration, and QA

## Goal
Implement a robust automated testing suite to validate role-based access control, FSM status transitions integrity, and cost calculations while preventing regression issues.

## Scope
- Unit tests for FSM transition states (Vehicle, Driver, Trip).
- Integration tests checking complete trip lifecycles (Draft → Dispatched → Completed).
- Security checks confirming RBAC restrictions across all dashboards and reports.
- Mocking configurations for external APIs (OSRM, OpenWeatherMap, Twilio).

## Responsibilities
- **QA Engineer / Developer**: Build test suites, configure mock responses, run local coverage audits.

## Django App(s)
`accounts`, `fleet`, `drivers`, `trips`, `reports` (individual `tests.py` files)

## Files to Create / Modify
```
accounts/tests.py     # RBAC access verification tests
fleet/tests.py        # Vehicle model and FSM checks
trips/tests.py        # Trip lifecycle integration and FSM checks
reports/tests.py      # Calculations precision validation
```

## Dependencies
- Completed base modules, FSM configurations, and calculation helpers.
- Standard Django test library wrapper (`django.test`).

## Business Rules
1. **Mocking External Connections**: Testing execution must run completely offline. No actual API requests can be dispatched to Twilio, OpenWeather, or OSRM.
2. **State Transition Strictness**: FSM rules must reject illegal state changes:
   - Trying to dispatch a vehicle marked `In Shop` must raise an FSM exception.
   - Assigning a driver with an expired license to a trip must raise a ValidationError.
3. **Database Independence**: Each test case must utilize isolated test database tables, teardown states cleanly, and avoid polluting sequential execution steps.
4. **Calculations Exactness**: Validation calculations (such as ROI and Utilization) must check for precision values up to four decimal points.

## Implementation Steps

### Step 1 — Write FSM and Trip integration Tests
```python
# trips/tests.py
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from vehicles.models import Vehicle
from drivers.models import Driver
from trips.models import Trip
from django_fsm import TransitionNotAllowed

User = get_user_model()

class TripLifecycleTestCase(TestCase):
    def setUp(self):
        # Create test models
        self.user = User.objects.create_user(email="driver@test.com", password="password")
        self.vehicle = Vehicle.objects.create(
            registration_number="VAN-01",
            model="Transit Van",
            type="cargo_van",
            max_load_capacity=1000.00,
            odometer=5000,
            acquisition_cost=25000.00,
            status="available"
        )
        self.driver = Driver.objects.create(
            user=self.user,
            license_number="DL-12345",
            license_expiry_date=timezone.now().date() + timezone.timedelta(days=100),
            status="available"
        )

    def test_successful_trip_dispatch(self):
        # Create Draft Trip
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            cargo_weight=500.00,
            planned_distance=20.00,
            status="draft"
        )
        
        # Dispatch Trip
        trip.dispatch() # FSM transition
        trip.save()

        # Assert status updates
        self.assertEqual(trip.status, "dispatched")
        self.assertEqual(trip.vehicle.status, "on_trip")
        self.assertEqual(trip.driver.status, "on_trip")

    def test_overload_prevention(self):
        # Create overloaded trip
        with self.assertRaises(ValidationError):
            trip = Trip.objects.create(
                vehicle=self.vehicle,
                driver=self.driver,
                cargo_weight=1500.00, # Exceeds 1000.00 max capacity
                planned_distance=20.00,
                status="draft"
            )
```

### Step 2 — Write RBAC view Tests
```python
# accounts/tests.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

class RBACSecurityTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager_group = Group.objects.create(name="Fleet Manager")
        self.driver_group = Group.objects.create(name="Driver")
        
        # Manager User
        self.manager = User.objects.create_user(email="manager@test.com", password="password")
        self.manager.groups.add(self.manager_group)

        # Driver User
        self.driver = User.objects.create_user(email="driver@test.com", password="password")
        self.driver.groups.add(self.driver_group)

    def test_reports_view_permission(self):
        # Drivers should be denied access to reports page
        self.client.login(email="driver@test.com", password="password")
        response = self.client.get(reverse("reports:overview"))
        self.assertEqual(response.status_code, 403) # Forbidden

        # Managers should be permitted
        self.client.login(email="manager@test.com", password="password")
        response = self.client.get(reverse("reports:overview"))
        self.assertEqual(response.status_code, 200) # Success
```

## Success Scenario
1. Developer runs `python manage.py test`.
2. The testing harness builds the temporary SQL database structures.
3. 24 test cases execute, inspecting validation parameters, FSM guards, and decorators.
4. Terminal returns "OK (failures=0)".

## Definition of Done
- [ ] Tests execute offline with complete mock wrapper implementations.
- [ ] Overload checks and expired license guards are verified via assertion tests.
- [ ] Access controls (RBAC groups) checked against protected view patterns.
- [ ] Live calculations match exact test values.
- [ ] No circular configuration loops occur when importing mock components.

## AI Instructions
- Utilize python's `unittest.mock.patch` library decorators to override Twilio's client post requests and return status `200` responses dynamically during testing execution.
- Maintain test datasets clean; avoid reusing primary key numbers within test fixtures to prevent uniqueness errors.
- Test FSM guard failures explicitly by validating that illegal action calls throw `TransitionNotAllowed` errors.
