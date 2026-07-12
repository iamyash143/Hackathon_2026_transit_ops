from django.contrib import admin

from documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "vehicle", "driver", "expiry_date", "status_label")
    list_filter = ("category", "expiry_date")
    search_fields = ("title", "vehicle__registration_number", "driver__name")
