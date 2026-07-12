# Authentication

## Goal

Implement secure, email-based authentication with Role-Based Access Control (RBAC) so every view can be protected by role and every template can branch on `user_role`.

## Scope

- Custom `User` model using email as the primary identifier
- Email + password login / logout
- Four RBAC groups: Fleet Manager, Driver, Safety Officer, Financial Analyst
- Reusable permission decorators and mixins for view protection
- Login page UI (styled with Tailwind / Flowbite)
- Permission-denied (403) page

## Responsibilities

**Owner:** Phase 1 lead (same developer as `PROJECT_SETUP.md`).  
Other developers consume the mixins and decorators — they do not modify `accounts`.

## Django App

`accounts`

## Files to Create / Modify

```
accounts/
├── __init__.py
├── apps.py
├── models.py           # Custom User model
├── backends.py         # Email authentication backend
├── forms.py            # EmailAuthenticationForm
├── views.py            # LoginView, LogoutView
├── urls.py
├── mixins.py           # RoleRequiredMixin, role-specific mixins
├── decorators.py       # @role_required, convenience wrappers
└── templates/
    └── accounts/
        ├── login.html
        └── 403.html

transitops/urls.py      # include('accounts.urls')
transitops/settings/base.py
    AUTHENTICATION_BACKENDS, AUTH_USER_MODEL, LOGIN_URL, LOGIN_REDIRECT_URL
```

## Dependencies

- `PROJECT_SETUP.md` must be complete (`AUTH_USER_MODEL` set, migrations run)
- `BASE_UI.md` base template must exist before login page is styled (coordinate timing or stub it first)

## Business Rules

- Only authenticated users may access any view except `/login/`.
- A user belongs to exactly one group (their role). `request.user.groups.first()` is the canonical way to read it.
- Superusers bypass all role checks (Django default behaviour — keep it).
- No view in any feature app should roll its own auth check; always use the shared mixins/decorators.
- `is_verified` flag is reserved for future email-verification flows; enforce it as `True` for all seed users.

## Implementation Steps

### 1. Custom User model

`accounts/models.py`:

```python
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)

class User(AbstractUser):
    username = None                         # drop username
    email = models.EmailField(unique=True)
    is_verified = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def role(self):
        group = self.groups.first()
        return group.name if group else None
```

### 2. Authentication backend

Django's default backend authenticates by `username`. Register a custom backend to use `email`.

`accounts/backends.py`:

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

class EmailBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
```

`settings/base.py`:

```python
AUTHENTICATION_BACKENDS = ['accounts.backends.EmailBackend']
```

### 3. Login form and views

`accounts/forms.py`:

```python
from django import forms

class EmailLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput)
```

`accounts/views.py`:

```python
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from .forms import EmailLoginForm

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = EmailLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
        )
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        form.add_error(None, 'Invalid email or password.')
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')
```

`accounts/urls.py`:

```python
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
```

### 4. RBAC mixins and decorators

`accounts/mixins.py` — used by all class-based views across every feature app:

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

class RoleRequiredMixin(LoginRequiredMixin):
    """
    Add `allowed_roles = ['Fleet Manager', 'Driver']` to any CBV.
    Superusers always pass.
    """
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return response          # LoginRequiredMixin already redirected
        if request.user.is_superuser:
            return super(LoginRequiredMixin, self).dispatch(request, *args, **kwargs)
        if self.allowed_roles and request.user.role not in self.allowed_roles:
            raise PermissionDenied
        return response

# Convenience subclasses — import these in feature views
class FleetManagerMixin(RoleRequiredMixin):
    allowed_roles = ['Fleet Manager']

class DriverMixin(RoleRequiredMixin):
    allowed_roles = ['Driver']

class SafetyOfficerMixin(RoleRequiredMixin):
    allowed_roles = ['Safety Officer']

class FinancialAnalystMixin(RoleRequiredMixin):
    allowed_roles = ['Financial Analyst']

class OperationalMixin(RoleRequiredMixin):
    """Fleet Manager + Driver — for shared operational views."""
    allowed_roles = ['Fleet Manager', 'Driver']
```

`accounts/decorators.py` — used by function-based views:

```python
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapped
    return decorator

# Convenience wrappers
fleet_manager_required = role_required('Fleet Manager')
driver_required = role_required('Driver')
safety_officer_required = role_required('Safety Officer')
financial_analyst_required = role_required('Financial Analyst')
```

### 5. 403 handler

`transitops/urls.py`:

```python
handler403 = 'accounts.views.permission_denied_view'
```

`accounts/views.py` (add):

```python
def permission_denied_view(request, exception=None):
    return render(request, 'accounts/403.html', status=403)
```

`accounts/templates/accounts/403.html` — extend `base.html`, show role and a back link.

### 6. Login page template

`accounts/templates/accounts/login.html`:

```html
{% extends "base_auth.html" %}
{% load crispy_forms_tags %}

{% block content %}
<div class="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
  <div class="w-full max-w-md p-8 bg-white rounded-xl shadow dark:bg-gray-800">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      TransitOps
    </h1>
    <form method="post" novalidate>
      {% csrf_token %}
      {{ form|crispy }}
      {% if form.non_field_errors %}
        <p class="text-sm text-red-500 mt-2">{{ form.non_field_errors.0 }}</p>
      {% endif %}
      <button type="submit"
        class="w-full mt-4 text-white bg-blue-600 hover:bg-blue-700 font-medium rounded-lg text-sm px-5 py-2.5">
        Sign in
      </button>
    </form>
  </div>
</div>
{% endblock %}
```

`base_auth.html` — a minimal layout without sidebar (used only for login/403). Detailed in `BASE_UI.md`.

## Success Scenario

1. Visit `http://localhost:8000/` → redirected to `/login/`
2. Submit wrong credentials → inline error, no crash
3. Submit correct credentials → redirected to `/dashboard/`
4. Access a role-protected view with the wrong role → `403.html` rendered
5. Superuser bypasses all role checks

## Definition of Done

- [ ] `accounts.User` is the `AUTH_USER_MODEL`; `username` field does not exist
- [ ] `python manage.py createsuperuser` prompts for email, not username
- [ ] Login with email + password works; wrong credentials show an inline error
- [ ] `RoleRequiredMixin` and `role_required` decorator both raise 403 for the wrong role
- [ ] Superuser passes all role checks
- [ ] `FleetManagerMixin`, `DriverMixin`, `SafetyOfficerMixin`, `FinancialAnalystMixin` are importable from `accounts.mixins`
- [ ] `/login/` page is styled with Tailwind / Flowbite, responsive on mobile

## AI Instructions

- `AUTH_USER_MODEL` must be declared in settings before `makemigrations`. Never change it after the first migration without a full DB reset.
- `AbstractUser` already has `first_name`, `last_name`, `is_active`, `is_staff`, `is_superuser`, `date_joined` — do not redefine them.
- Use `request.user.groups.first()` to read the role. Do not use `request.user.groups.filter(name=...).exists()` in views — use the mixins/decorators instead.
- The `EmailBackend` must be in `AUTHENTICATION_BACKENDS`; without it, `authenticate(email=...)` silently returns `None`.
- Do not add model-level `Permission` assignments to `accounts` — that is Phase 2's job once feature models exist.
- `base_auth.html` is a standalone layout with no sidebar. Import it only for login and 403. All feature views extend `base.html` (defined in `BASE_UI.md`).
- The `role` property on `User` returns `None` for superusers with no group. All role checks must guard against `None`.
