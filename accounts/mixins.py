from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

class RoleRequiredMixin(LoginRequiredMixin):
    """
    Add `allowed_roles = ['Fleet Manager', 'Driver']` to any CBV.
    Superusers always pass.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return response          # LoginRequiredMixin already redirected
        if request.user.is_superuser:
            return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)
        if self.allowed_roles and request.user.role not in self.allowed_roles:
            raise PermissionDenied
        return response

# Convenience subclasses — import these in feature views
class FleetManagerMixin(RoleRequiredMixin):
    allowed_roles = ['Fleet Manager']

class DriverMixin(RoleRequiredMixin):
    allowed_roles = ['Driver']

class SafetyOfficerMixin(RoleRequiredMixin):
    allowed_roles = ['Safety Officer']

class FinancialAnalystMixin(RoleRequiredMixin):
    allowed_roles = ['Financial Analyst']

class OperationalMixin(RoleRequiredMixin):
    """Fleet Manager + Driver — for shared operational views."""
    allowed_roles = ['Fleet Manager', 'Driver']
