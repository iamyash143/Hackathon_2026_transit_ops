import csv
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string

from accounts.decorators import role_required
from finance.models import FuelLog
from fleet.models import Vehicle
from maintenance.models import MaintenanceLog
from trips.models import Trip


def _filtered_vehicles(request):
    queryset = Vehicle.objects.exclude(status='Retired')
    vehicle_type = request.GET.get('vehicle_type')
    search_query = request.GET.get('search')

    if vehicle_type:
        queryset = queryset.filter(vehicle_type=vehicle_type)
    if search_query:
        queryset = queryset.filter(
            Q(registration_number__icontains=search_query) | Q(name__icontains=search_query)
        )
    return queryset, vehicle_type, search_query


@login_required
@role_required('Fleet Manager', 'Financial Analyst')
def reports_overview(request):
    queryset, vehicle_type, search_query = _filtered_vehicles(request)
    sort_by = request.GET.get('sort', 'registration_number')
    decimal_zero = Value(Decimal('0.00'), output_field=DecimalField(max_digits=12, decimal_places=2))

    fuel_subquery = FuelLog.objects.filter(vehicle=OuterRef('pk')).values('vehicle').annotate(
        total=Sum('cost')
    ).values('total')
    maintenance_subquery = MaintenanceLog.objects.filter(vehicle=OuterRef('pk')).values('vehicle').annotate(
        total=Sum('cost')
    ).values('total')

    vehicles = queryset.annotate(
        annotated_fuel_cost=Coalesce(
            Subquery(fuel_subquery, output_field=DecimalField(max_digits=10, decimal_places=2)),
            decimal_zero,
        ),
        annotated_maint_cost=Coalesce(
            Subquery(maintenance_subquery, output_field=DecimalField(max_digits=10, decimal_places=2)),
            decimal_zero,
        ),
    ).annotate(total_operational_cost=F('annotated_fuel_cost') + F('annotated_maint_cost'))

    sort_mapping = {
        'registration_number': 'registration_number',
        'total_cost': 'total_operational_cost',
        '-total_cost': '-total_operational_cost',
    }
    context = {
        'vehicles': vehicles.order_by(sort_mapping.get(sort_by, 'registration_number')),
        'current_sort': sort_by,
        'filters': {'vehicle_type': vehicle_type, 'search': search_query},
    }
    if request.headers.get('HX-Request'):
        return render(request, 'reports/partials/vehicle_table.html', context)
    return render(request, 'reports/overview.html', context)


@login_required
@role_required('Fleet Manager', 'Financial Analyst')
def export_vehicles_csv(request):
    vehicles, _, _ = _filtered_vehicles(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="vehicles_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Registration Number', 'Name', 'Type', 'Status', 'Odometer'])
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
    html = HTML(
        string=render_to_string('reports/pdf/trip_manifest.html', {'trip': trip}),
        base_url=request.build_absolute_uri('/'),
    )
    response = HttpResponse(html.write_pdf(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="manifest_{trip.pk}.pdf"'
    return response
