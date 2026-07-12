from datetime import timedelta
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from documents.models import Document
from drivers.models import Driver, DriverStatus


class DocumentTests(TestCase):
    def setUp(self):
        self.driver = Driver.objects.create(
            name="Alex Driver",
            license_number="LIC-001",
            license_category="C",
            license_expiry=timezone.now().date() + timedelta(days=365),
            contact_number="+15551234567",
        )

    def test_rejects_unsupported_file_extension(self):
        uploaded_file = SimpleUploadedFile("license.exe", b"bad", content_type="application/octet-stream")
        document = Document(
            title="License",
            category=Document.Category.LICENSE,
            file=uploaded_file,
            expiry_date=timezone.now().date() + timedelta(days=365),
            driver=self.driver,
        )

        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_rejects_file_larger_than_five_mb(self):
        oversized = BytesIO(b"x" * ((5 * 1024 * 1024) + 1))
        uploaded_file = SimpleUploadedFile("license.pdf", oversized.read(), content_type="application/pdf")
        document = Document(
            title="License",
            category=Document.Category.LICENSE,
            file=uploaded_file,
            expiry_date=timezone.now().date() + timedelta(days=365),
            driver=self.driver,
        )

        with self.assertRaises(ValidationError):
            document.full_clean()

    def test_expired_license_document_suspends_driver(self):
        uploaded_file = SimpleUploadedFile("license.pdf", b"%PDF-1.4", content_type="application/pdf")
        Document.objects.create(
            title="Expired License",
            category=Document.Category.LICENSE,
            file=uploaded_file,
            expiry_date=timezone.now().date() - timedelta(days=1),
            driver=self.driver,
        )

        self.driver.refresh_from_db()
        self.assertEqual(self.driver.status, DriverStatus.SUSPENDED)
