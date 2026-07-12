from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


ROLES = (
    'Fleet Manager',
    'Driver',
    'Safety Officer',
    'Financial Analyst',
)


class Command(BaseCommand):
    help = 'Create the TransitOps RBAC groups.'

    def handle(self, *args, **options):
        for role_name in ROLES:
            _, created = Group.objects.get_or_create(name=role_name)
            status = 'Created' if created else 'Already exists'
            self.stdout.write(f'{status}: {role_name}')
