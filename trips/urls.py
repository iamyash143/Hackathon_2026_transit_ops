from django.urls import path

from trips import views

app_name = "trips"

urlpatterns = [
    path("", views.TripListView.as_view(), name="trip_list"),
    path("new/", views.TripCreateView.as_view(), name="trip_create"),
    path("<int:pk>/", views.TripDetailView.as_view(), name="trip_detail"),
]
