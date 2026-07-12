from decimal import Decimal
from django.db.models import Sum, Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone


def get_vehicle_fuel_cost(vehicle) -> Decimal:
    from finance.models import FuelLog
    result = FuelLog.objects.filter(vehicle=vehicle).aggregate(
        total=Sum("cost")
    )
    return result["total"] or Decimal("0.00")


def get_vehicle_maintenance_cost(vehicle) -> Decimal:
    from maintenance.models import MaintenanceLog
    result = MaintenanceLog.objects.filter(vehicle=vehicle).aggregate(
        total=Sum("cost")
    )
    return result["total"] or Decimal("0.00")


def get_vehicle_operational_cost(vehicle) -> Decimal:
    return get_vehicle_fuel_cost(vehicle) + get_vehicle_maintenance_cost(vehicle)


def get_vehicle_fuel_efficiency(vehicle) -> Decimal | None:
    """
    Returns km per liter averaged across all completed trips.
    Returns None if no fuel data exists.
    """
    from finance.models import FuelLog
    from trips.models import Trip

    trips = Trip.objects.filter(
        vehicle=vehicle,
        status="completed",
        final_odometer__isnull=False,
    )

    total_distance = Decimal("0.00")
    total_liters   = Decimal("0.00")

    for trip in trips:
        try:
            log = FuelLog.objects.get(trip=trip)
            if log.liters and log.liters > 0:
                distance = Decimal(str(trip.planned_distance))
                total_distance += distance
                total_liters   += log.liters
        except FuelLog.DoesNotExist:
            continue

    if total_liters == 0:
        return None
    return round(total_distance / total_liters, 2)


def get_vehicle_roi(vehicle, revenue: Decimal = Decimal("0.00")) -> Decimal | None:
    """
    ROI = (Revenue - (Maintenance + Fuel)) / Acquisition Cost
    Returns None if acquisition_cost is zero to prevent ZeroDivisionError.
    """
    if not getattr(vehicle, 'acquisition_cost', None) or vehicle.acquisition_cost == 0:
        return None

    op_cost = get_vehicle_operational_cost(vehicle)
    roi = (revenue - op_cost) / vehicle.acquisition_cost
    return round(roi, 4)


def get_fleet_utilization() -> Decimal:
    """
    Fleet utilization = (total dispatched hours / total available window hours) * 100
    Computed across ALL vehicles for completed trips in the current month.
    """
    from trips.models import Trip

    now = timezone.now()
    trips = Trip.objects.filter(
        status="completed",
        start_time__month=now.month,
        start_time__year=now.year,
        end_time__isnull=False,
    )

    total_trip_seconds = sum(
        (t.end_time - t.start_time).total_seconds()
        for t in trips
        if t.start_time and t.end_time
    )

    from fleet.models import Vehicle
    vehicle_count = Vehicle.objects.exclude(status="retired").count()

    if vehicle_count == 0:
        return Decimal("0.00")

    # Available hours = vehicle_count * hours in month
    import calendar
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    total_available_seconds = vehicle_count * days_in_month * 24 * 3600

    utilization = (Decimal(str(total_trip_seconds)) /
                   Decimal(str(total_available_seconds))) * 100
    return round(utilization, 2)


def get_dashboard_kpis() -> dict:
    """
    Assembles all dashboard KPIs into a single dict for the context.
    Called once per dashboard request — not cached in this phase.
    """
    from fleet.models import Vehicle
    from drivers.models import Driver
    from trips.models import Trip

    vehicles = Vehicle.objects.all()

    return {
        "active_vehicles":      vehicles.filter(status="on_trip").count(),
        "available_vehicles":   vehicles.filter(status="available").count(),
        "in_maintenance":       vehicles.filter(status="in_shop").count(),
        "active_trips":         Trip.objects.filter(status="dispatched").count(),
        "pending_trips":        Trip.objects.filter(status="draft").count(),
        "drivers_on_duty":      Driver.objects.filter(status="on_trip").count(),
        "fleet_utilization":    get_fleet_utilization(),
    }
