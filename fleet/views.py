from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from accounts.mixins import FleetManagerMixin, RoleRequiredMixin
from .models import Vehicle, VehicleStatus
from .forms import VehicleForm
from django.urls import reverse_lazy

class VehicleListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Vehicle
    template_name = 'fleet/vehicle_list.html'
    context_object_name = 'vehicles'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by('registration_number')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(registration_number__icontains=q) | \
                 qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = VehicleStatus.choices
        return ctx

class VehicleDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Vehicle
    template_name = 'fleet/vehicle_detail.html'

class VehicleCreateView(FleetManagerMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'fleet/vehicle_form.html'

    def get_success_url(self):
        return self.object.get_absolute_url()

class VehicleUpdateView(FleetManagerMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'fleet/vehicle_form.html'

    def get_success_url(self):
        return self.object.get_absolute_url()

def vehicle_retire(request, pk):
    """POST-only action. Fleet Manager only."""
    from accounts.decorators import fleet_manager_required
    
    # We apply the decorator manually here or let urls.py handle it.
    # To be safe, we decorate the logic.
    @fleet_manager_required
    def _retire(req):
        vehicle = get_object_or_404(Vehicle, pk=pk)
        if req.method == 'POST':
            vehicle.retire()
            vehicle.save()
            messages.success(req, f'{vehicle} has been retired.')
        return redirect('fleet:vehicle_list')
        
    return _retire(request)
