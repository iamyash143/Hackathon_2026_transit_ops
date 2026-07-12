# Document Management

## Goal
Implement a document registry allowing upload and tracking of compliance credentials (e.g., driver licenses, vehicle insurance, and registration documents) with automatic validation and expiry warnings.

## Scope
- Multi-file type upload engine (PDF, PNG, JPG) with strict file size limits.
- Expiration monitoring system linking files to specific vehicles or drivers.
- File upload interfaces integrated into existing Vehicle and Driver profile views.
- Automatic driver suspension triggers when critical documents expire.

## Responsibilities
- **Safety Officer**: Upload, view, and verify driver credentials and registration documents.
- **Fleet Manager**: Upload and review vehicle insurance and registration certificates.
- **Driver**: Read and download their own uploaded files.

## Django App(s)
`documents` (or modular components inside `fleet` and `drivers`)

## Files to Create / Modify
```
documents/
  __init__.py
  apps.py             # App configuration
  models.py           # Document model definition
  validators.py       # Custom file format and size validators
  views.py            # Upload, delete, and list views
  urls.py             # Document routing
  templates/
    documents/
      upload_modal.html # HTMX form for adding new files
      document_list.html # Document catalog layout
```

## Dependencies
- Phase 2 `fleet` and `drivers` models.
- Phase 1 media storage configuration in `settings.py` (`MEDIA_URL`, `MEDIA_ROOT`).

## Business Rules
1. **Format Validation**: Only `.pdf`, `.png`, `.jpg`, and `.jpeg` file extensions are permitted.
2. **File Size Boundary**: Upload size must not exceed 5MB. Enforce this check during form clean methods and at the model validator level.
3. **Automatic Driver Status Update**: If a driver's active license document expires, a signal must trigger updating the `Driver.status` field to `suspended`. This automatically locks them out of trip dispatch selections (Phase 3 FSM compatibility).
4. **Document Expiration Window**: Any document expiring within 30 days must be highlighted in red with a "Warning" tag on the dashboard.

## Implementation Steps

### Step 1 — Write File Validators
```python
# documents/validators.py
import os
from django.core.exceptions import ValidationError

def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1]
    valid_extensions = ['.pdf', '.png', '.jpg', '.jpeg']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension. Allowed: PDF, PNG, JPG.')

def validate_file_size(value):
    limit = 5 * 1024 * 1024  # 5MB
    if value.size > limit:
        raise ValidationError('File size too large. Maximum size is 5MB.')
```

### Step 2 — Define the Document Model
```python
# documents/models.py
from django.db import models
from django.utils import timezone
from .validators import validate_file_extension, validate_file_size

class Document(models.Model):
    CATEGORY_CHOICES = [
        ("license", "Driver License"),
        ("insurance", "Vehicle Insurance"),
        ("registration", "Vehicle Registration"),
    ]

    title = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    file = models.FileField(
        upload_to="fleet_docs/",
        validators=[validate_file_extension, validate_file_size]
    )
    expiry_date = models.DateField()
    
    # Optional relationships to link documents to entities
    vehicle = models.ForeignKey('fleet.Vehicle', on_delete=models.CASCADE, null=True, blank=True, related_name="documents")
    driver = models.ForeignKey('drivers.Driver', on_delete=models.CASCADE, null=True, blank=True, related_name="documents")

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def is_expiring_soon(self):
        warning_window = timezone.now().date() + timezone.timedelta(days=30)
        return timezone.now().date() <= self.expiry_date <= warning_window
```

### Step 3 — Write the Upload View
```python
# documents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Document
from .forms import DocumentForm  # Simple ModelForm for Document

@login_required
def upload_document(request):
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()
            # If the category is driver license, trigger safety check
            if document.category == "license" and document.driver:
                document.driver.check_license_validity() # Helper to evaluate FSM status
            return redirect("documents:list")
    else:
        form = DocumentForm()
    return render(request, "documents/upload_modal.html", {"form": form})
```

## Success Scenario
1. Safety Officer opens the profile of driver "Alex".
2. Safety Officer uploads a scanned driving license (PDF format, 2MB).
3. The server saves the file, reads the expiry date (one year from today), and associates it with "Alex".
4. The document is flagged as "Valid", keeping "Alex" eligible for trip dispatches.

## Definition of Done
- [ ] Custom validation checks prevent non-image/non-PDF files from uploading.
- [ ] File size validation rejects assets larger than 5MB with a user-friendly error.
- [ ] Expiration checkers change document status styles automatically.
- [ ] Expired license status updates the associated driver to `suspended` status.
- [ ] Files upload to `/media/fleet_docs/` safely with secure random filenames.

## AI Instructions
- Store files using secure Django upload paths (`upload_to="fleet_docs/%Y/%m/%d/"`) to prevent collisions.
- Always include `enctype="multipart/form-data"` in all HTML form tags handling uploads.
- Implement soft delete or cascading options to handle file cleanup on disk when models are deleted using Django's `post_delete` signal.
