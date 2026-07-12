from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from fleet.models import Vehicle, VehicleStatus
from maintenance.models import MaintenanceLog, MaintenanceStatus
from maintenance.forms import MaintenanceCreateForm, MaintenanceCloseForm

User = get_user_model()

class MaintenanceTest(TestCase):
    def setUp(self):
        # Create groups/roles
        self.fleet_manager_group = Group.objects.create(name='Fleet Manager')
        self.safety_officer_group = Group.objects.create(name='Safety Officer')
        self.financial_analyst_group = Group.objects.create(name='Financial Analyst')

        # Create users
        self.fleet_manager = User.objects.create_user(email='manager@example.com', password='password123')
        self.fleet_manager.groups.add(self.fleet_manager_group)

        self.safety_officer = User.objects.create_user(email='safety@example.com', password='password123')
        self.safety_officer.groups.add(self.safety_officer_group)

        self.financial_analyst = User.objects.create_user(email='finance@example.com', password='password123')
        self.financial_analyst.groups.add(self.financial_analyst_group)

        self.regular_user = User.objects.create_user(email='regular@example.com', password='password123')

        # Create a test vehicle
        self.vehicle = Vehicle.objects.create(
            registration_number='VAN-01',
            name='Delivery Van 1',
            vehicle_type='Van',
            max_load_capacity=1500.00,
            odometer=10000,
            acquisition_cost=250000.00,
            status=VehicleStatus.AVAILABLE
        )

    def test_create_maintenance_log_locks_vehicle(self):
        # Assert vehicle is initially Available
        self.assertEqual(self.vehicle.status, VehicleStatus.AVAILABLE)

        # Create an open maintenance log
        log = MaintenanceLog.objects.create(
            vehicle=self.vehicle,
            date='2026-07-12',
            description='Oil Change & Filter replacement',
            cost=2000.00,
            status=MaintenanceStatus.OPEN
        )

        # Reload vehicle and check status is now In Shop
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.assertEqual(self.vehicle.status, VehicleStatus.IN_SHOP)

    def test_close_maintenance_log_unlocks_vehicle(self):
        # Create an open maintenance log
        log = MaintenanceLog.objects.create(
            vehicle=self.vehicle,
            date='2026-07-12',
            description='Brake inspection',
            cost=1500.00,
            status=MaintenanceStatus.OPEN
        )
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.assertEqual(self.vehicle.status, VehicleStatus.IN_SHOP)

        # Close the maintenance log
        log.status = MaintenanceStatus.CLOSED
        log.cost = 1800.00  # Finalized cost
        log.save()

        # Reload vehicle and check status returns to Available
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.assertEqual(self.vehicle.status, VehicleStatus.AVAILABLE)

    def test_close_maintenance_log_retires_vehicle(self):
        # Create an open maintenance log
        log = MaintenanceLog.objects.create(
            vehicle=self.vehicle,
            date='2026-07-12',
            description='Engine overhaul',
            cost=50000.00,
            status=MaintenanceStatus.OPEN
        )
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.assertEqual(self.vehicle.status, VehicleStatus.IN_SHOP)

        # Close the log with retire_on_close=True
        log.status = MaintenanceStatus.CLOSED
        log.retire_on_close = True
        log.save()

        # Reload vehicle and check status is Retired
        self.vehicle = Vehicle.objects.get(pk=self.vehicle.pk)
        self.assertEqual(self.vehicle.status, VehicleStatus.RETIRED)

    def test_create_form_excludes_non_available_vehicles(self):
        # vehicle 1 is Available (from setUp)
        # vehicle 2 in Shop
        vehicle2 = Vehicle.objects.create(
            registration_number='VAN-02',
            name='Delivery Van 2',
            vehicle_type='Van',
            max_load_capacity=1500.00,
            odometer=20000,
            acquisition_cost=250000.00,
            status=VehicleStatus.IN_SHOP
        )

        form = MaintenanceCreateForm()
        queryset_vehicles = list(form.fields['vehicle'].queryset)

        self.assertIn(self.vehicle, queryset_vehicles)
        self.assertNotIn(vehicle2, queryset_vehicles)

    def test_form_validation_blocks_duplicate_open_log(self):
        # Create an open log
        log = MaintenanceLog.objects.create(
            vehicle=self.vehicle,
            date='2026-07-12',
            description='Tire rotation',
            cost=500.00,
            status=MaintenanceStatus.OPEN
        )

        # Try to validate a form to create another open log for same vehicle
        form_data = {
            'vehicle': self.vehicle.pk,
            'date': '2026-07-12',
            'description': 'Suspension repair',
            'cost': 1200.00
        }
        form = MaintenanceCreateForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('vehicle', form.errors)
        self.assertEqual(
            form.errors['vehicle'][0],
            f'{self.vehicle} already has an open maintenance record.'
        )

    def test_rbac_view_access(self):
        # Test client requests
        # Create an open log to detail/close
        log = MaintenanceLog.objects.create(
            vehicle=self.vehicle,
            date='2026-07-12',
            description='Regular service',
            cost=3000.00,
            status=MaintenanceStatus.OPEN
        )

        list_url = reverse('maintenance:maintenance_list')
        detail_url = reverse('maintenance:maintenance_detail', kwargs={'pk': log.pk})
        create_url = reverse('maintenance:maintenance_create')
        close_url = reverse('maintenance:maintenance_close', kwargs={'pk': log.pk})

        # --- Regular User (Unauthorized) ---
        self.client.login(email='regular@example.com', password='password123')
        
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 403) # Forbidden

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 403)

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(close_url, {'final_cost': 3500.00})
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # --- Safety Officer (Read-Only) ---
        self.client.login(email='safety@example.com', password='password123')
        
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(close_url, {'final_cost': 3500.00})
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # --- Financial Analyst (Read-Only) ---
        self.client.login(email='finance@example.com', password='password123')
        
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 403)

        response = self.client.post(close_url, {'final_cost': 3500.00})
        self.assertEqual(response.status_code, 403)
        self.client.logout()

        # --- Fleet Manager (Full Access) ---
        self.client.login(email='manager@example.com', password='password123')
        
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)

        # Close action
        response = self.client.post(close_url, {'final_cost': 3200.00, 'retire_on_close': False})
        self.assertEqual(response.status_code, 302) # Redirect to detail page
        
        # Verify the record is indeed closed and cost updated
        log.refresh_from_db()
        self.assertEqual(log.status, MaintenanceStatus.CLOSED)
        self.assertEqual(log.cost, 3200.00)
        self.client.logout()
