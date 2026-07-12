from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from fleet.models import Vehicle
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
        vehicles = vehicles.filter(vehicle_type=vehicle_type)
    # the Phase 2 Vehicle model does not have a region field, we'll ignore it safely
    # if region:
    #     vehicles = vehicles.filter(region=region)
    if status:
        vehicles = vehicles.filter(status=status)

    # Compute filtered KPIs
    kpis = {
        "active_vehicles": vehicles.filter(status="On Trip").count(),
        "available_vehicles": vehicles.filter(status="Available").count(),
        "in_maintenance": vehicles.filter(status="In Shop").count(),
        "active_trips": Trip.objects.filter(status="dispatched", vehicle__in=vehicles).count(),
        "pending_trips": Trip.objects.filter(status="draft", vehicle__in=vehicles).count(),
        "drivers_on_duty": Driver.objects.filter(status="On Trip").count(),
        "fleet_utilization": get_fleet_utilization(),
    }

    # Chart datasets (JSON serialized for Chart.js)
    chart_data = {
        "labels": ["Available", "On Trip", "In Shop", "Retired"],
        "data": [
            vehicles.filter(status="Available").count(),
            vehicles.filter(status="On Trip").count(),
            vehicles.filter(status="In Shop").count(),
            vehicles.filter(status="Retired").count(),
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
