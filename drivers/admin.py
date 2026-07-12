from django.contrib import admin
from django.utils import timezone
from .models import Driver

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display  = ('name', 'license_number', 'license_category',
                     'license_expiry', 'safety_score', 'status')
    list_filter   = ('status', 'license_category')
    search_fields = ('name', 'license_number')
    readonly_fields = ('status', 'created_at', 'updated_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs # annotation can be added here if needed
