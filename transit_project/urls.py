"""URL configuration for the TransitOps project."""

from django.contrib import admin
from django.http import HttpResponseNotFound
from django.urls import include, path

from core import views as core_views


def unavailable_feature(request):
    """Return a safe response for a Phase 1 navigation placeholder."""
    return HttpResponseNotFound('This feature is not available yet.')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('vehicles/', include('fleet.urls', namespace='fleet')),
    path('', include('accounts.urls')),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    path('drivers/', include('drivers.urls', namespace='drivers')),
    path('finance/', unavailable_feature, name='finance_dashboard'),
    path('trips/', unavailable_feature, name='trip_list'),
    path('maintenance/', include('maintenance.urls', namespace='maintenance')),
    path('reports/', unavailable_feature, name='reports'),
]

handler403 = 'accounts.views.permission_denied_view'
