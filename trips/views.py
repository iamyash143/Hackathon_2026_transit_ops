from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView
from django_fsm import TransitionNotAllowed

from accounts.decorators import role_required
from accounts.mixins import OperationalMixin, RoleRequiredMixin
from trips.forms import TripCompleteForm, TripForm
from trips.models import Trip, TripStatus


class TripListView(RoleRequiredMixin, ListView):
    allowed_roles = ["Fleet Manager", "Driver", "Safety Officer", "Financial Analyst"]
    model = Trip
    template_name = "trips/trip_list.html"
    context_object_name = "trips"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("vehicle", "driver")
        if self.request.user.role == "Driver":
            queryset = queryset.filter(driver__contact_number=self.request.user.email)
        status = self.request.GET.get("status")
        return queryset.filter(status=status) if status else queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "")
        context["status_choices"] = TripStatus.choices
        return context


class TripDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ["Fleet Manager", "Driver", "Safety Officer", "Financial Analyst"]
    model = Trip
    template_name = "trips/trip_detail.html"
    context_object_name = "trip"


class TripCreateView(OperationalMixin, CreateView):
    model = Trip
    form_class = TripForm
    template_name = "trips/trip_form.html"

    def get_success_url(self):
        return reverse("trips:trip_detail", kwargs={"pk": self.object.pk})


@role_required("Fleet Manager", "Driver")
def trip_dispatch(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    if request.method == "POST":
        try:
            with transaction.atomic():
                trip.dispatch()
                trip.save()
            messages.success(request, "Trip dispatched — vehicle and driver are now On Trip.")
        except (TransitionNotAllowed, ValidationError):
            messages.error(request, "Dispatch failed: check cargo weight, vehicle, and driver availability.")
    return redirect("trips:trip_detail", pk=pk)


@role_required("Fleet Manager", "Driver")
def trip_complete(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    if trip.status == TripStatus.COMPLETED:
        messages.warning(request, "This trip is already completed.")
        return redirect("trips:trip_detail", pk=pk)

    form = TripCompleteForm(request.POST or None, trip=trip)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                trip.fuel_cost = form.cleaned_data["fuel_cost"]
                trip.complete(
                    final_odometer=form.cleaned_data["final_odometer"],
                    fuel_consumed=form.cleaned_data["fuel_consumed"],
                )
                trip.save()
            messages.success(request, "Trip completed. Vehicle and driver are Available.")
            return redirect("trips:trip_detail", pk=pk)
        except (TransitionNotAllowed, ValidationError):
            messages.error(request, "Could not complete trip.")
    return render(request, "trips/trip_complete_form.html", {"trip": trip, "form": form})


@role_required("Fleet Manager")
def trip_cancel(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    if request.method == "POST":
        try:
            with transaction.atomic():
                trip.cancel()
                trip.save()
            messages.warning(request, "Trip cancelled. Vehicle and driver restored to Available.")
        except (TransitionNotAllowed, ValidationError):
            messages.error(request, "Only dispatched trips can be cancelled.")
    return redirect("trips:trip_detail", pk=pk)
