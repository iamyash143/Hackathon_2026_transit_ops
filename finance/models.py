from django.db import models
from fleet.models import Vehicle

class ExpenseType(models.TextChoices):
    TOLL        = 'Toll',        'Toll'
    FINE        = 'Fine',        'Fine'
    PARKING     = 'Parking',     'Parking'
    REPAIR      = 'Repair',      'Repair'
    OTHER       = 'Other',       'Other'

class FuelLog(models.Model):
    vehicle    = models.ForeignKey(Vehicle, on_delete=models.PROTECT,
                                   related_name='fuel_logs')
    trip       = models.ForeignKey('trips.Trip', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='fuel_logs')
    liters     = models.DecimalField(max_digits=8, decimal_places=2)
    cost       = models.DecimalField(max_digits=10, decimal_places=2)
    date       = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fuel {self.liters}L — {self.vehicle} — {self.date}"

class ExpenseLog(models.Model):
    vehicle      = models.ForeignKey(Vehicle, on_delete=models.PROTECT,
                                     related_name='expense_logs')
    trip         = models.ForeignKey('trips.Trip', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='expense_logs')
    expense_type = models.CharField(max_length=20, choices=ExpenseType.choices)
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    date         = models.DateField()
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.expense_type} ₹{self.amount} — {self.vehicle} — {self.date}"

from django.db.models import Sum, Avg, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal

def vehicle_fuel_cost(vehicle):
    return FuelLog.objects.filter(vehicle=vehicle).aggregate(
        total=Coalesce(Sum('cost'), Decimal('0'), output_field=DecimalField())
    )['total']

def vehicle_maintenance_cost(vehicle):
    from maintenance.models import MaintenanceLog, MaintenanceStatus
    return MaintenanceLog.objects.filter(
        vehicle=vehicle, status=MaintenanceStatus.CLOSED
    ).aggregate(
        total=Coalesce(Sum('cost'), Decimal('0'), output_field=DecimalField())
    )['total']

def vehicle_total_operational_cost(vehicle):
    return vehicle_fuel_cost(vehicle) + vehicle_maintenance_cost(vehicle)

def vehicle_roi(vehicle, revenue=Decimal('0')):
    """
    ROI = (Revenue - (Maintenance Costs + Fuel Costs)) / Acquisition Cost
    Revenue is passed in — not stored in the system yet (Phase 5 extension).
    """
    if vehicle.acquisition_cost == 0:
        return Decimal('0')
    total_cost = vehicle_total_operational_cost(vehicle)
    return (revenue - total_cost) / vehicle.acquisition_cost

def fleet_fuel_efficiency():
    """
    Average fuel efficiency across all completed trips (km/L).
    Returns queryset of dicts with trip_id and efficiency.
    """
    from trips.models import Trip, TripStatus
    from django.db.models import F, ExpressionWrapper
    return (
        Trip.objects
        .filter(status=TripStatus.COMPLETED, fuel_consumed__gt=0)
        .annotate(efficiency=ExpressionWrapper(
            F('planned_distance') / F('fuel_consumed'),
            output_field=DecimalField(max_digits=8, decimal_places=2)
        ))
        .values('id', 'vehicle__registration_number', 'efficiency')
    )
