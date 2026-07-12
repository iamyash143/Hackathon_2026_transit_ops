from django.db.models.signals import post_save
from django.dispatch import receiver

from trips.models import Trip, TripStatus


@receiver(post_save, sender=Trip)
def on_trip_status_change(sender, instance, **kwargs):
    """Keep trip post-save behavior explicit for completed records."""
    if instance.status == TripStatus.COMPLETED:
        return
