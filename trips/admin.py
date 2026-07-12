from django.contrib import admin
from .models import Trip

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display  = ('trip_id', 'vehicle', 'driver', 'source', 'destination',
                     'cargo_weight', 'status', 'start_time', 'end_time')
    list_filter   = ('status',)
    search_fields = ('vehicle__registration_number', 'driver__name', 'source', 'destination')
    readonly_fields = ('trip_id', 'status', 'start_time', 'end_time', 'created_at', 'updated_at')
