from django.db.models.signals import post_save
from django.dispatch import receiver

# We would normally import Trip from trips.models, but since we are mocking it on this branch:
# We will just write the function shell.
try:
    from trips.models import Trip
except ImportError:
    Trip = None

if Trip:
    @receiver(post_save, sender=Trip)
    def on_trip_status_change(sender, instance, **kwargs):
        """
        After a trip is saved in 'completed' state, the FuelLog is already
        created by Trip.complete(). No additional action is needed here in Phase 03.
        Dashboard queries are live — no cache to invalidate.
        Extend this signal in Phase 04 if caching or async chart refresh is added.
        """
        if instance.status == "completed":
            pass  # Hook point for future cache invalidation
