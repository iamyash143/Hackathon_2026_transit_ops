# Dashboard

## Goal
Build a centralized, responsive dashboard displaying real-time Key Performance Indicators (KPIs) and interactive charts. It must dynamically filter metrics by vehicle type, status, and region, serving as the primary control center for all user roles.

## Scope
- Centralized dashboard landing page (`/dashboard/`) protected by authentication.
- Real-time KPI cards: Active Vehicles, Available Vehicles, Vehicles in Maintenance, Active Trips, Pending Trips, Drivers On Duty, and Fleet Utilization (%).
- Role-based UI components (RBAC integration).
- Asynchronous filtering by vehicle type, status, and region.
- Interactive data visualizations using Chart.js (Fleet Utilization trend, cost allocation, and status distribution).

## Responsibilities
- **Fleet Manager**: Full visibility of all KPI cards, fleet status, and active operations.
- **Financial Analyst**: Access to operational cost breakdowns, fleet utilization, and financial trend charts.
- **Safety Officer**: View of driver statuses, safety scores, and active driver ratios.
- **Driver**: Simplified personal landing page showing assigned trips and active tasks.

## Django App(s)
`dashboard` (new app) or `core`

## Files to Create / Modify
```
dashboard/
  __init__.py
  apps.py             # App configuration
  views.py            # Dashboard view with KPI aggregation and filtering
  urls.py             # Dashboard URL routing
  templates/
    dashboard/
      index.html      # Main dashboard structure (grid layout)
      partials/
        kpi_cards.html # HTMX partial for updated KPI cards
        charts.html    # HTMX partial for updated Chart.js datasets
```

## Dependencies
- Phase 1 `Base UI` setup (Tailwind CSS v4 + Flowbite).
- Phase 3 `Cost Calculations` (`reports/metrics.py`) for KPI functions.
- Phase 2 `RBAC` group classification to determine template layout.

## Business Rules
1. **Access Control**: Only authenticated users can access the dashboard.
2. **Dynamic Filtering**: Changing filter values (Vehicle Type, Vehicle Status, Region) must update both the KPI counters and the charts asynchronously using HTMX.
3. **Data Currency**: KPI counts must represent the live state of the database. Active metrics (e.g., Active Vehicles, Active Trips) must support optional HTMX polling every 30 seconds.
4. **Utilization Formula**: Fleet utilization calculation must filter out `retired` vehicles from the denominator.
5. **Role Restrictions**: Users without management or analyst roles must not see financial or ROI charts.

## Implementation Steps

### Step 1 — Scaffold the Dashboard App
Register the `dashboard` app in `settings.py` and set up URLs.
```python
# dashboard/apps.py
from django.apps import AppConfig

class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
```

### Step 2 — Implement the Dashboard View
Write a view that aggregates metrics based on requested filters.
```python
# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from vehicles.models import Vehicle
from drivers.models import Driver
from trips.models import Trip
from reports.metrics import get_dashboard_kpis, get_fleet_utilization

@login_required
def dashboard_home(request):
    # Extract filters
    vehicle_type = request.GET.get("vehicle_type")
    region = request.GET.get("region")
    status = request.GET.get("status")

    # Apply filters to base querysets
    vehicles = Vehicle.objects.all()
    if vehicle_type:
        vehicles = vehicles.filter(type=vehicle_type)
    if region:
        vehicles = vehicles.filter(region=region)
    if status:
        vehicles = vehicles.filter(status=status)

    # Compute filtered KPIs
    kpis = {
        "active_vehicles": vehicles.filter(status="on_trip").count(),
        "available_vehicles": vehicles.filter(status="available").count(),
        "in_maintenance": vehicles.filter(status="in_shop").count(),
        "active_trips": Trip.objects.filter(status="dispatched", vehicle__in=vehicles).count(),
        "pending_trips": Trip.objects.filter(status="draft", vehicle__in=vehicles).count(),
        "drivers_on_duty": Driver.objects.filter(status="on_trip").count(),
        "fleet_utilization": get_fleet_utilization(),
    }

    # Chart datasets (JSON serialized for Chart.js)
    chart_data = {
        "labels": ["Available", "On Trip", "In Shop", "Retired"],
        "data": [
            vehicles.filter(status="available").count(),
            vehicles.filter(status="on_trip").count(),
            vehicles.filter(status="in_shop").count(),
            vehicles.filter(status="retired").count(),
        ]
    }

    context = {
        "kpis": kpis,
        "chart_data": chart_data,
        "filters": {
            "vehicle_type": vehicle_type,
            "region": region,
            "status": status,
        }
    }

    # Handle HTMX partial updates
    if request.headers.get("HX-Request"):
        return render(request, "dashboard/partials/kpi_cards.html", context)

    return render(request, "dashboard/index.html", context)
```

### Step 3 — Main Dashboard HTML Layout
Construct a grid layout using Tailwind and Flowbite containing filter selectors, KPI cards, and chart containers.
```html
<!-- dashboard/templates/dashboard/index.html -->
{% extends "base.html" %}

{% block content %}
<div class="p-6 space-y-6">
  <!-- Filters Bar -->
  <form hx-get="{% url 'dashboard:home' %}" hx-target="#kpi-section" hx-trigger="change" class="flex flex-wrap gap-4 p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
    <div>
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Vehicle Type</label>
      <select name="vehicle_type" class="mt-1 block rounded-md border-gray-300 shadow-sm dark:bg-gray-700 dark:text-white">
        <option value="">All Types</option>
        <option value="heavy_truck">Heavy Truck</option>
        <option value="cargo_van">Cargo Van</option>
      </select>
    </div>
    <div>
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Region</label>
      <select name="region" class="mt-1 block rounded-md border-gray-300 shadow-sm dark:bg-gray-700 dark:text-white">
        <option value="">All Regions</option>
        <option value="north">North</option>
        <option value="south">South</option>
      </select>
    </div>
  </form>

  <!-- KPI Section (Swapped by HTMX) -->
  <div id="kpi-section" hx-get="{% url 'dashboard:home' %}" hx-trigger="every 30s" hx-target="this">
    {% include "dashboard/partials/kpi_cards.html" %}
  </div>

  <!-- Charts Grid -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    <div class="p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
      <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-4">Vehicle Status Distribution</h3>
      <div class="relative h-64">
        <canvas id="statusChart" data-chart-labels='{{ chart_data.labels|safe }}' data-chart-values='{{ chart_data.data|safe }}'></canvas>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', function () {
    const ctx = document.getElementById('statusChart').getContext('2d');
    const labels = JSON.parse(document.getElementById('statusChart').getAttribute('data-chart-labels'));
    const data = JSON.parse(document.getElementById('statusChart').getAttribute('data-chart-values'));

    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: ['#10B981', '#3B82F6', '#F59E0B', '#EF4444'],
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false
      }
    });
  });
</script>
{% endblock %}
```

### Step 4 — Implement HTMX KPI Card Partial
```html
<!-- dashboard/templates/dashboard/partials/kpi_cards.html -->
<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
  <!-- Active Vehicles Card -->
  <div class="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
    <span class="text-sm text-blue-600 dark:text-blue-400 font-semibold">Active Vehicles</span>
    <h4 class="text-2xl font-bold dark:text-white mt-1">{{ kpis.active_vehicles }}</h4>
  </div>
  <!-- Available Vehicles Card -->
  <div class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
    <span class="text-sm text-green-600 dark:text-green-400 font-semibold">Available Vehicles</span>
    <h4 class="text-2xl font-bold dark:text-white mt-1">{{ kpis.available_vehicles }}</h4>
  </div>
  <!-- Active Trips Card -->
  <div class="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
    <span class="text-sm text-purple-600 dark:text-purple-400 font-semibold">Active Trips</span>
    <h4 class="text-2xl font-bold dark:text-white mt-1">{{ kpis.active_trips }}</h4>
  </div>
  <!-- Utilization Card -->
  <div class="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
    <span class="text-sm text-yellow-600 dark:text-yellow-400 font-semibold">Fleet Utilization</span>
    <h4 class="text-2xl font-bold dark:text-white mt-1">{{ kpis.fleet_utilization }}%</h4>
  </div>
</div>
```

## Success Scenario
1. A Fleet Manager logs in and views `/dashboard/`.
2. All KPI numbers reflect live database statuses.
3. The user switches region filter to "North".
4. The dashboard cards update dynamically via HTMX without full-page reloads, showing only "North" region metrics.

## Definition of Done
- [ ] `/dashboard/` is mapped to `dashboard_home` view and protected with `@login_required`.
- [ ] KPI cards render correct values from database state.
- [ ] Region and vehicle type filters send parameters to view via HTMX.
- [ ] Active trips and vehicles auto-poll periodically (using HTMX `hx-trigger="every 30s"`).
- [ ] Chart.js successfully mounts and parses Django context lists inside HTML attributes.
- [ ] Appropriate CSS styles applied for both Light and Dark themes.

## AI Instructions
- Embed chart configuration values within safe-parsed HTML attributes (e.g., `data-chart-values="{{ chart_data.data|safe }}"`) rather than rendering dynamic inline javascript, avoiding syntax validation problems.
- Protect dashboard views against unauthorized user roles using Group-based check middleware or custom decorators.
- Ensure all numbers cast safely to strings before passing to JS frontend data attributes.
