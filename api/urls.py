from django.urls import path
from .views import api_status

urlpatterns = [
    path('status/', api_status, name='api-status'),
]
