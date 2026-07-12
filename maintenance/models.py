from django.db import models
from fleet.models import Vehicle

class MaintenanceLog(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=20, default='open')
    odometer_at_service = models.PositiveIntegerField(default=0)
