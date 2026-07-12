from django.db import models

class Driver(models.Model):
    license_number = models.CharField(max_length=50)
    license_category = models.CharField(max_length=50)
    license_expiry = models.DateField()
    contact_number = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, default='Available')

    def __str__(self):
        return f"Driver {self.id}"
