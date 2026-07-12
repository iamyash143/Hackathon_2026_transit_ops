from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from drivers.models import Driver, DriverStatus

class DriverModelTest(TestCase):
    def setUp(self):
        self.driver = Driver.objects.create(
            name="Test Driver",
            license_number="LIC123",
            license_category="B",
            license_expiry=timezone.now().date() + timedelta(days=60),
            contact_number="123456789",
        )

    def test_eligible_query(self):
        # Driver is available and license is valid
        self.assertIn(self.driver, Driver.eligible())
        
        # Expired license
        self.driver.license_expiry = timezone.now().date() - timedelta(days=1)
        self.driver.save()
        self.assertNotIn(self.driver, Driver.eligible())
        
        # Reset and change status
        self.driver.license_expiry = timezone.now().date() + timedelta(days=60)
        self.driver.suspend()
        self.driver.save()
        self.assertNotIn(self.driver, Driver.eligible())

    def test_computed_properties(self):
        self.assertFalse(self.driver.license_is_expired)
        self.assertFalse(self.driver.license_expiring_soon)

        self.driver.license_expiry = timezone.now().date() + timedelta(days=10)
        self.driver.save()
        self.assertFalse(self.driver.license_is_expired)
        self.assertTrue(self.driver.license_expiring_soon)

        self.driver.license_expiry = timezone.now().date() - timedelta(days=1)
        self.driver.save()
        self.assertTrue(self.driver.license_is_expired)
        self.assertFalse(self.driver.license_expiring_soon)

    def test_fsm_transitions(self):
        self.assertEqual(self.driver.status, DriverStatus.AVAILABLE)
        
        self.driver.dispatch()
        self.assertEqual(self.driver.status, DriverStatus.ON_TRIP)

        self.driver.return_from_trip()
        self.assertEqual(self.driver.status, DriverStatus.AVAILABLE)

        self.driver.suspend()
        self.assertEqual(self.driver.status, DriverStatus.SUSPENDED)

        self.driver.reinstate()
        self.assertEqual(self.driver.status, DriverStatus.AVAILABLE)
