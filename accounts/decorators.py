from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapped
    return decorator

# Convenience wrappers
fleet_manager_required = role_required('Fleet Manager')
driver_required = role_required('Driver')
safety_officer_required = role_required('Safety Officer')
financial_analyst_required = role_required('Financial Analyst')
