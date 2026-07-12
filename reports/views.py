from django.db.models import Sum, OuterRef, Subquery
from django.shortcuts import render
from fleet.models import Vehicle
from finance.models import FuelLog
from maintenance.models import MaintenanceLog
from reports.metrics import get_dashboard_kpis

def reports_view(request):
    fuel_subquery = FuelLog.objects.filter(
        vehicle=OuterRef("pk")
    ).values("vehicle").annotate(total=Sum("cost")).values("total")

    maint_subquery = MaintenanceLog.objects.filter(
        vehicle=OuterRef("pk")
    ).values("vehicle").annotate(total=Sum("cost")).values("total")

    vehicles = Vehicle.objects.annotate(
        total_fuel_cost=Subquery(fuel_subquery),
        total_maint_cost=Subquery(maint_subquery),
    )

    context = {
        "vehicles": vehicles,
        "kpis": get_dashboard_kpis(),
    }
    return render(request, "reports/overview.html", context)
