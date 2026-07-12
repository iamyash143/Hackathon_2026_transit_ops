from django.contrib import admin
from .models import FuelLog, ExpenseLog

@admin.register(FuelLog)
class FuelLogAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'trip', 'liters', 'cost', 'date')
    list_filter   = ('vehicle', 'date')
    search_fields = ('vehicle__registration_number',)
    readonly_fields = ('created_at',)

@admin.register(ExpenseLog)
class ExpenseLogAdmin(admin.ModelAdmin):
    list_display  = ('vehicle', 'trip', 'expense_type', 'amount', 'date')
    list_filter   = ('expense_type', 'vehicle')
    search_fields = ('vehicle__registration_number', 'notes')
    readonly_fields = ('created_at',)
