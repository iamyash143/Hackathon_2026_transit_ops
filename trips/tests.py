from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from drivers.models import Driver
from fleet.models import Vehicle
from trips.models import Trip


class TripTests(TestCase):
    def setUp(self):
        self.vehicle = Vehicle.objects.create(
            registration_number="TRK-001",
            name="Truck 1",
            vehicle_type="Heavy Truck",
            max_load_capacity=Decimal("500.00"),
            odometer=1000,
            acquisition_cost=Decimal("100000.00"),
        )
        self.driver = Driver.objects.create(
            name="Alex Driver",
            license_number="LIC-TRIP-001",
            license_category="C",
            license_expiry=timezone.now().date() + timedelta(days=90),
            contact_number="+15551234567",
        )

    def test_rejects_cargo_over_vehicle_capacity(self):
        trip = Trip(
            vehicle=self.vehicle,
            driver=self.driver,
            source="Delhi",
            destination="Noida",
            cargo_weight=Decimal("600.00"),
            planned_distance=Decimal("12.80"),
        )

        with self.assertRaises(ValidationError):
            trip.full_clean()

    def test_dispatch_sets_assets_on_trip(self):
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source="Delhi",
            destination="Noida",
            cargo_weight=Decimal("450.00"),
            planned_distance=Decimal("12.80"),
        )

        trip.dispatch()
        trip.save()
        self.vehicle.refresh_from_db()
        self.driver.refresh_from_db()

        self.assertEqual(trip.status, "dispatched")
        self.assertEqual(self.vehicle.status, "On Trip")
        self.assertEqual(self.driver.status, "On Trip")
