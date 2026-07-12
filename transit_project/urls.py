"""URL configuration for the TransitOps project."""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound
from django.urls import include, path

from core import views as core_views


def unavailable_feature(request):
    """Return a safe response for a Phase 1 navigation placeholder."""
    return HttpResponseNotFound('This feature is not available yet.')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('documents/', include('documents.urls', namespace='documents')),
    path('vehicles/', include('fleet.urls', namespace='fleet')),
    path('', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('drivers/', include('drivers.urls', namespace='drivers')),
    path('finance/', unavailable_feature, name='finance_dashboard'),
    path('trips/', include('trips.urls', namespace='trips')),
    path('maintenance/', include('maintenance.urls', namespace='maintenance')),
    path('reports/', include('reports.urls', namespace='reports')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = 'accounts.views.permission_denied_view'
