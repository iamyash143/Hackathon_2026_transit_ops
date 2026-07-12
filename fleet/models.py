from django.db import models

class Vehicle(models.Model):
    registration_number = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    odometer = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, default='Available')

    def __str__(self):
        return self.registration_number
