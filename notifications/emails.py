import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)
User = get_user_model()


def _get_group_emails(group_name: str) -> list[str]:
    """Return email addresses of all active users in the given group."""
    return list(
        User.objects.filter(
            groups__name=group_name,
            is_active=True,
        ).values_list("email", flat=True)
    )


def send_html_email(subject, recipients, template_name, context, text_content):
    if not recipients:
        return False
    try:
        html_content = render_to_string(template_name, context)
    except Exception:
        logger.exception("Failed to render email template %s", template_name)
        html_content = ""

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )
        if html_content:
            message.attach_alternative(html_content, "text/html")
        message.send()
        return True
    except Exception:
        logger.exception("Failed to send email alert")
        return False


def send_license_expiry_email(driver, days_remaining: int, document=None):
    recipients = list({driver_email for driver_email in [getattr(driver, "email", "")] if driver_email})
    safety_recipients = _get_group_emails("Safety Officer")
    if hasattr(driver, "user") and getattr(driver.user, "email", None):
        recipients.append(driver.user.email)
    recipients = list(dict.fromkeys(recipients + safety_recipients))

    subject = f"License Expiry Warning: {driver} expires in {days_remaining} days"
    text_content = (
        f"Driver: {driver}\n"
        f"License Number: {driver.license_number}\n"
        f"License Category: {driver.license_category}\n"
        f"Expiry Date: {document.expiry_date if document else driver.license_expiry}\n"
        f"Days Remaining: {days_remaining}\n\n"
        "Please renew and upload updated credentials in TransitOps."
    )
    return send_html_email(
        subject=subject,
        recipients=recipients,
        template_name="notifications/email/license_warning.html",
        context={
            "driver": driver,
            "document": document,
            "days_remaining": days_remaining,
        },
        text_content=text_content,
    )


def send_maintenance_due_email(vehicle, km_since_service: int):
    recipients = _get_group_emails("Fleet Manager")
    subject = f"Maintenance Due: {vehicle.registration_number}"
    text_content = (
        f"Vehicle: {vehicle.registration_number} - {vehicle.name}\n"
        f"Current Odometer: {vehicle.odometer} km\n"
        f"KM Since Last Service: {km_since_service} km\n"
        f"Threshold: {settings.MAINTENANCE_KM_THRESHOLD} km\n\n"
        "Schedule maintenance at your earliest convenience."
    )
    return send_html_email(
        subject=subject,
        recipients=recipients,
        template_name="notifications/email/maintenance_due.html",
        context={"vehicle": vehicle, "km_since_service": km_since_service},
        text_content=text_content,
    )


def send_maintenance_overdue_email(vehicle, days_in_shop: int):
    recipients = _get_group_emails("Fleet Manager")
    subject = f"Maintenance Overdue: {vehicle.registration_number} ({days_in_shop} days)"
    text_content = (
        f"Vehicle {vehicle.registration_number} has been in the shop for {days_in_shop} days.\n"
        "Please review the maintenance log and close or escalate the record."
    )
    return send_html_email(
        subject=subject,
        recipients=recipients,
        template_name="notifications/email/maintenance_overdue.html",
        context={"vehicle": vehicle, "days_in_shop": days_in_shop},
        text_content=text_content,
    )
