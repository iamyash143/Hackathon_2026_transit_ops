import csv
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, OuterRef, Subquery, DecimalField, F
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.template.loader import render_to_string
from accounts.decorators import role_required
from fleet.models import Vehicle
from finance.models import FuelLog
from maintenance.models import MaintenanceLog
from trips.models import Trip

@login_required
@role_required(allowed_roles=["Fleet Manager", "Financial Analyst"])
def reports_overview(request):
    # Base query
    queryset = Vehicle.objects.exclude(status="Retired")

    # Handle filters
    vehicle_type = request.GET.get("vehicle_type")
    region = request.GET.get("region")
    search_query = request.GET.get("search")
    sort_by = request.GET.get("sort", "registration_number")

    if vehicle_type:
        queryset = queryset.filter(vehicle_type=vehicle_type)
    if search_query:
        queryset = queryset.filter(registration_number__icontains=search_query) | queryset.filter(name__icontains=search_query)

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

@login_required
@role_required(allowed_roles=["Financial Analyst", "Fleet Manager"])
def export_vehicles_csv(request):
    # Retrieve identical queryset filters
    vehicle_type = request.GET.get("vehicle_type")
    search_query = request.GET.get("search")

    vehicles = Vehicle.objects.exclude(status="Retired")
    if vehicle_type:
        vehicles = vehicles.filter(vehicle_type=vehicle_type)
    if search_query:
        vehicles = vehicles.filter(registration_number__icontains=search_query) | vehicles.filter(name__icontains=search_query)

    # Set up HTTP response headers
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="vehicles_report.csv"'

    writer = csv.writer(response)
    # Header row
    writer.writerow(["Registration Number", "Name", "Type", "Status", "Odometer"])

    # Write data rows
    for vehicle in vehicles:
        writer.writerow([
            vehicle.registration_number,
            vehicle.name,
            vehicle.vehicle_type,
            vehicle.status,
            vehicle.odometer,
        ])

    return response

@login_required
def export_trip_manifest_pdf(request, trip_id):
    from weasyprint import HTML

    trip = get_object_or_404(Trip, pk=trip_id)

    # Render HTML template to a string context
    html_string = render_to_string("reports/pdf/trip_manifest.html", {"trip": trip})

    # Initialize WeasyPrint document
    html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
    pdf_file = html.write_pdf()

    # Return as PDF attachment
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="manifest_{trip.pk}.pdf"'
    return response
