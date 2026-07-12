from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from fleet.models import Vehicle, VehicleStatus

class MaintenanceStatus(models.TextChoices):
    OPEN   = 'Open',   'Open'
    CLOSED = 'Closed', 'Closed'

class MaintenanceLog(models.Model):
    vehicle     = models.ForeignKey(Vehicle, on_delete=models.PROTECT,
                                    related_name='maintenance_logs')
    date        = models.DateField()
    description = models.TextField()
    cost        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status      = models.CharField(max_length=10,
                                   choices=MaintenanceStatus.choices,
                                   default=MaintenanceStatus.OPEN)
    retire_on_close = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Maintenance [{self.status}] — {self.vehicle} — {self.date}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('maintenance:maintenance_detail', kwargs={'pk': self.pk})

# ── Signals ──────────────────────────────────────────────────────────────────

@receiver(post_save, sender=MaintenanceLog)
def handle_maintenance_status_change(sender, instance, created, **kwargs):
    vehicle = instance.vehicle

    if created and instance.status == MaintenanceStatus.OPEN:
        # New open log → lock vehicle
        if vehicle.status == VehicleStatus.AVAILABLE:
            vehicle.send_to_maintenance()
            vehicle.save()

    elif not created and instance.status == MaintenanceStatus.CLOSED:
        # Log closed → restore or retire vehicle
        if vehicle.status == VehicleStatus.IN_SHOP:
            if instance.retire_on_close:
                vehicle.retire()
            else:
                vehicle.complete_maintenance()
            vehicle.save()

# ── Predictive Maintenance Alert (post_save on Trip) ──────────────────────────

ODOMETER_SERVICE_INTERVAL = 15000  # km between oil changes

def check_maintenance_threshold(sender, instance, **kwargs):
    """Flag vehicles that have exceeded the service interval since last maintenance."""
    try:
        from trips.models import TripStatus
    except ImportError:
        # trips app is not available/installed on this branch
        return

    if instance.status != TripStatus.COMPLETED:
        return

    vehicle = instance.vehicle
    if not hasattr(vehicle, 'maintenance_due'):
        return

    last_closed = MaintenanceLog.objects.filter(
        vehicle=vehicle, status=MaintenanceStatus.CLOSED
    ).order_by('-updated_at').first()

    # If no prior service log exists, default to 0
    last_service_odometer = last_closed.vehicle.odometer if last_closed else 0
    if vehicle.odometer - last_service_odometer >= ODOMETER_SERVICE_INTERVAL:
        vehicle.maintenance_due = True
        vehicle.save(update_fields=['maintenance_due'])

# Connect dynamically to avoid system checks failing if 'trips' app is not in INSTALLED_APPS
from django.conf import settings
if 'trips' in settings.INSTALLED_APPS:
    post_save.connect(check_maintenance_threshold, sender='trips.Trip')
