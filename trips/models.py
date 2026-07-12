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
        if self.vehicle_id and self.cargo_weight > self.vehicle.max_load_capacity:
            raise ValidationError(
                f"Cargo weight ({self.cargo_weight} kg) exceeds vehicle maximum "
                f"load capacity ({self.vehicle.max_load_capacity} kg)."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("trips:trip_detail", kwargs={"pk": self.pk})

    @transition(field=status, source=TripStatus.DRAFT, target=TripStatus.DISPATCHED)
    def dispatch(self):
        """Dispatch a valid trip and mark the assigned vehicle and driver unavailable."""
        if self.vehicle.status != VehicleStatus.AVAILABLE:
            raise ValidationError("Only available vehicles can be dispatched.")
        if self.driver.status != DriverStatus.AVAILABLE:
            raise ValidationError("Only available drivers can be dispatched.")
        if self.driver.license_expiry < timezone.now().date():
            raise ValidationError("Drivers with expired licenses cannot be dispatched.")
        self.clean()
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

    @transition(field=status, source=TripStatus.DISPATCHED, target=TripStatus.CANCELLED)
    def cancel(self):
        """Cancel a dispatched trip and release the assigned vehicle and driver."""
        with transaction.atomic():
            self.end_time = timezone.now()
            self.vehicle.return_from_trip()
            self.driver.return_from_trip()
            self.vehicle.save()
            self.driver.save()
