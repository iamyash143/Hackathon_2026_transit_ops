from django.contrib import admin
from .models import MaintenanceLog

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'date', 'description', 'cost', 'status', 'retire_on_close')
    list_filter   = ('status', 'date')
    search_fields = ('vehicle__registration_number', 'description')
    readonly_fields = ('created_at', 'updated_at')
