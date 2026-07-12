import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from documents.validators import validate_file_extension, validate_file_size
from drivers.models import Driver
from fleet.models import Vehicle


LICENSE_EXPIRY_WARNING_DAYS = 30


def compliance_document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"fleet_docs/{timezone.now():%Y/%m/%d}/{uuid.uuid4().hex}{extension}"


class Document(models.Model):
    """Compliance file attached to a driver or vehicle."""

    class Category(models.TextChoices):
        LICENSE = "license", "Driver License"
        INSURANCE = "insurance", "Vehicle Insurance"
        REGISTRATION = "registration", "Vehicle Registration"

    title = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=Category.choices)
    file = models.FileField(
        upload_to=compliance_document_upload_path,
        validators=[validate_file_extension, validate_file_size],
    )
    expiry_date = models.DateField()
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["expiry_date", "title"]

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    def clean(self):
        if bool(self.vehicle) == bool(self.driver):
            raise ValidationError("Attach each document to exactly one vehicle or driver.")
        if self.category == self.Category.LICENSE and not self.driver:
            raise ValidationError("Driver license documents must be attached to a driver.")
        if self.category in {self.Category.INSURANCE, self.Category.REGISTRATION} and not self.vehicle:
            raise ValidationError("Vehicle documents must be attached to a vehicle.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("documents:document_list")

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def is_expiring_soon(self):
        today = timezone.now().date()
        warning_limit = today + timezone.timedelta(days=LICENSE_EXPIRY_WARNING_DAYS)
        return today <= self.expiry_date <= warning_limit

    @property
    def status_label(self):
        if self.is_expired:
            return "Expired"
        if self.is_expiring_soon:
            return "Warning"
        return "Valid"
