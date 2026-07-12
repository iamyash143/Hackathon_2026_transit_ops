from django.views.generic import CreateView, DetailView, ListView

from accounts.mixins import OperationalMixin, RoleRequiredMixin
from trips.forms import TripForm
from trips.models import Trip


class TripListView(RoleRequiredMixin, ListView):
    allowed_roles = ["Fleet Manager", "Driver", "Safety Officer", "Financial Analyst"]
    model = Trip
    template_name = "trips/trip_list.html"
    context_object_name = "trips"


class TripDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ["Fleet Manager", "Driver", "Safety Officer", "Financial Analyst"]
    model = Trip
    template_name = "trips/trip_detail.html"


class TripCreateView(OperationalMixin, CreateView):
    model = Trip
    form_class = TripForm
    template_name = "trips/trip_form.html"
