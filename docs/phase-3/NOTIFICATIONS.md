# Notifications

## Goal

Deliver automated alerts for two critical operational events:

1. **Expiring driver licenses** — notify the Safety Officer when any driver's license
   expires within 30 days.
2. **Maintenance due warnings** — notify the Fleet Manager when a vehicle's odometer
   crosses a maintenance threshold since its last recorded service.

Alerts are sent via email (primary) and optionally SMS (bonus). Execution is triggered
by a Django management command scheduled via cron or Celery Beat.

---

## Scope

- A management command that queries for alert conditions and dispatches notifications.
- Email sending via `django-anymail` (SendGrid, Mailgun, or Postmark backend).
- Optional SMS via Twilio for high-priority maintenance alerts.
- An in-app notification flag on the dashboard (a simple DB flag, no WebSocket needed).
- No new models beyond an optional `Notification` log table.
- No real-time push — polling-based or scheduled execution only.

---

## Responsibilities

| Alert Type | Trigger Condition | Recipient | Channel |
|---|---|---|---|
| License Expiry Warning | `driver.license_expiry` ≤ today + 30 days | Safety Officer | Email |
| License Expiry Critical | `driver.license_expiry` ≤ today + 7 days | Safety Officer + Driver | Email + SMS |
| Maintenance Due | `vehicle.odometer - last_service_odometer` ≥ 15,000 km | Fleet Manager | Email |
| Maintenance Overdue | Vehicle `in_shop` for more than 7 days | Fleet Manager | Email |

---

## Django App

`notifications/` (create as a standalone app)

---

## Files to Create / Modify

```
notifications/
  __init__.py
  apps.py
  models.py            # CREATE — optional NotificationLog model
  emails.py            # CREATE — email builder functions
  sms.py               # CREATE — Twilio SMS helper (bonus)
  management/
    commands/
      send_alerts.py   # CREATE — main management command

# Settings
settings.py            # MODIFY — add Anymail config and Twilio credentials
```

---

## Dependencies

- `django-anymail` installed: `pip install django-anymail[sendgrid]` (or mailgun/postmark).
- `twilio` installed: `pip install twilio` (optional, for SMS).
- `Driver` model with `license_expiry` (DateField) and `contact_number` fields.
- `Vehicle` model with `odometer` field.
- `MaintenanceLog` model with `date` and `status` fields.
- `RBAC.md` — emails are sent to users in the `Safety Officer` and `Fleet Manager` groups.
- `STATUS_AUTOMATION.md` — maintenance flag state is used to determine overdue alerts.

---

## Business Rules

1. License expiry emails are sent only once per 7-day window per driver — avoid spam.
   Track last-sent date in `NotificationLog`.
2. Maintenance due threshold is fixed at **15,000 km** since last closed `MaintenanceLog`.
   If no prior log exists, calculate from vehicle acquisition odometer (treat as 0).
3. A `Suspended` driver still triggers a license expiry alert — the Safety Officer must be
   informed regardless of driver status.
4. Emails are sent to **all users in the target Group**, not a single hardcoded email address.
5. SMS is sent only when the alert is **critical** (≤ 7 days to expiry or active maintenance
   overdue). Standard 30-day warnings are email-only.
6. Do not send alerts for `Retired` vehicles.

---

## Implementation Steps

### Step 1 — Settings Configuration

```python
# settings.py

# --- Anymail (Email) ---
INSTALLED_APPS += ["anymail"]

EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
# Or: "anymail.backends.mailgun.EmailBackend"

ANYMAIL = {
    "SENDGRID_API_KEY": env("SENDGRID_API_KEY"),
}
DEFAULT_FROM_EMAIL = "transitops@yourdomain.com"

# --- Twilio (SMS — optional) ---
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN  = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", default="")

# --- Notification thresholds ---
LICENSE_WARN_DAYS          = 30
LICENSE_CRITICAL_DAYS      = 7
MAINTENANCE_KM_THRESHOLD   = 15000
MAINTENANCE_OVERDUE_DAYS   = 7
```

---

### Step 2 — Optional NotificationLog Model

```python
# notifications/models.py
from django.db import models
from drivers.models import Driver
from vehicles.models import Vehicle

class NotificationLog(models.Model):
    ALERT_LICENSE_WARNING  = "license_warning"
    ALERT_LICENSE_CRITICAL = "license_critical"
    ALERT_MAINTENANCE_DUE  = "maintenance_due"
    ALERT_MAINTENANCE_OVER = "maintenance_overdue"

    ALERT_TYPES = [
        (ALERT_LICENSE_WARNING,  "License Warning"),
        (ALERT_LICENSE_CRITICAL, "License Critical"),
        (ALERT_MAINTENANCE_DUE,  "Maintenance Due"),
        (ALERT_MAINTENANCE_OVER, "Maintenance Overdue"),
    ]

    alert_type  = models.CharField(max_length=30, choices=ALERT_TYPES)
    driver      = models.ForeignKey(Driver, null=True, blank=True,
                                    on_delete=models.SET_NULL)
    vehicle     = models.ForeignKey(Vehicle, null=True, blank=True,
                                    on_delete=models.SET_NULL)
    sent_at     = models.DateTimeField(auto_now_add=True)
    channel     = models.CharField(max_length=10,
                                    choices=[("email", "Email"), ("sms", "SMS")])
    recipient   = models.EmailField(blank=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.alert_type} | {self.sent_at:%Y-%m-%d}"
```

---

### Step 3 — Email Builder

```python
# notifications/emails.py
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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
```

---

### Step 4 — SMS Helper (Bonus)

```python
# notifications/sms.py
from django.conf import settings


def send_sms(to_number: str, message: str) -> bool:
    """
    Sends an SMS via Twilio. Returns True on success, False on failure.
    Gracefully skips if Twilio credentials are not configured.
    """
    if not all([
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN,
        settings.TWILIO_FROM_NUMBER,
    ]):
        return False

    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_FROM_NUMBER,
            to=to_number,
        )
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Twilio SMS failed: {e}")
        return False
```

---

### Step 5 — Management Command

```python
# notifications/management/commands/send_alerts.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

from drivers.models import Driver
from vehicles.models import Vehicle
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

        for vehicle in Vehicle.objects.exclude(status__in=["retired", "in_shop"]):
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
```

---

### Step 6 — Schedule Execution

**Option A — Cron (simple, no Celery):**
```cron
# Run daily at 08:00
0 8 * * * cd /path/to/project && python manage.py send_alerts >> /var/log/transitops/alerts.log 2>&1
```

**Option B — Celery Beat (if Celery is already configured):**
```python
# settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "send-daily-alerts": {
        "task": "notifications.tasks.run_send_alerts",
        "schedule": crontab(hour=8, minute=0),
    },
}
```

```python
# notifications/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def run_send_alerts():
    call_command("send_alerts")
```

---

## Success Scenario

1. Driver Alex has a license expiring in 20 days. Running `python manage.py send_alerts`
   sends one email to all Safety Officers. A `NotificationLog` record is created.
2. Running the command again 3 days later — no duplicate email sent (de-duplication check passes).
3. A vehicle has traveled 16,200 km since its last oil change. Fleet Manager receives a
   "Maintenance Due" email. Vehicle is still `available` (no automatic status change — Fleet Manager acts manually).
4. A maintenance log has been open for 9 days. Fleet Manager receives a "Maintenance Overdue" alert.
5. Twilio credentials are missing in `.env`. SMS block executes silently without raising an exception.

---

## Definition of Done

- [ ] `send_alerts` management command runs without errors on a clean database.
- [ ] License expiry emails are sent to all users in the `Safety Officer` group — not a hardcoded address.
- [ ] De-duplication logic prevents the same alert from being sent more than once per 7-day window.
- [ ] `NotificationLog` records are created for every dispatched alert.
- [ ] SMS sends only for critical alerts (≤ 7 days) and fails silently if Twilio is not configured.
- [ ] Retired vehicles are excluded from all maintenance alert queries.
- [ ] Cron entry or Celery Beat task is documented and tested.

---

## AI Instructions

- Always fetch recipient emails by Group name using `_get_group_emails()` — never hardcode addresses.
- The `send_alerts` command must be idempotent — running it twice on the same day must not send duplicate emails. Check `NotificationLog` before dispatching.
- Wrap all email and SMS send calls in `try/except` — a failed Twilio call must not abort the entire command run.
- If `MaintenanceLog` does not have an `odometer_at_service` field, add it to the model as a `PositiveIntegerField(default=0)` and include it in the migration — this is a small model addition, not a redesign.
- Use `send_mail()` from `django.core.mail` — Anymail transparently handles routing to the configured ESP backend. Do not import provider-specific clients directly in `emails.py`.
- When testing locally without real credentials, set `EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"` in dev settings — emails will print to stdout.
