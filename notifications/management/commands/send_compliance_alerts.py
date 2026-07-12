from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from documents.models import Document
from notifications.emails import send_license_expiry_email
from notifications.models import NotificationLog
from notifications.sms import send_sms


class Command(BaseCommand):
    help = "Dispatch warning notifications for driver license documents expiring at 30, 15, and 5 days."

    def handle(self, *args, **options):
        today = timezone.now().date()
        reminder_days = getattr(settings, "LICENSE_REMINDER_DAYS", [30, 15, 5])
        processed = 0

        documents = (
            Document.objects.filter(
                category=Document.Category.LICENSE,
                driver__isnull=False,
                expiry_date__in=[today + timedelta(days=days) for days in reminder_days],
            )
            .select_related("driver")
            .order_by("expiry_date")
        )

        for document in documents:
            days_remaining = (document.expiry_date - today).days
            driver = document.driver
            alert_type = (
                NotificationLog.ALERT_LICENSE_CRITICAL
                if days_remaining <= 5
                else NotificationLog.ALERT_LICENSE_WARNING
            )
            message = (
                f"TransitOps: Your license document expires in {days_remaining} days. "
                "Please renew and upload updated credentials."
            )

            if self._should_send(driver, alert_type, "email"):
                if send_license_expiry_email(driver, days_remaining, document):
                    NotificationLog.objects.create(
                        alert_type=alert_type,
                        driver=driver,
                        channel="email",
                        recipient=self._driver_recipient(driver),
                    )
                    processed += 1

            if driver.contact_number and self._should_send(driver, alert_type, "sms"):
                if send_sms(driver.contact_number, message):
                    NotificationLog.objects.create(
                        alert_type=alert_type,
                        driver=driver,
                        channel="sms",
                        recipient=driver.contact_number,
                    )
                    processed += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {processed} compliance alerts."))

    def _should_send(self, driver, alert_type, channel):
        today = timezone.now().date()
        return not NotificationLog.objects.filter(
            driver=driver,
            alert_type=alert_type,
            channel=channel,
            sent_at__date=today,
        ).exists()

    def _driver_recipient(self, driver):
        if hasattr(driver, "user") and getattr(driver.user, "email", None):
            return driver.user.email
        return ""
