from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from drivers.models import Driver, DriverStatus
from finance.models import ExpenseLog, ExpenseType, FuelLog
from fleet.models import Vehicle, VehicleStatus
from maintenance.models import MaintenanceLog, MaintenanceStatus
from trips.models import Trip, TripStatus


DEMO_USERS = (
    ("admin@transitops.local", "TransitOps", "Admin", None, True),
    ("manager@transitops.local", "Aarav", "Sharma", "Fleet Manager", False),
    ("driver@transitops.local", "Rohan", "Mehta", "Driver", False),
    ("safety@transitops.local", "Priya", "Nair", "Safety Officer", False),
    ("finance@transitops.local", "Neha", "Kapoor", "Financial Analyst", False),
)

DEMO_VEHICLES = (
    {
        "registration_number": "MH12AB4581",
        "name": "Pune Linehaul 12T",
        "vehicle_type": "Box Truck",
        "max_load_capacity": Decimal("12000.00"),
        "odometer": 48250,
        "acquisition_cost": Decimal("2850000.00"),
    },
    {
        "registration_number": "KA05MC7712",
        "name": "Bengaluru Urban Van",
        "vehicle_type": "Cargo Van",
        "max_load_capacity": Decimal("1800.00"),
        "odometer": 36120,
        "acquisition_cost": Decimal("980000.00"),
    },
    {
        "registration_number": "DL01TA4421",
        "name": "Delhi Shuttle Coach",
        "vehicle_type": "Mini Bus",
        "max_load_capacity": Decimal("3500.00"),
        "odometer": 72400,
        "acquisition_cost": Decimal("1950000.00"),
    },
    {
        "registration_number": "MH04TD1207",
        "name": "Mumbai Refrigerated 8T",
        "vehicle_type": "Refrigerated Truck",
        "max_load_capacity": Decimal("8000.00"),
        "odometer": 21980,
        "acquisition_cost": Decimal("3420000.00"),
    },
    {
        "registration_number": "RJ14GC9090",
        "name": "Jaipur Spare Pickup",
        "vehicle_type": "Pickup",
        "max_load_capacity": Decimal("1100.00"),
        "odometer": 15530,
        "acquisition_cost": Decimal("760000.00"),
    },
)

DEMO_DRIVERS = (
    {
        "license_number": "DL-MH-2018-45891",
        "name": "Rohan Mehta",
        "license_category": "HCV",
        "contact_number": "+91-98765-12001",
        "safety_score": 94,
        "license_expiry_days": 420,
    },
    {
        "license_number": "DL-KA-2020-77812",
        "name": "Meera Iyer",
        "license_category": "LMV",
        "contact_number": "+91-98765-12002",
        "safety_score": 89,
        "license_expiry_days": 24,
    },
    {
        "license_number": "DL-DL-2017-33021",
        "name": "Kabir Khan",
        "license_category": "Bus",
        "contact_number": "+91-98765-12003",
        "safety_score": 78,
        "license_expiry_days": 180,
    },
    {
        "license_number": "DL-RJ-2019-66210",
        "name": "Vikram Singh",
        "license_category": "LMV",
        "contact_number": "+91-98765-12004",
        "safety_score": 61,
        "license_expiry_days": -12,
    },
)

DEMO_TRIPS = (
    {
        "trip_id": UUID("11111111-1111-4111-8111-111111111111"),
        "vehicle": "MH12AB4581",
        "driver": "DL-MH-2018-45891",
        "source": "Pune Warehouse",
        "source_lat": Decimal("18.520430"),
        "source_lng": Decimal("73.856743"),
        "destination": "Nashik Distribution Hub",
        "destination_lat": Decimal("19.997454"),
        "destination_lng": Decimal("73.789803"),
        "cargo_weight": Decimal("7200.00"),
        "planned_distance": Decimal("212.00"),
        "final_odometer_delta": 214,
        "fuel_consumed": Decimal("34.50"),
        "fuel_cost": Decimal("3312.00"),
        "expense_type": ExpenseType.TOLL,
        "expense_amount": Decimal("940.00"),
        "expense_notes": "Mumbai-Pune expressway and state tolls.",
        "complete": True,
    },
    {
        "trip_id": UUID("22222222-2222-4222-8222-222222222222"),
        "vehicle": "KA05MC7712",
        "driver": "DL-KA-2020-77812",
        "source": "Bengaluru Depot",
        "source_lat": Decimal("12.971599"),
        "source_lng": Decimal("77.594566"),
        "destination": "Mysuru Retail Cluster",
        "destination_lat": Decimal("12.295810"),
        "destination_lng": Decimal("76.639381"),
        "cargo_weight": Decimal("980.00"),
        "planned_distance": Decimal("146.00"),
        "final_odometer_delta": 148,
        "fuel_consumed": Decimal("18.20"),
        "fuel_cost": Decimal("1747.00"),
        "expense_type": ExpenseType.PARKING,
        "expense_amount": Decimal("180.00"),
        "expense_notes": "Market unloading bay parking.",
        "complete": True,
    },
    {
        "trip_id": UUID("33333333-3333-4333-8333-333333333333"),
        "vehicle": "MH04TD1207",
        "driver": "DL-KA-2020-77812",
        "source": "Mumbai Cold Storage",
        "source_lat": Decimal("19.076090"),
        "source_lng": Decimal("72.877426"),
        "destination": "Surat Pharma Hub",
        "destination_lat": Decimal("21.170240"),
        "destination_lng": Decimal("72.831062"),
        "cargo_weight": Decimal("4200.00"),
        "planned_distance": Decimal("284.00"),
        "final_odometer_delta": 0,
        "fuel_consumed": None,
        "fuel_cost": None,
        "expense_type": ExpenseType.TOLL,
        "expense_amount": Decimal("1260.00"),
        "expense_notes": "Advance toll float for active cold-chain trip.",
        "complete": False,
    },
)


class Command(BaseCommand):
    help = "Create a realistic local demo dataset for TransitOps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="DemoPass2026!",
            help="Password assigned to all demo users. Default: DemoPass2026!",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        today = timezone.localdate()

        self._check_migrations_applied()
        call_command("seed_groups", verbosity=0)

        users = self._seed_users(password)
        vehicles = self._seed_vehicles()
        drivers = self._seed_drivers(today)
        self._seed_completed_and_active_trips(vehicles, drivers, today)
        self._seed_maintenance(vehicles, today)

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write("")
        self.stdout.write("Demo login accounts:")
        for email, _, _, role, is_admin in DEMO_USERS:
            label = "Admin" if is_admin else role
            self.stdout.write(f"  {label}: {email} / {password}")
        self.stdout.write("")
        self.stdout.write(
            "Passwords are hashed in the database, so you cannot view the original password later. "
            "Re-run this command or use `python manage.py changepassword <email>` to reset one."
        )
        self.stdout.write(
            f"Seeded {len(users)} users, {len(vehicles)} vehicles, and {len(drivers)} drivers."
        )

    def _seed_users(self, password):
        User = get_user_model()
        users = {}

        for email, first_name, last_name, role, is_admin in DEMO_USERS:
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_staff": is_admin,
                    "is_superuser": is_admin,
                    "is_verified": True,
                },
            )
            user.first_name = first_name
            user.last_name = last_name
            user.is_staff = is_admin
            user.is_superuser = is_admin
            user.is_verified = True
            user.set_password(password)
            user.save()

            user.groups.clear()
            if role:
                group = Group.objects.get(name=role)
                user.groups.add(group)

            users[email] = user

        return users

    def _seed_vehicles(self):
        vehicles = {}

        for data in DEMO_VEHICLES:
            vehicle, created = Vehicle.objects.get_or_create(
                registration_number=data["registration_number"],
                defaults=data,
            )
            if not created:
                for field, value in data.items():
                    if field not in {"registration_number", "odometer"}:
                        setattr(vehicle, field, value)
                vehicle.save()
            vehicles[vehicle.registration_number] = vehicle

        return vehicles

    def _seed_drivers(self, today):
        drivers = {}

        for data in DEMO_DRIVERS:
            license_expiry = today + timedelta(days=data["license_expiry_days"])
            driver, created = Driver.objects.get_or_create(
                license_number=data["license_number"],
                defaults={
                    "name": data["name"],
                    "license_category": data["license_category"],
                    "license_expiry": license_expiry,
                    "contact_number": data["contact_number"],
                    "safety_score": data["safety_score"],
                },
            )
            if not created:
                driver.name = data["name"]
                driver.license_category = data["license_category"]
                driver.license_expiry = license_expiry
                driver.contact_number = data["contact_number"]
                driver.safety_score = data["safety_score"]
                driver.save()
            drivers[driver.license_number] = driver

        expired_driver = drivers["DL-RJ-2019-66210"]
        if expired_driver.status in {DriverStatus.AVAILABLE, DriverStatus.OFF_DUTY}:
            expired_driver.suspend()
            expired_driver.save()

        return drivers

    def _seed_completed_and_active_trips(self, vehicles, drivers, today):
        for data in DEMO_TRIPS:
            vehicle = vehicles[data["vehicle"]]
            driver = drivers[data["driver"]]

            trip, _ = Trip.objects.get_or_create(
                trip_id=data["trip_id"],
                defaults={
                    "vehicle": vehicle,
                    "driver": driver,
                    "source": data["source"],
                    "source_lat": data["source_lat"],
                    "source_lng": data["source_lng"],
                    "destination": data["destination"],
                    "destination_lat": data["destination_lat"],
                    "destination_lng": data["destination_lng"],
                    "cargo_weight": data["cargo_weight"],
                    "planned_distance": data["planned_distance"],
                },
            )

            if trip.status == TripStatus.DRAFT:
                trip.dispatch()
                trip.save()
                if data["complete"]:
                    final_odometer = vehicle.odometer + data["final_odometer_delta"]
                    trip.complete(
                        final_odometer=final_odometer,
                        fuel_consumed=data["fuel_consumed"],
                    )
                    trip.save()

            ExpenseLog.objects.update_or_create(
                vehicle=vehicle,
                trip=trip,
                expense_type=data["expense_type"],
                date=today,
                defaults={
                    "amount": data["expense_amount"],
                    "notes": data["expense_notes"],
                },
            )

            if data["complete"] and data["fuel_consumed"] is not None:
                FuelLog.objects.update_or_create(
                    vehicle=vehicle,
                    trip=trip,
                    date=today,
                    defaults={
                        "liters": data["fuel_consumed"],
                        "cost": data["fuel_cost"],
                    },
                )

    def _seed_maintenance(self, vehicles, today):
        MaintenanceLog.objects.update_or_create(
            vehicle=vehicles["MH12AB4581"],
            date=today - timedelta(days=18),
            description="Preventive service: engine oil, brake inspection, and tire rotation.",
            defaults={
                "cost": Decimal("18400.00"),
                "status": MaintenanceStatus.CLOSED,
                "odometer_at_service": 48250,
            },
        )

        open_log, _ = MaintenanceLog.objects.update_or_create(
            vehicle=vehicles["DL01TA4421"],
            date=today,
            description="AC compressor fault and front suspension noise under inspection.",
            defaults={
                "cost": Decimal("0.00"),
                "status": MaintenanceStatus.OPEN,
                "odometer_at_service": 72400,
            },
        )
        if open_log.status == MaintenanceStatus.OPEN and open_log.vehicle.status == VehicleStatus.AVAILABLE:
            open_log.vehicle.send_to_maintenance()
            open_log.vehicle.save()

    def _check_migrations_applied(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if not plan:
            return

        migrations = ", ".join(f"{migration.app_label}.{migration.name}" for migration, _ in plan[:8])
        if len(plan) > 8:
            migrations = f"{migrations}, ..."

        raise CommandError(
            "Database migrations are not fully applied. "
            "Run `python manage.py migrate` first, then run `python manage.py seed_demo_data` again. "
            f"Unapplied migrations: {migrations}"
        )
