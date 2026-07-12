from pathlib import Path

from django.core.exceptions import ValidationError


ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024


def validate_file_extension(value):
    extension = Path(value.name).suffix.lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError("Unsupported file extension. Allowed: PDF, PNG, JPG.")


def validate_file_size(value):
    if value.size > MAX_DOCUMENT_SIZE_BYTES:
        raise ValidationError("File size too large. Maximum size is 5MB.")
