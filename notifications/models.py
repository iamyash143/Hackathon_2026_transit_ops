from django.db import models
from drivers.models import Driver
from fleet.models import Vehicle

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
