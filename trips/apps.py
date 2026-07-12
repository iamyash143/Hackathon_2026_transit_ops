from django.apps import AppConfig

class TripsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trips'

    def ready(self):
        try:
            import trips.signals  # noqa
        except ImportError:
            pass
