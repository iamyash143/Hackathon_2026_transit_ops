# Role-Based Access Control (RBAC)

## Goal

Enforce role-level permissions across all views and API endpoints.
Each authenticated user belongs to exactly one Django Group that maps to a
functional role. Views must verify group membership before executing any business logic.

---

## Scope

- Define the four operational roles as Django Groups.
- Create reusable mixins and decorators for role enforcement.
- Apply access control to all existing views (CRUD endpoints are already built — this adds the gate).
- No new models. No new URLs. Only permission enforcement.

---

## Responsibilities

| Role | Can Do |
|---|---|
| **Fleet Manager** | Full CRUD on Vehicles and Maintenance. Read Trips. View all reports. |
| **Driver** | Read own assigned trips only. Update trip status (Dispatched → Completed). Log fuel and expenses. |
| **Safety Officer** | Full CRUD on Drivers. Read Vehicles, Trips, and compliance reports. |
| **Financial Analyst** | Read-only on all operational data. Full access to Expenses, Fuel Logs, and analytics. |

---

## Django App

`accounts` (or wherever the custom `User` model lives)

---

## Files to Create / Modify

```
accounts/
  rbac.py              # Role constants, mixins, decorators — CREATE
  apps.py              # Add ready() call to seed groups — MODIFY
  management/
    commands/
      seed_groups.py   # One-time management command to create Groups + Permissions — CREATE

# Apply mixins to existing views across apps:
vehicles/views.py      # MODIFY — add RoleRequiredMixin
drivers/views.py       # MODIFY — add RoleRequiredMixin
trips/views.py         # MODIFY — add RoleRequiredMixin
maintenance/views.py   # MODIFY — add RoleRequiredMixin
expenses/views.py      # MODIFY — add RoleRequiredMixin
```

---

## Dependencies

- Custom `User` model must already exist with `email` as the primary identifier.
- Django's `Group` and `Permission` models (built-in, no extra packages needed).
- All CRUD views must already exist before applying mixins.

---

## Business Rules

1. A user with no group assigned must be treated as unauthorized — redirect to login.
2. A Driver may only see and update **their own** assigned trips. No cross-driver visibility.
3. A Safety Officer can suspend a driver (set `status = Suspended`) but cannot create or dispatch trips.
4. A Financial Analyst has **zero write access** to operational models (Vehicles, Drivers, Trips, Maintenance).
5. Fleet Manager cannot create or edit Driver profiles (that is the Safety Officer's domain).
6. Superusers bypass all group checks (Django default behavior — do not override).

---

## Implementation Steps

### Step 1 — Define Role Constants

```python
# accounts/rbac.py

ROLE_FLEET_MANAGER = "Fleet Manager"
ROLE_DRIVER = "Driver"
ROLE_SAFETY_OFFICER = "Safety Officer"
ROLE_FINANCIAL_ANALYST = "Financial Analyst"

ALL_ROLES = [
    ROLE_FLEET_MANAGER,
    ROLE_DRIVER,
    ROLE_SAFETY_OFFICER,
    ROLE_FINANCIAL_ANALYST,
]
```

---

### Step 2 — Seed Groups via Management Command

```python
# accounts/management/commands/seed_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from accounts.rbac import ALL_ROLES

ROLE_PERMISSIONS = {
    "Fleet Manager":      ["view_trip", "add_vehicle", "change_vehicle",
                           "delete_vehicle", "view_vehicle",
                           "add_maintenancelog", "change_maintenancelog",
                           "delete_maintenancelog", "view_maintenancelog"],
    "Driver":             ["view_trip", "change_trip",
                           "add_fuellog", "add_expenselog"],
    "Safety Officer":     ["add_driver", "change_driver", "delete_driver",
                           "view_driver", "view_vehicle", "view_trip"],
    "Financial Analyst":  ["view_vehicle", "view_driver", "view_trip",
                           "view_fuellog", "view_expenselog",
                           "view_maintenancelog",
                           "add_expenselog", "change_expenselog"],
}

class Command(BaseCommand):
    help = "Seed default RBAC groups and permissions"

    def handle(self, *args, **kwargs):
        for role_name, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            perms = Permission.objects.filter(codename__in=codenames)
            group.permissions.set(perms)
            self.stdout.write(f"  Seeded: {role_name} ({perms.count()} permissions)")
```

Run once after migrations:
```bash
python manage.py seed_groups
```

---

### Step 3 — Build Reusable Mixins

```python
# accounts/rbac.py (continued)

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(AccessMixin):
    """
    Add `allowed_roles = [ROLE_FLEET_MANAGER]` to any CBV.
    Raises 403 if the authenticated user's group is not in allowed_roles.
    """
    allowed_roles: list[str] = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_superuser:
            user_groups = request.user.groups.values_list("name", flat=True)
            if not any(role in user_groups for role in self.allowed_roles):
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def role_required(*roles):
    """Decorator for function-based views."""
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if not request.user.is_superuser:
                user_groups = request.user.groups.values_list("name", flat=True)
                if not any(r in user_groups for r in roles):
                    raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def get_user_role(user) -> str | None:
    """Returns the user's primary role name, or None."""
    return user.groups.values_list("name", flat=True).first()
```

---

### Step 4 — Apply to Existing Views

**Class-based view example:**
```python
# vehicles/views.py
from accounts.rbac import RoleRequiredMixin, ROLE_FLEET_MANAGER

class VehicleCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = [ROLE_FLEET_MANAGER]
    model = Vehicle
    ...
```

**Function-based view example:**
```python
# trips/views.py
from accounts.rbac import role_required, ROLE_DRIVER, ROLE_FLEET_MANAGER

@role_required(ROLE_DRIVER, ROLE_FLEET_MANAGER)
def complete_trip(request, pk):
    ...
```

**Driver self-ownership filter (trips/views.py):**
```python
from accounts.rbac import get_user_role, ROLE_DRIVER

class TripListView(RoleRequiredMixin, ListView):
    allowed_roles = [ROLE_FLEET_MANAGER, ROLE_DRIVER, ROLE_SAFETY_OFFICER]

    def get_queryset(self):
        qs = Trip.objects.select_related("vehicle", "driver")
        if get_user_role(self.request.user) == ROLE_DRIVER:
            qs = qs.filter(driver__user=self.request.user)
        return qs
```

---

### Step 5 — Role-Aware Dashboard Routing

```python
# accounts/views.py or a shared dashboard view
from accounts.rbac import get_user_role

def dashboard(request):
    role = get_user_role(request.user)
    templates = {
        "Fleet Manager":     "dashboards/fleet_manager.html",
        "Driver":            "dashboards/driver.html",
        "Safety Officer":    "dashboards/safety_officer.html",
        "Financial Analyst": "dashboards/financial_analyst.html",
    }
    template = templates.get(role, "dashboards/default.html")
    return render(request, template, {})
```

---

## Success Scenario

1. A `Driver` logs in and navigates to `/trips/` — they see only their own trips.
2. The same user attempts to GET `/vehicles/create/` — they receive a 403 Forbidden page.
3. A `Financial Analyst` visits `/reports/` — full read access. Attempts POST to any form — blocked.
4. A `Safety Officer` updates a driver's status to `Suspended` — allowed. Tries to dispatch a trip — 403.

---

## Definition of Done

- [ ] `seed_groups` command runs without errors after a fresh `migrate`.
- [ ] `RoleRequiredMixin` applied to all vehicle, driver, trip, maintenance, and expense views.
- [ ] Driver queryset filter limits trip visibility to self-owned records only.
- [ ] 403 page renders (not a 500) when an unauthorized role hits a protected URL.
- [ ] Superuser bypasses all group checks.
- [ ] No raw `user.is_staff` or `user.is_superuser` checks used for role logic — only Group membership.

---

## AI Instructions

- Import roles from `accounts.rbac` constants — never hardcode role name strings in views.
- Always apply `RoleRequiredMixin` **before** `LoginRequiredMixin` in the MRO if both are used.
- Do not use Django's `@permission_required` decorator — use `role_required` from `accounts/rbac.py` for consistency.
- When filtering querysets by role, use `get_user_role()` helper — do not call `request.user.groups.filter(...)` inline in views.
- The `seed_groups` command must be idempotent — `get_or_create` on both Groups and permission assignments.
