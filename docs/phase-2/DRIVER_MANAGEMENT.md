# Driver Management

## Goal

Maintain driver profiles with status lifecycle enforcement and license compliance tracking. Driver eligibility gates trip dispatch — expired or suspended drivers are permanently excluded from assignment.

## Scope

- `Driver` model with FSM-managed status and license fields
- Full CRUD: list, detail, create, edit (no hard delete — use Suspended / Off Duty)
- Status transitions: `Available ↔ On Trip`, `Available / On Trip → Off Duty`, `Any → Suspended`
- License expiry tracking with dashboard-visible warnings
- Django Admin with compliance filters
- RBAC: Safety Officer has full CRUD; Fleet Manager and Driver have read-only; Financial Analyst has read-only

## Responsibilities

**Owner:** Dev B  
Exposes: `Driver` model, `DriverStatus` choices, `eligible()` queryset, status transition methods  
Consumed by: `trips` (dispatch eligibility check)

## Django App

`drivers`

```bash
python manage.py startapp drivers
```

Register in `INSTALLED_APPS`: `'drivers'`

## Files to Create / Modify

```
drivers/
├── __init__.py
├── apps.py
├── models.py           # Driver model + FSM transitions
├── forms.py            # DriverForm (crispy-tailwind)
├── views.py            # List, Detail, Create, Update, Suspend/Reinstate actions
├── urls.py             # namespaced: app_name = 'drivers'
├── admin.py
└── templates/
    └── drivers/
        ├── driver_list.html
        ├── driver_detail.html
        └── driver_form.html

transitops/urls.py      # path('drivers/', include('drivers.urls', namespace='drivers'))
```

## Dependencies

- Phase 1 complete (`accounts.mixins`, `base.html`)
- No other Phase 2 app
- `trips` app will import `Driver` and `DriverStatus` — coordinate model field names before the `trips` developer begins

## Business Rules

- `license_number` is unique across the system
- Eligible for dispatch: `status == Available` AND `license_expiry >= today`
- Drivers with `status == Suspended` cannot be reinstated from the dispatch pool — only a Safety Officer can change this
- Drivers `On Trip` cannot be suspended mid-trip (enforce via FSM source guard)
- `safety_score` is an integer 0–100; validated at form level
- No hard deletes — Off Duty and Suspended are the terminal non-active states
- License expiry within 30 days triggers a warning indicator (UI badge); expiry < today blocks dispatch entirely

## Implementation Steps

### 1. Model

`drivers/models.py`:

```python
from django.db import models
from django.utils import timezone
from django_fsm import FSMField, transition

class DriverStatus(models.TextChoices):
    AVAILABLE  = 'Available',  'Available'
    ON_TRIP    = 'On Trip',    'On Trip'
    OFF_DUTY   = 'Off Duty',   'Off Duty'
    SUSPENDED  = 'Suspended',  'Suspended'

class Driver(models.Model):
    name            = models.CharField(max_length=100)
    license_number  = models.CharField(max_length=50, unique=True, db_index=True)
    license_category = models.CharField(max_length=10)          # e.g. 'B', 'C', 'EC'
    license_expiry  = models.DateField()
    contact_number  = models.CharField(max_length=20)
    safety_score    = models.PositiveSmallIntegerField(default=100)  # 0–100
    status          = FSMField(default=DriverStatus.AVAILABLE, protected=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.license_number})"

    # ── Computed properties ──────────────────────────────────────────────────

    @property
    def license_is_expired(self):
        return self.license_expiry < timezone.now().date()

    @property
    def license_expiring_soon(self):
        delta = (self.license_expiry - timezone.now().date()).days
        return 0 <= delta <= 30

    # ── FSM transitions ──────────────────────────────────────────────────────

    @transition(field=status,
                source=DriverStatus.AVAILABLE,
                target=DriverStatus.ON_TRIP)
    def dispatch(self):
        """Called by Trip FSM. Validates license in the Trip model, not here."""
        pass

    @transition(field=status,
                source=DriverStatus.ON_TRIP,
                target=DriverStatus.AVAILABLE)
    def return_from_trip(self):
        pass

    @transition(field=status,
                source=[DriverStatus.AVAILABLE, DriverStatus.OFF_DUTY],
                target=DriverStatus.SUSPENDED)
    def suspend(self):
        pass

    @transition(field=status,
                source=DriverStatus.SUSPENDED,
                target=DriverStatus.AVAILABLE)
    def reinstate(self):
        pass

    @transition(field=status,
                source=[DriverStatus.AVAILABLE, DriverStatus.ON_TRIP],
                target=DriverStatus.OFF_DUTY)
    def go_off_duty(self):
        pass

    @transition(field=status,
                source=DriverStatus.OFF_DUTY,
                target=DriverStatus.AVAILABLE)
    def go_available(self):
        pass

    # ── Querysets ────────────────────────────────────────────────────────────

    @classmethod
    def eligible(cls):
        """Drivers eligible for trip assignment — Available + valid license."""
        return cls.objects.filter(
            status=DriverStatus.AVAILABLE,
            license_expiry__gte=timezone.now().date(),
        )

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('drivers:driver_detail', kwargs={'pk': self.pk})
```

### 2. Form

`drivers/forms.py`:

```python
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit
from .models import Driver

class DriverForm(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            'name', 'license_number', 'license_category',
            'license_expiry', 'contact_number', 'safety_score',
        ]
        widgets = {
            'license_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_safety_score(self):
        score = self.cleaned_data['safety_score']
        if not (0 <= score <= 100):
            raise forms.ValidationError('Safety score must be between 0 and 100.')
        return score

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='w-full md:w-1/2'),
                Column('contact_number', css_class='w-full md:w-1/2'),
            ),
            Row(
                Column('license_number', css_class='w-full md:w-1/3'),
                Column('license_category', css_class='w-full md:w-1/3'),
                Column('license_expiry', css_class='w-full md:w-1/3'),
            ),
            'safety_score',
            Submit('submit', 'Save Driver',
                   css_class='text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5 mt-4'),
        )
```

### 3. Views

`drivers/views.py`:

```python
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from accounts.mixins import SafetyOfficerMixin, RoleRequiredMixin
from accounts.decorators import safety_officer_required
from .models import Driver, DriverStatus
from .forms import DriverForm

class DriverListView(RoleRequiredMixin, ListView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Driver
    template_name = 'drivers/driver_list.html'
    context_object_name = 'drivers'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by('name')
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(license_number__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['status_choices'] = DriverStatus.choices
        return ctx

class DriverDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = ['Fleet Manager', 'Driver', 'Safety Officer', 'Financial Analyst']
    model = Driver
    template_name = 'drivers/driver_detail.html'

class DriverCreateView(SafetyOfficerMixin, CreateView):
    model = Driver
    form_class = DriverForm
    template_name = 'drivers/driver_form.html'

class DriverUpdateView(SafetyOfficerMixin, UpdateView):
    model = Driver
    form_class = DriverForm
    template_name = 'drivers/driver_form.html'

@safety_officer_required
def driver_suspend(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.suspend()
        driver.save()
        messages.warning(request, f'{driver.name} has been suspended.')
    return redirect('drivers:driver_detail', pk=pk)

@safety_officer_required
def driver_reinstate(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.reinstate()
        driver.save()
        messages.success(request, f'{driver.name} has been reinstated.')
    return redirect('drivers:driver_detail', pk=pk)
```

### 4. URLs

`drivers/urls.py`:

```python
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
```

Register in `transitops/urls.py`:

```python
path('drivers/', include('drivers.urls', namespace='drivers')),
```

### 5. Admin

`drivers/admin.py`:

```python
from django.contrib import admin
from django.utils import timezone
from .models import Driver

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display  = ('name', 'license_number', 'license_category',
                     'license_expiry', 'safety_score', 'status')
    list_filter   = ('status', 'license_category')
    search_fields = ('name', 'license_number')
    readonly_fields = ('status', 'created_at', 'updated_at')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate_expiry_warning()  # optional enhancement
```

### 6. Templates (structure)

`driver_list.html` — Flowbite table with columns: Name, License #, Category, Expiry (badge: red if expired, amber if expiring soon, green otherwise), Safety Score, Status. Safety Officer sees Create button. Search and status filter with HTMX `hx-get` on input.

`driver_detail.html` — All fields. Safety Officer sees Suspend / Reinstate buttons (rendered conditionally based on current status). Show license expiry warning banner if `driver.license_expiring_soon` or `driver.license_is_expired`.

`driver_form.html` — Renders `{{ form|crispy }}`. Used for both create and edit.

**License expiry badge logic in templates:**
```html
{% if driver.license_is_expired %}
  <span class="bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded dark:bg-red-900 dark:text-red-300">
    Expired
  </span>
{% elif driver.license_expiring_soon %}
  <span class="bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded dark:bg-yellow-900 dark:text-yellow-300">
    Expiring Soon
  </span>
{% else %}
  <span class="bg-green-100 text-green-800 text-xs font-medium px-2.5 py-0.5 rounded dark:bg-green-900 dark:text-green-300">
    Valid
  </span>
{% endif %}
```

## Success Scenario

1. Safety Officer creates driver `Alex` with a valid license → status `Available`
2. Driver list shows `Alex` with a green `Valid` badge
3. Safety Officer suspends `Alex` → status becomes `Suspended`
4. `Driver.eligible()` queryset no longer returns `Alex`
5. Trip creation form (Phase 2 — Trip Management) cannot select `Alex`
6. Fleet Manager can view driver list and detail but sees no Suspend / Reinstate buttons

## Definition of Done

- [ ] `Driver` model migrated; `license_number` has a unique DB constraint
- [ ] All FSM transitions defined; `status` field is `protected=True`
- [ ] `Driver.eligible()` filters by `Available` AND `license_expiry >= today`
- [ ] `license_is_expired` and `license_expiring_soon` properties return correct booleans
- [ ] Safety Officer can create, edit, suspend, and reinstate drivers
- [ ] All other roles can view list and detail only — no mutation buttons rendered
- [ ] License expiry badge shows correct colour in the list view
- [ ] Django Admin shows status as read-only

## AI Instructions

- `Driver.eligible()` is the single source of truth consumed by the `trips` app. Never duplicate the filter logic in Trip views.
- `status` is `FSMField` with `protected=True` — the same rules as Vehicle apply. No direct assignment.
- The `suspend()` transition source excludes `ON_TRIP` intentionally — you cannot suspend a driver mid-trip. If this is needed operationally, complete the trip first.
- `license_expiry` validation belongs in the Trip FSM's condition, not in the Driver model. The Driver model only stores and exposes the date; the Trip decides whether to block dispatch.
- `safety_score` validation (0–100) is in the form only. Do not add a DB constraint — it would break admin bulk edits. The form guard is sufficient.
- The `trips` app imports `Driver` and `DriverStatus` from this app. Never create a circular import by importing `trips` models into `drivers`.
