# CSV and PDF Exporting

## Goal
Provide a reliable exporting mechanism for platform records, generating standard CSV reports for tabular analysis and styled, print-ready PDF manifests for drivers and dispatchers.

## Scope
- CSV export endpoints for Vehicles and Financial Analytics datasets.
- PDF generation endpoint for individual Trip Manifests utilizing WeasyPrint.
- Filters and search state parameters persistence during export generation.
- Access restriction checks on download endpoints.

## Responsibilities
- **Fleet Manager & Driver**: Access to download and print PDF Trip Manifests.
- **Financial Analyst**: Access to export financial cost datasets to CSV.
- **Developer**: Set up WeasyPrint and clean print-media stylesheets.

## Django App(s)
`reports` or `trips`

## Files to Create / Modify
```
reports/
  views.py            # Add CSV export and PDF export handlers
  urls.py             # Add export URL routes
  templates/
    reports/
      pdf/
        trip_manifest.html # Print-optimized HTML template for WeasyPrint
```

## Dependencies
- WeasyPrint library (`weasyprint` python package).
- Phase 2 `trips` and `finance` models.
- System-level PDF library dependencies (such as Pango/cairo, standard on modern environments).

## Business Rules
1. **Filter Alignment**: CSV exports must honor the same query filters (vehicle type, status, region, search queries) that are active on the user's dashboard view.
2. **Formatting**: PDF manifests must match a professional layout format suitable for printing on standard A4 paper size.
3. **Data Security**: Financial CSV downloads must verify that the user possesses `Financial Analyst` permissions before generating the report file.
4. **Encoding**: CSV files must use UTF-8 encoding with a Byte Order Mark (BOM) to guarantee compatibility with Microsoft Excel.

## Implementation Steps

### Step 1 — Add Export URL Routing
Configure routes for the CSV and PDF download actions.
```python
# reports/urls.py
from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("export/csv/vehicles/", views.export_vehicles_csv, name="export_vehicles_csv"),
    path("trips/<uuid:trip_id>/pdf/", views.export_trip_manifest_pdf, name="export_trip_manifest"),
]
```

### Step 2 — Write CSV and PDF views
Implement Python standard `csv` output writer and `WeasyPrint` PDF renderer.
```python
# reports/views.py
import csv
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from trips.models import Trip
from vehicles.models import Vehicle

@login_required
def export_vehicles_csv(request):
    # Retrieve identical queryset filters
    vehicle_type = request.GET.get("vehicle_type")
    region = request.GET.get("region")

    vehicles = Vehicle.objects.exclude(status="retired")
    if vehicle_type:
        vehicles = vehicles.filter(type=vehicle_type)
    if region:
        vehicles = vehicles.filter(region=region)

    # Set up HTTP response headers
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="vehicles_report.csv"'

    writer = csv.writer(response)
    # Header row
    writer.writerow(["Registration Number", "Model", "Type", "Status", "Region", "Odometer"])

    # Write data rows
    for vehicle in vehicles:
        writer.writerow([
            vehicle.registration_number,
            vehicle.model,
            vehicle.get_type_display(),
            vehicle.get_status_display(),
            vehicle.region,
            vehicle.odometer,
        ])

    return response

@login_required
def export_trip_manifest_pdf(request, trip_id):
    from weasyprint import HTML

    trip = get_object_or_404(Trip, pk=trip_id)

    # Render HTML template to a string context
    html_string = render_to_string("reports/pdf/trip_manifest.html", {"trip": trip})

    # Initialize WeasyPrint document
    html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
    pdf_file = html.write_pdf()

    # Return as PDF attachment
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="manifest_{trip.pk}.pdf"'
    return response
```

### Step 3 — Create Print-optimized PDF Template
Add custom CSS stylesheet properties for page breaks and margins.
```html
<!-- reports/templates/reports/pdf/trip_manifest.html -->
<!DOCTYPE html>
<html>
<head>
  <style>
    @page {
      size: A4;
      margin: 20mm;
      @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 9pt;
      }
    }
    body {
      font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
      color: #333;
      line-height: 1.5;
    }
    .header {
      border-bottom: 2px solid #3B82F6;
      padding-bottom: 10px;
      margin-bottom: 20px;
    }
    .title {
      font-size: 24pt;
      font-weight: bold;
      color: #1E3A8A;
    }
    .grid {
      display: table;
      width: 100%;
      margin-bottom: 20px;
    }
    .row {
      display: table-row;
    }
    .col {
      display: table-cell;
      padding: 8px;
      border-bottom: 1px solid #E5E7EB;
    }
    .label {
      font-weight: bold;
      color: #4B5563;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="title">TransitOps Trip Manifest</div>
    <div>Generated: {% now "Y-m-d H:i" %}</div>
  </div>

  <div class="grid">
    <div class="row">
      <div class="col label">Trip ID:</div>
      <div class="col">{{ trip.pk }}</div>
    </div>
    <div class="row">
      <div class="col label">Vehicle:</div>
      <div class="col">{{ trip.vehicle.registration_number }} ({{ trip.vehicle.model }})</div>
    </div>
    <div class="row">
      <div class="col label">Driver:</div>
      <div class="col">{{ trip.driver.user.get_full_name }}</div>
    </div>
    <div class="row">
      <div class="col label">Source Location:</div>
      <div class="col">{{ trip.source }}</div>
    </div>
    <div class="row">
      <div class="col label">Destination Location:</div>
      <div class="col">{{ trip.destination }}</div>
    </div>
    <div class="row">
      <div class="col label">Planned Distance:</div>
      <div class="col">{{ trip.planned_distance }} km</div>
    </div>
  </div>
</body>
</html>
```

## Success Scenario
1. A Driver visits their active trip detail page.
2. Clicking "Download Manifest (PDF)" triggers the `export_trip_manifest` URL endpoint.
3. The server generates a PDF document and initiates the browser download action.
4. The downloaded PDF file contains exact trip details and displays correctly in a PDF reader.

## Definition of Done
- [ ] WeasyPrint generates valid, readable PDF documents.
- [ ] CSV file export supports exact filtering matching the reports page queryset.
- [ ] UTF-8 encoding with BOM prevents corruption of special characters in spreadsheet apps.
- [ ] Views enforce role-based validation before compilation begins.
- [ ] A4 margins, headers, and page counters are styled correctly on the PDF stylesheet.

## AI Instructions
- Use `base_url=request.build_absolute_uri("/")` when instantiating the WeasyPrint object so that local asset files (logos, styles) resolve correctly.
- Always write CSV responses with `charset="utf-8-sig"` to prevent Excel encoding rendering bugs.
- Design print styles without complex external CSS framework dependencies (like heavy Tailwind classes); write vanilla CSS rules inside PDF template tags to guarantee output fidelity.
