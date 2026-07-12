from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.reports_overview, name="overview"),
    path("export/csv/vehicles/", views.export_vehicles_csv, name="export_vehicles_csv"),
    path("trips/<int:trip_id>/pdf/", views.export_trip_manifest_pdf, name="export_trip_manifest"),
]
