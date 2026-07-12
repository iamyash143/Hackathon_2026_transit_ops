from django.db import models
from django_fsm import FSMField, transition

from reports.metrics import (
    get_vehicle_fuel_cost,
    get_vehicle_fuel_efficiency,
    get_vehicle_maintenance_cost,
    get_vehicle_operational_cost,
    get_vehicle_roi,
)


class VehicleStatus(models.TextChoices):
    AVAILABLE = 'Available', 'Available'
    ON_TRIP = 'On Trip', 'On Trip'
    IN_SHOP = 'In Shop', 'In Shop'
    RETIRED = 'Retired', 'Retired'


class Vehicle(models.Model):
    registration_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=50)
    max_load_capacity = models.DecimalField(max_digits=8, decimal_places=2)  # kg
    odometer = models.PositiveIntegerField(default=0)  # km
    acquisition_cost = models.DecimalField(max_digits=12, decimal_places=2)
    status = FSMField(default=VehicleStatus.AVAILABLE, protected=True)
    maintenance_due = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.registration_number} — {self.name}"

    @transition(field=status, source=VehicleStatus.AVAILABLE, target=VehicleStatus.ON_TRIP)
    def dispatch(self):
        """Called by Trip FSM on dispatch. Do not call directly from views."""

    @transition(field=status, source=VehicleStatus.ON_TRIP, target=VehicleStatus.AVAILABLE)
    def return_from_trip(self):
        pass

    @transition(field=status, source=VehicleStatus.AVAILABLE, target=VehicleStatus.IN_SHOP)
    def send_to_maintenance(self):
        pass

    @transition(field=status, source=VehicleStatus.IN_SHOP, target=VehicleStatus.AVAILABLE)
    def complete_maintenance(self):
        pass

    @transition(
        field=status,
        source=[VehicleStatus.AVAILABLE, VehicleStatus.IN_SHOP],
        target=VehicleStatus.RETIRED,
    )
    def retire(self):
        pass

    @classmethod
    def dispatchable(cls):
        """Vehicles eligible for trip assignment."""
        return cls.objects.filter(status=VehicleStatus.AVAILABLE)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('fleet:vehicle_detail', kwargs={'pk': self.pk})

    @property
    def fuel_cost(self):
        return get_vehicle_fuel_cost(self)

    @property
    def maintenance_cost(self):
        return get_vehicle_maintenance_cost(self)

    @property
    def operational_cost(self):
        return get_vehicle_operational_cost(self)

    @property
    def fuel_efficiency(self):
        return get_vehicle_fuel_efficiency(self)

    @property
    def roi(self):
        return get_vehicle_roi(self)
