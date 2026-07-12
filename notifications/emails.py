from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


def _get_group_emails(group_name: str) -> list[str]:
    """Returns email addresses of all active users in the given group."""
    return list(
        User.objects.filter(
            groups__name=group_name,
            is_active=True,
        ).values_list("email", flat=True)
    )


def send_license_expiry_email(driver, days_remaining: int):
    recipients = _get_group_emails("Safety Officer")
    if not recipients:
        return

    severity = "⚠️ CRITICAL" if days_remaining <= settings.LICENSE_CRITICAL_DAYS \
               else "⚠️ Warning"

    subject = (
        f"{severity}: Driver {driver} — License Expires in {days_remaining} Days"
    )
    body = (
        f"Driver: {driver}\n"
        f"License Number: {driver.license_number}\n"
        f"License Category: {driver.license_category}\n"
        f"Expiry Date: {driver.license_expiry}\n"
        f"Days Remaining: {days_remaining}\n\n"
        f"Please take immediate action to renew this license."
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )


def send_maintenance_due_email(vehicle, km_since_service: int):
    recipients = _get_group_emails("Fleet Manager")
    if not recipients:
        return

    subject = f"🔧 Maintenance Due: {vehicle.registration_number}"
    body = (
        f"Vehicle: {vehicle.registration_number} — {vehicle.name}\n"
        f"Current Odometer: {vehicle.odometer} km\n"
        f"KM Since Last Service: {km_since_service} km\n"
        f"Threshold: {settings.MAINTENANCE_KM_THRESHOLD} km\n\n"
        f"Schedule maintenance at your earliest convenience."
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )


def send_maintenance_overdue_email(vehicle, days_in_shop: int):
    recipients = _get_group_emails("Fleet Manager")
    if not recipients:
        return

    subject = f"🚨 Maintenance Overdue: {vehicle.registration_number} ({days_in_shop} days)"
    body = (
        f"Vehicle {vehicle.registration_number} has been in the shop for {days_in_shop} days.\n"
        f"Please review the maintenance log and close or escalate the record."
    )

    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )
