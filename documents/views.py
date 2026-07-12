from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, ListView

from accounts.mixins import RoleRequiredMixin
from documents.forms import DocumentForm
from documents.models import Document
from drivers.models import Driver
from fleet.models import Vehicle


class DocumentListView(RoleRequiredMixin, ListView):
    allowed_roles = ["Fleet Manager", "Driver", "Safety Officer", "Financial Analyst"]
    model = Document
    template_name = "documents/document_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        queryset = Document.objects.select_related("vehicle", "driver")
        user_role = getattr(self.request.user, "role", None)
        if user_role == "Driver":
            driver = Driver.objects.filter(name=self.request.user.get_full_name()).first()
            if not driver:
                return queryset.none()
            queryset = queryset.filter(driver=driver)
        return queryset


class DocumentCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = ["Fleet Manager", "Safety Officer"]
    model = Document
    form_class = DocumentForm
    template_name = "documents/upload_modal.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        vehicle_pk = self.request.GET.get("vehicle")
        driver_pk = self.request.GET.get("driver")
        if vehicle_pk:
            kwargs["initial_vehicle"] = get_object_or_404(Vehicle, pk=vehicle_pk)
        if driver_pk:
            kwargs["initial_driver"] = get_object_or_404(Driver, pk=driver_pk)
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Document uploaded successfully.")
        return super().form_valid(form)


@login_required
def delete_document(request, pk):
    document = get_object_or_404(Document, pk=pk)
    user_role = getattr(request.user, "role", None)
    can_delete = request.user.is_superuser or user_role in {"Fleet Manager", "Safety Officer"}
    if not request.user.is_authenticated or not can_delete:
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    if request.method == "POST":
        document.delete()
        messages.success(request, "Document deleted.")
    return redirect("documents:document_list")
