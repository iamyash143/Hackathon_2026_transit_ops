from django.db import models
from fleet.models import Vehicle
from drivers.models import Driver

class Trip(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    source = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    planned_distance = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, default='draft')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    final_odometer = models.PositiveIntegerField(null=True, blank=True)
    fuel_consumed = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
