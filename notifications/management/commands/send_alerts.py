from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from drivers.models import Driver
from fleet.models import Vehicle
from maintenance.models import MaintenanceLog
from notifications.emails import (
    send_license_expiry_email,
    send_maintenance_due_email,
    send_maintenance_overdue_email,
)
from notifications.sms import send_sms
from notifications.models import NotificationLog


class Command(BaseCommand):
    help = "Send alerts for expiring licenses and maintenance due warnings."

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        self._check_license_expiry(today)
        self._check_maintenance_due()
        self._check_maintenance_overdue(today)
        self.stdout.write(self.style.SUCCESS("Alerts processed."))

    # ── License Expiry ────────────────────────────────────────────────────────

    def _check_license_expiry(self, today):
        warn_date     = today + timedelta(days=settings.LICENSE_WARN_DAYS)
        critical_date = today + timedelta(days=settings.LICENSE_CRITICAL_DAYS)

        expiring_drivers = Driver.objects.filter(
            license_expiry__lte=warn_date,
            license_expiry__gte=today,
        ).exclude(status="retired")  # Drivers don't retire but keeps filter clean

        for driver in expiring_drivers:
            days_remaining = (driver.license_expiry - today).days

            # De-duplicate: skip if already alerted in last 7 days
            already_sent = NotificationLog.objects.filter(
                driver=driver,
                alert_type__in=[
                    NotificationLog.ALERT_LICENSE_WARNING,
                    NotificationLog.ALERT_LICENSE_CRITICAL,
                ],
                sent_at__gte=timezone.now() - timedelta(days=7),
            ).exists()

            if already_sent:
                continue

            alert_type = (
                NotificationLog.ALERT_LICENSE_CRITICAL
                if days_remaining <= settings.LICENSE_CRITICAL_DAYS
                else NotificationLog.ALERT_LICENSE_WARNING
            )

            send_license_expiry_email(driver, days_remaining)
            NotificationLog.objects.create(
                alert_type=alert_type,
                driver=driver,
                channel="email",
            )
            self.stdout.write(f"  License alert sent: {driver} ({days_remaining} days)")

            # SMS for critical — send directly to driver
            if days_remaining <= settings.LICENSE_CRITICAL_DAYS and driver.contact_number:
                msg = (
                    f"URGENT: Your driving license expires in {days_remaining} days. "
                    f"Please renew immediately. — TransitOps"
                )
                if send_sms(driver.contact_number, msg):
                    NotificationLog.objects.create(
                        alert_type=alert_type,
                        driver=driver,
                        channel="sms",
                    )

    # ── Maintenance Due ───────────────────────────────────────────────────────

    def _check_maintenance_due(self):
        threshold = settings.MAINTENANCE_KM_THRESHOLD

        for vehicle in Vehicle.objects.exclude(status__in=["Retired", "In Shop"]):
            last_log = MaintenanceLog.objects.filter(
                vehicle=vehicle, status="closed"
            ).order_by("-date").first()

            last_service_odometer = last_log.odometer_at_service \
                if last_log and hasattr(last_log, "odometer_at_service") \
                else 0

            km_since = vehicle.odometer - last_service_odometer

            if km_since >= threshold:
                already_sent = NotificationLog.objects.filter(
                    vehicle=vehicle,
                    alert_type=NotificationLog.ALERT_MAINTENANCE_DUE,
                    sent_at__gte=timezone.now() - timedelta(days=7),
                ).exists()

                if already_sent:
                    continue

                send_maintenance_due_email(vehicle, km_since)
                NotificationLog.objects.create(
                    alert_type=NotificationLog.ALERT_MAINTENANCE_DUE,
                    vehicle=vehicle,
                    channel="email",
                )
                self.stdout.write(
                    f"  Maintenance due alert: {vehicle.registration_number} "
                    f"({km_since} km since service)"
                )

    # ── Maintenance Overdue ───────────────────────────────────────────────────

    def _check_maintenance_overdue(self, today):
        overdue_threshold = timedelta(days=settings.MAINTENANCE_OVERDUE_DAYS)

        open_logs = MaintenanceLog.objects.filter(
            status="open",
            date__lte=today - overdue_threshold,
        ).select_related("vehicle")

        for log in open_logs:
            days_in_shop = (today - log.date).days

            already_sent = NotificationLog.objects.filter(
                vehicle=log.vehicle,
                alert_type=NotificationLog.ALERT_MAINTENANCE_OVER,
                sent_at__gte=timezone.now() - timedelta(days=3),
            ).exists()

            if already_sent:
                continue

            send_maintenance_overdue_email(log.vehicle, days_in_shop)
            NotificationLog.objects.create(
                alert_type=NotificationLog.ALERT_MAINTENANCE_OVER,
                vehicle=log.vehicle,
                channel="email",
            )
            self.stdout.write(
                f"  Maintenance overdue: {log.vehicle.registration_number} "
                f"({days_in_shop} days in shop)"
            )
