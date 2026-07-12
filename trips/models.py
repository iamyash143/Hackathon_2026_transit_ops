import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django_fsm import FSMField, transition

from drivers.models import Driver, DriverStatus
from fleet.models import Vehicle, VehicleStatus


class TripStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    DISPATCHED = "dispatched", "Dispatched"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class Trip(models.Model):
    """Dispatch record linking a vehicle, driver, route, and cargo load."""

    trip_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="trips")
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT, related_name="trips")
    source = models.CharField(max_length=255)
    source_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    source_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination = models.CharField(max_length=255)
    destination_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    destination_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    cargo_weight = models.DecimalField(max_digits=8, decimal_places=2)
    planned_distance = models.DecimalField(max_digits=8, decimal_places=2)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    final_odometer = models.PositiveIntegerField(null=True, blank=True)
    fuel_consumed = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    status = FSMField(default=TripStatus.DRAFT, choices=TripStatus.choices, protected=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Trip {self.trip_id}"

    def clean(self):
        if self.cargo_weight and self.cargo_weight <= 0:
            raise ValidationError("Cargo weight must be greater than zero.")
        if self.planned_distance and self.planned_distance <= 0:
            raise ValidationError("Planned distance must be greater than zero.")

    def save(self, *args, **kwargs):
        # django-fsm protects direct status assignment; validating that field
        # reassigns its value internally and raises on otherwise valid saves.
        self.full_clean(exclude={"status"})
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("trips:trip_detail", kwargs={"pk": self.pk})

    def _cargo_within_capacity(self):
        return self.cargo_weight <= self.vehicle.max_load_capacity

    def _vehicle_available(self):
        return self.vehicle.status == VehicleStatus.AVAILABLE

    def _driver_eligible(self):
        return self.driver.status == DriverStatus.AVAILABLE and not self.driver.license_is_expired

    @transition(
        field=status,
        source=TripStatus.DRAFT,
        target=TripStatus.DISPATCHED,
        conditions=[_cargo_within_capacity, _vehicle_available, _driver_eligible],
    )
    def dispatch(self):
        """Dispatch a valid trip and mark the assigned vehicle and driver unavailable."""
        with transaction.atomic():
            self.start_time = timezone.now()
            self.vehicle.dispatch()
            self.driver.dispatch()
            self.vehicle.save()
            self.driver.save()

    @transition(field=status, source=TripStatus.DISPATCHED, target=TripStatus.COMPLETED)
    def complete(self, final_odometer=None, fuel_consumed=None):
        """Complete a dispatched trip and restore vehicle and driver availability."""
        if final_odometer is not None:
            self.final_odometer = final_odometer
        if fuel_consumed is not None:
            self.fuel_consumed = fuel_consumed
        if self.final_odometer is None:
            raise ValidationError("Final odometer is required to complete a trip.")
        with transaction.atomic():
            self.end_time = timezone.now()
            self.vehicle.odometer = self.final_odometer
            self.vehicle.return_from_trip()
            self.driver.return_from_trip()
            self.vehicle.save()
            self.driver.save()
            if self.fuel_consumed is not None:
                from finance.models import FuelLog

                FuelLog.objects.create(
                    vehicle=self.vehicle,
                    trip=self,
                    liters=self.fuel_consumed,
                    cost=getattr(self, "fuel_cost", 0) or 0,
                    date=timezone.now().date(),
                )

    @transition(field=status, source=TripStatus.DISPATCHED, target=TripStatus.CANCELLED)
    def cancel(self):
        """Cancel a dispatched trip and release the assigned vehicle and driver."""
        with transaction.atomic():
            self.end_time = timezone.now()
            self.vehicle.return_from_trip()
            self.driver.return_from_trip()
            self.vehicle.save()
            self.driver.save()
