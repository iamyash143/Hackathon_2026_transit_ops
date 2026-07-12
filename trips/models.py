import uuid
from django.db import models
from django.utils import timezone
from django_fsm import FSMField, transition
from fleet.models import Vehicle
from drivers.models import Driver

class TripStatus(models.TextChoices):
    DRAFT      = 'Draft',      'Draft'
    DISPATCHED = 'Dispatched', 'Dispatched'
    COMPLETED  = 'Completed',  'Completed'
    CANCELLED  = 'Cancelled',  'Cancelled'

class Trip(models.Model):
    trip_id         = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    vehicle         = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='trips')
    driver          = models.ForeignKey(Driver,  on_delete=models.PROTECT, related_name='trips')
    source          = models.CharField(max_length=200)
    destination     = models.CharField(max_length=200)
    cargo_weight    = models.DecimalField(max_digits=8, decimal_places=2)     # kg
    planned_distance = models.DecimalField(max_digits=8, decimal_places=2)    # km
    start_time      = models.DateTimeField(null=True, blank=True)
    end_time        = models.DateTimeField(null=True, blank=True)
    final_odometer  = models.PositiveIntegerField(null=True, blank=True)      # km; set on completion
    fuel_consumed   = models.DecimalField(max_digits=8, decimal_places=2,
                                          null=True, blank=True)              # litres; set on completion
    status          = FSMField(default=TripStatus.DRAFT, protected=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Trip {str(self.trip_id)[:8]} — {self.source} → {self.destination}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('trips:trip_detail', kwargs={'pk': self.pk})

    # ── FSM conditions ───────────────────────────────────────────────────────

    def _cargo_within_capacity(self):
        return self.cargo_weight <= self.vehicle.max_load_capacity

    def _vehicle_available(self):
        from fleet.models import VehicleStatus
        return self.vehicle.status == VehicleStatus.AVAILABLE

    def _driver_eligible(self):
        from drivers.models import DriverStatus
        return (
            self.driver.status == DriverStatus.AVAILABLE
            and not self.driver.license_is_expired
        )

    # ── FSM transitions ──────────────────────────────────────────────────────

    @transition(
        field=status,
        source=TripStatus.DRAFT,
        target=TripStatus.DISPATCHED,
        conditions=[_cargo_within_capacity, _vehicle_available, _driver_eligible],
    )
    def dispatch(self):
        self.start_time = timezone.now()
        self.vehicle.dispatch()
        self.vehicle.save()
        self.driver.dispatch()
        self.driver.save()

    @transition(
        field=status,
        source=TripStatus.DISPATCHED,
        target=TripStatus.COMPLETED,
    )
    def complete(self):
        """
        Caller must set self.final_odometer and self.fuel_consumed before calling.
        Validation of those values happens in the view / form, not here.
        """
        from django.apps import apps
        self.end_time = timezone.now()

        # Update vehicle odometer
        self.vehicle.odometer = self.final_odometer
        self.vehicle.return_from_trip()
        self.vehicle.save()

        # Restore driver
        self.driver.return_from_trip()
        self.driver.save()

        # Create fuel log
        FuelLog = apps.get_model('finance', 'FuelLog')
        FuelLog.objects.create(
            vehicle=self.vehicle,
            trip=self,
            liters=self.fuel_consumed,
            cost=getattr(self, 'fuel_cost', 0) or 0,
            date=timezone.now().date(),
        )

    @transition(
        field=status,
        source=TripStatus.DISPATCHED,
        target=TripStatus.CANCELLED,
    )
    def cancel(self):
        self.vehicle.return_from_trip()
        self.vehicle.save()
        self.driver.return_from_trip()
        self.driver.save()
