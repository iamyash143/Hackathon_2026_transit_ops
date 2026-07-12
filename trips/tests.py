from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from django_fsm import TransitionNotAllowed
from datetime import timedelta

from fleet.models import Vehicle, VehicleStatus
from drivers.models import Driver, DriverStatus
from finance.models import FuelLog
from trips.models import Trip, TripStatus
from trips.forms import TripCreateForm, TripCompleteForm

User = get_user_model()

class TripManagementTest(TestCase):
    def setUp(self):
        # Create groups/roles
        self.fleet_manager_group = Group.objects.create(name='Fleet Manager')
        self.driver_group = Group.objects.create(name='Driver')
        self.safety_officer_group = Group.objects.create(name='Safety Officer')
        self.financial_analyst_group = Group.objects.create(name='Financial Analyst')

        # Create users
        self.fleet_manager = User.objects.create_user(email='manager@example.com', password='password123')
        self.fleet_manager.groups.add(self.fleet_manager_group)

        self.driver_user = User.objects.create_user(email='driver@example.com', password='password123')
        self.driver_user.groups.add(self.driver_group)

        self.safety_officer = User.objects.create_user(email='safety@example.com', password='password123')
        self.safety_officer.groups.add(self.safety_officer_group)

        self.financial_analyst = User.objects.create_user(email='finance@example.com', password='password123')
        self.financial_analyst.groups.add(self.financial_analyst_group)

        self.regular_user = User.objects.create_user(email='regular@example.com', password='password123')

        # Create eligible vehicle
        self.vehicle = Vehicle.objects.create(
            registration_number='VAN-01',
            name='Delivery Van 1',
            vehicle_type='Van',
            max_load_capacity=1000.00,
            odometer=5000,
            acquisition_cost=300000.00,
            status=VehicleStatus.AVAILABLE
        )

        # Create eligible driver
        self.driver = Driver.objects.create(
            name='John Doe',
            license_number='LIC-123',
            license_category='C',
            license_expiry=timezone.now().date() + timedelta(days=365),
            contact_number='driver@example.com',  # Matched to driver_user.email for role filtering
            status=DriverStatus.AVAILABLE,
            safety_score=95
        )

    def test_trip_dispatch_locks_vehicle_and_driver(self):
        # Create a draft trip
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source='Warehouse A',
            destination='Retail Store B',
            cargo_weight=500.00,
            planned_distance=150.00,
            status=TripStatus.DRAFT
        )

        # Dispatch
        trip.dispatch()
        trip.save()

        # Reload objects from DB to verify statuses
        trip = Trip.objects.get(pk=trip.pk)
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.driver = Driver.objects.get(pk=self.driver.pk)

        self.assertEqual(trip.status, TripStatus.DISPATCHED)
        self.assertEqual(self.vehicle.status, VehicleStatus.ON_TRIP)
        self.assertEqual(self.driver.status, DriverStatus.ON_TRIP)
        self.assertIsNotNone(trip.start_time)

    def test_cargo_exceeds_capacity_blocks_dispatch(self):
        # Create a draft trip exceeding vehicle capacity (1000.00 kg)
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source='Warehouse A',
            destination='Retail Store B',
            cargo_weight=1200.00,
            planned_distance=150.00,
            status=TripStatus.DRAFT
        )

        with self.assertRaises(TransitionNotAllowed):
            trip.dispatch()

    def test_unavailable_vehicle_blocks_dispatch(self):
        # Make vehicle In Shop
        self.vehicle.send_to_maintenance()
        self.vehicle.save()

        # Create a draft trip
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source='Warehouse A',
            destination='Retail Store B',
            cargo_weight=500.00,
            planned_distance=150.00,
            status=TripStatus.DRAFT
        )

        with self.assertRaises(TransitionNotAllowed):
            trip.dispatch()

    def test_unavailable_driver_blocks_dispatch(self):
        # Suspend driver
        self.driver.suspend()
        self.driver.save()

        # Create a draft trip
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source='Warehouse A',
            destination='Retail Store B',
            cargo_weight=500.00,
            planned_distance=150.00,
            status=TripStatus.DRAFT
        )

        with self.assertRaises(TransitionNotAllowed):
            trip.dispatch()

    def test_expired_license_blocks_dispatch(self):
        # Expire license
        self.driver.license_expiry = timezone.now().date() - timedelta(days=1)
        self.driver.save()

        # Create a draft trip
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source='Warehouse A',
            destination='Retail Store B',
            cargo_weight=500.00,
            planned_distance=150.00,
            status=TripStatus.DRAFT
        )

        with self.assertRaises(TransitionNotAllowed):
            trip.dispatch()

    def test_trip_complete_updates_odometer_creates_fuellog_restores_status(self):
        # Create a trip and dispatch it
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source='Warehouse A',
            destination='Retail Store B',
            cargo_weight=500.00,
            planned_distance=150.00,
            status=TripStatus.DRAFT
        )
        trip.dispatch()
        trip.save()

        # Complete the trip
        trip.final_odometer = 5200
        trip.fuel_consumed = 40.00
        trip.fuel_cost = 4200.00  # Stored on object temporarily

        trip.complete()
        trip.save()

        # Reload objects from DB
        trip = Trip.objects.get(pk=trip.pk)
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.driver = Driver.objects.get(pk=self.driver.pk)

        self.assertEqual(trip.status, TripStatus.COMPLETED)
        self.assertEqual(self.vehicle.odometer, 5200)
        self.assertEqual(self.vehicle.status, VehicleStatus.AVAILABLE)
        self.assertEqual(self.driver.status, DriverStatus.AVAILABLE)
        self.assertIsNotNone(trip.end_time)

        # Check if FuelLog was created
        fuel_log = FuelLog.objects.filter(trip=trip).first()
        self.assertIsNotNone(fuel_log)
        self.assertEqual(fuel_log.liters, 40.00)
        self.assertEqual(fuel_log.cost, 4200.00)

    def test_trip_cancel_restores_status(self):
        # Create a trip and dispatch it
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source='Warehouse A',
            destination='Retail Store B',
            cargo_weight=500.00,
            planned_distance=150.00,
            status=TripStatus.DRAFT
        )
        trip.dispatch()
        trip.save()

        # Cancel
        trip.cancel()
        trip.save()

        # Reload objects from DB
        trip = Trip.objects.get(pk=trip.pk)
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.driver = Driver.objects.get(pk=self.driver.pk)

        self.assertEqual(trip.status, TripStatus.CANCELLED)
        self.assertEqual(self.vehicle.status, VehicleStatus.AVAILABLE)
        self.assertEqual(self.driver.status, DriverStatus.AVAILABLE)

    def test_trip_create_form_dropdowns(self):
        # Create non-available vehicle
        vehicle_in_shop = Vehicle.objects.create(
            registration_number='VAN-02',
            name='Repairing Van',
            vehicle_type='Van',
            max_load_capacity=1000.00,
            odometer=6000,
            acquisition_cost=300000.00,
            status=VehicleStatus.IN_SHOP
        )

        # Create non-eligible driver (expired license)
        driver_expired = Driver.objects.create(
            name='Jane Doe',
            license_number='LIC-456',
            license_category='C',
            license_expiry=timezone.now().date() - timedelta(days=1),
            contact_number='jane@example.com',
            status=DriverStatus.AVAILABLE,
            safety_score=90
        )

        form = TripCreateForm()
        vehicle_queryset = list(form.fields['vehicle'].queryset)
        driver_queryset = list(form.fields['driver'].queryset)

        self.assertIn(self.vehicle, vehicle_queryset)
        self.assertNotIn(vehicle_in_shop, vehicle_queryset)

        self.assertIn(self.driver, driver_queryset)
        self.assertNotIn(driver_expired, driver_queryset)

    def test_complete_form_validation_rejects_lower_odometer(self):
        # Dispatch trip
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source='Warehouse A',
            destination='Retail Store B',
            cargo_weight=500.00,
            planned_distance=150.00,
            status=TripStatus.DISPATCHED
        )

        # Form with final_odometer equal to vehicle's current (5000) should fail
        form_data = {
            'final_odometer': 5000,
            'fuel_consumed': 25.00,
            'fuel_cost': 2500.00
        }
        form = TripCompleteForm(data=form_data, trip=trip)
        self.assertFalse(form.is_valid())
        self.assertIn('final_odometer', form.errors)

    def test_views_role_based_access(self):
        trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=self.driver,
            source='Warehouse A',
            destination='Retail Store B',
            cargo_weight=500.00,
            planned_distance=150.00,
            status=TripStatus.DRAFT
        )

        list_url = reverse('trips:trip_list')
        detail_url = reverse('trips:trip_detail', kwargs={'pk': trip.pk})
        create_url = reverse('trips:trip_create')
        dispatch_url = reverse('trips:trip_dispatch', kwargs={'pk': trip.pk})

        # --- Regular User (Unauthorized) ---
        self.client.login(email='regular@example.com', password='password123')
        self.assertEqual(self.client.get(list_url).status_code, 403)
        self.assertEqual(self.client.get(detail_url).status_code, 403)
        self.assertEqual(self.client.get(create_url).status_code, 403)
        self.assertEqual(self.client.post(dispatch_url).status_code, 403)
        self.client.logout()

        # --- Driver (Operational/Restricted List) ---
        self.client.login(email='driver@example.com', password='password123')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)
        # Should see the trip because driver's contact_number matches driver_user.email
        self.assertContains(response, 'Warehouse A')

        # Create another trip for a different driver
        other_driver = Driver.objects.create(
            name='Other Driver',
            license_number='LIC-999',
            license_category='C',
            license_expiry=timezone.now().date() + timedelta(days=100),
            contact_number='other@example.com',
            status=DriverStatus.AVAILABLE
        )
        other_trip = Trip.objects.create(
            vehicle=self.vehicle,
            driver=other_driver,
            source='Warehouse X',
            destination='Retail Store Y',
            cargo_weight=100.00,
            planned_distance=50.00,
            status=TripStatus.DRAFT
        )

        response = self.client.get(list_url)
        self.assertNotContains(response, 'Warehouse X')  # Excluded!
        self.client.logout()
