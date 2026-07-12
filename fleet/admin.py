from django.contrib import admin
from .models import Vehicle

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display  = ('registration_number', 'name', 'vehicle_type', 'status', 'odometer', 'acquisition_cost')
    list_filter   = ('status', 'vehicle_type')
    search_fields = ('registration_number', 'name')
    readonly_fields = ('status', 'created_at', 'updated_at')
