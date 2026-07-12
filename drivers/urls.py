from django.urls import path
from . import views

app_name = 'drivers'

urlpatterns = [
    path('', views.DriverListView.as_view(), name='driver_list'),
    path('<int:pk>/', views.DriverDetailView.as_view(), name='driver_detail'),
    path('new/', views.DriverCreateView.as_view(), name='driver_create'),
    path('<int:pk>/edit/', views.DriverUpdateView.as_view(), name='driver_update'),
    path('<int:pk>/suspend/', views.driver_suspend, name='driver_suspend'),
    path('<int:pk>/reinstate/', views.driver_reinstate, name='driver_reinstate'),
]
