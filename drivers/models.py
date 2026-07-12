from django.db import models
from django.utils import timezone
from django_fsm import FSMField, transition

class DriverStatus(models.TextChoices):
    AVAILABLE  = 'available',  'Available'
    ON_TRIP    = 'on_trip',    'On Trip'
    OFF_DUTY   = 'off_duty',   'Off Duty'
    SUSPENDED  = 'suspended',  'Suspended'

class Driver(models.Model):
    name            = models.CharField(max_length=100)
    license_number  = models.CharField(max_length=50, unique=True, db_index=True)
    license_category = models.CharField(max_length=10)          # e.g. 'B', 'C', 'EC'
    license_expiry  = models.DateField()
    contact_number  = models.CharField(max_length=20)
    safety_score    = models.PositiveSmallIntegerField(default=100)  # 0–100
    status          = FSMField(default=DriverStatus.AVAILABLE, protected=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.license_number})"

    # ── Computed properties ──────────────────────────────────────────────────

    @property
    def license_is_expired(self):
        return self.license_expiry < timezone.now().date()

    @property
    def license_expiring_soon(self):
        delta = (self.license_expiry - timezone.now().date()).days
        return 0 <= delta <= 30

    # ── FSM transitions ──────────────────────────────────────────────────────

    @transition(field=status,
                source=DriverStatus.AVAILABLE,
                target=DriverStatus.ON_TRIP)
    def dispatch(self):
        """Called by Trip FSM. Validates license in the Trip model, not here."""
        pass

    @transition(field=status,
                source=DriverStatus.ON_TRIP,
                target=DriverStatus.AVAILABLE)
    def return_from_trip(self):
        pass

    @transition(field=status,
                source=[DriverStatus.AVAILABLE, DriverStatus.OFF_DUTY],
                target=DriverStatus.SUSPENDED)
    def suspend(self):
        pass

    @transition(field=status,
                source=DriverStatus.SUSPENDED,
                target=DriverStatus.AVAILABLE)
    def reinstate(self):
        pass

    @transition(field=status,
                source=[DriverStatus.AVAILABLE, DriverStatus.ON_TRIP],
                target=DriverStatus.OFF_DUTY)
    def go_off_duty(self):
        pass

    @transition(field=status,
                source=DriverStatus.OFF_DUTY,
                target=DriverStatus.AVAILABLE)
    def go_available(self):
        pass

    # ── Querysets ────────────────────────────────────────────────────────────

    @classmethod
    def eligible(cls):
        """Drivers eligible for trip assignment — Available + valid license."""
        return cls.objects.filter(
            status=DriverStatus.AVAILABLE,
            license_expiry__gte=timezone.now().date(),
        )

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('drivers:driver_detail', kwargs={'pk': self.pk})
