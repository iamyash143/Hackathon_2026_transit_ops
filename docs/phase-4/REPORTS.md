# Reports & Analytics

## Goal
Implement a dynamic reports and analytics platform exposing detailed operational cost metrics, fuel efficiency ratios, and vehicle ROI. Enable Fleet Managers and Financial Analysts to perform search, multi-attribute filtering, and multi-column sorting on annotated datasets without experiencing N+1 performance bottlenecks.

## Scope
- Searchable and sortable reports dashboard (`/reports/`) protected by authentication and role validation.
- Live database annotations compiling total fuel cost, total maintenance cost, and vehicle ROI.
- Text search matching vehicle registration numbers or names.
- Multi-dimensional filters (vehicle type, region, status).
- Column sorting (by ROI, total costs, or fuel efficiency).
- Integrated summary bar displaying average efficiency and total fleet spending.

## Responsibilities
- **Financial Analyst**: Full read and export access to ROI computations, cost distributions, and financial records.
- **Fleet Manager**: Read access to operational metrics, vehicle lifecycles, and fleet efficiency reports.
- **Safety Officer & Driver**: Restrained access; dashboard redirects or permission denial responses.

## Django App(s)
`reports`

## Files to Create / Modify
```
reports/
  __init__.py
  apps.py             # App configuration
  views.py            # Reports list view with SQL Subqueries
  urls.py             # Route definitions
  templates/
    reports/
      overview.html   # Main report layout with tables and filters
      partials/
        vehicle_table.html # HTMX partial template for table row updates
```

## Dependencies
- Phase 3 `Cost Calculations` (`reports/metrics.py`) for metrics logic.
- Phase 2 models (`Vehicle`, `Trip`, `FuelLog`, `MaintenanceLog`, `ExpenseLog`).
- Phase 1 custom decorators/mixins for role authorization checks.

## Business Rules
1. **Performance Requirement**: All operational and financial reports must run in a single SQL query per request. Calling property methods (e.g., `vehicle.roi` or `vehicle.operational_cost`) inside template loops is strictly forbidden.
2. **Numeric Safety**:
   - Division by zero must return `None` (rendered as `—` in templates).
   - All currency values must utilize the `Decimal` data type and format with two decimal places.
3. **FSM Compliance**: Completed trip counts must verify that `Trip.status == 'completed'` and `final_odometer` values are populated.
4. **Access Control**: Users must belong to `Fleet Manager` or `Financial Analyst` groups to access this feature.

## Implementation Steps

### Step 1 — Scaffold the Reports App
Initialize the app and declare URLs namespace.
```python
# reports/urls.py
from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.reports_overview, name="overview"),
]
```

### Step 2 — Implement optimized reports view
Write an annotated query view in `reports/views.py`.
```python
# reports/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, OuterRef, Subquery, DecimalField, F
from django.db.models.functions import Coalesce
from accounts.decorators import role_required
from vehicles.models import Vehicle
from expenses.models import FuelLog
from maintenance.models import MaintenanceLog

@login_required
@role_required(allowed_roles=["Fleet Manager", "Financial Analyst"])
def reports_overview(request):
    # Base query
    queryset = Vehicle.objects.exclude(status="retired")

    # Handle filters
    vehicle_type = request.GET.get("vehicle_type")
    region = request.GET.get("region")
    search_query = request.GET.get("search")
    sort_by = request.GET.get("sort", "registration_number")

    if vehicle_type:
        queryset = queryset.filter(type=vehicle_type)
    if region:
        queryset = queryset.filter(region=region)
    if search_query:
        queryset = queryset.filter(registration_number__icontains=search_query) | queryset.filter(model__icontains=search_query)

    # Subqueries for aggregation to avoid N+1 query loops
    fuel_subquery = FuelLog.objects.filter(vehicle=OuterRef("pk")).values("vehicle").annotate(
        total=Sum("cost")
    ).values("total")

    maint_subquery = MaintenanceLog.objects.filter(vehicle=OuterRef("pk")).values("vehicle").annotate(
        total=Sum("cost")
    ).values("total")

    # Annotate vehicle queryset
    queryset = queryset.annotate(
        annotated_fuel_cost=Coalesce(Subquery(fuel_subquery, output_field=DecimalField()), 0.00),
        annotated_maint_cost=Coalesce(Subquery(maint_subquery, output_field=DecimalField()), 0.00),
    ).annotate(
        total_operational_cost=F("annotated_fuel_cost") + F("annotated_maint_cost")
    )

    # Simple dynamic sorting mapping
    sort_mapping = {
        "registration_number": "registration_number",
        "total_cost": "total_operational_cost",
        "-total_cost": "-total_operational_cost",
    }
    queryset = queryset.order_by(sort_mapping.get(sort_by, "registration_number"))

    context = {
        "vehicles": queryset,
        "current_sort": sort_by,
        "filters": {
            "vehicle_type": vehicle_type,
            "region": region,
            "search": search_query,
        }
    }

    if request.headers.get("HX-Request"):
        return render(request, "reports/partials/vehicle_table.html", context)

    return render(request, "reports/overview.html", context)
```

### Step 3 — Template markup with HTMX search and sorting
```html
<!-- reports/templates/reports/overview.html -->
{% extends "base.html" %}

{% block content %}
<div class="p-6 bg-gray-50 dark:bg-gray-900 min-h-screen">
  <div class="mb-6 flex justify-between items-center">
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white">Operational Reports</h1>
  </div>

  <!-- Search & Filters -->
  <div class="mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg shadow flex flex-wrap gap-4">
    <input type="text" name="search" placeholder="Search registration or model..." 
           hx-get="{% url 'reports:overview' %}" 
           hx-trigger="keyup changed delay:300ms" 
           hx-target="#report-table-body" 
           class="rounded-md border-gray-300 dark:bg-gray-700 dark:text-white w-64">
  </div>

  <!-- Data Table -->
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
    <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
      <thead class="bg-gray-100 dark:bg-gray-700">
        <tr>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            Vehicle
          </th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
            <a href="?sort={% if current_sort == 'total_cost' %}-total_cost{% else %}total_cost{% endif %}" hx-get="{% url 'reports:overview' %}?sort={% if current_sort == 'total_cost' %}-total_cost{% else %}total_cost{% endif %}" hx-target="#report-table-body">
              Operational Cost
            </a>
          </th>
        </tr>
      </thead>
      <tbody id="report-table-body" class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
        {% include "reports/partials/vehicle_table.html" %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

### Step 4 — Partial table body
```html
<!-- reports/templates/reports/partials/vehicle_table.html -->
{% for vehicle in vehicles %}
<tr>
  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
    {{ vehicle.registration_number }} ({{ vehicle.model }})
  </td>
  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
    ₹{{ vehicle.total_operational_cost|floatformat:2 }}
  </td>
</tr>
{% empty %}
<tr>
  <td colspan="2" class="px-6 py-4 text-center text-sm text-gray-500">No records found.</td>
</tr>
{% endfor %}
```

## Success Scenario
1. A Financial Analyst accesses `/reports/`.
2. The user inputs "Van-05" in the search box.
3. Within 300ms, the table filters down to vehicles containing "Van-05" in their registration number or model.
4. Database analytics show single query execution under SQL logs.

## Definition of Done
- [ ] Reports view uses `Subquery` to pre-aggregate related values instead of looping properties.
- [ ] Search input is debounced using `hx-trigger="keyup changed delay:300ms"`.
- [ ] Sort anchors update sorting state asynchronously via HTMX headers.
- [ ] Zero values are formatted correctly using the `floatformat:2` filters.
- [ ] View is limited to authenticated Fleet Managers and Financial Analysts.

## AI Instructions
- Write raw SQL query mappings or `Coalesce` statements to replace empty query return values with `0.00` to prevent math operators from breaking on `None`.
- Do not mix presentation formatting (like currency symbols) within Python views; handle all symbols and locale formatters in Django template layouts.
