# Base UI

## Goal

Deliver a shared HTML shell — base template, sidebar navigation, dark mode toggle, and HTMX wiring — that every feature developer extends without touching CSS configuration.

## Scope

- Tailwind CSS v4 installation and build pipeline
- Flowbite component library setup
- HTMX loaded globally with `hx-boost` active
- `base.html` — full layout with sidebar, topbar, content slot
- `base_auth.html` — minimal layout for login / 403 (no sidebar)
- Sidebar navigation items driven by `user_role` context variable
- Dark mode toggle (Flowbite built-in, persisted via `localStorage`)
- Static files configuration (`STATICFILES_DIRS`, `STATIC_URL`)
- Django template directories configured

## Responsibilities

**Owner:** Phase 1 lead.  
Feature developers extend `base.html` with `{% block content %}` — they do not modify the base template or Tailwind config.

## Django App

`core` (templates live in `core/templates/`)

## Files to Create / Modify

```
core/
└── templates/
    ├── base.html               # Full app shell — sidebar + topbar + content block
    ├── base_auth.html          # Auth-only shell — no sidebar
    └── partials/
        └── _sidebar.html       # Extracted sidebar, included by base.html

static/
└── src/
    └── input.css               # Tailwind entry point

transitops/
└── settings/
    └── base.py                 # STATICFILES_DIRS, TEMPLATES dirs

package.json                    # Tailwind CLI build scripts
```

## Dependencies

- `PROJECT_SETUP.md` — static files settings must be in place
- `AUTHENTICATION.md` — `user_role` context variable must be injected (from `core/context_processors.py`)
- Must be done before any feature app renders a template

## Business Rules

- Every authenticated view must extend `base.html`.
- Sidebar links are conditionally rendered based on `{{ user_role }}`.
- The dark mode class (`dark`) is toggled on `<html>` via JavaScript — Tailwind's `darkMode: 'class'` strategy.
- Feature apps must never import Tailwind or Flowbite themselves — it is global.
- HTMX is loaded in `base.html`; `hx-boost="true"` is set on `<body>`.

## Implementation Steps

### 1. Install Tailwind CSS v4 and Flowbite

```bash
npm init -y
npm install tailwindcss@next @tailwindcss/cli flowbite
```

`package.json` scripts:

```json
{
  "scripts": {
    "dev": "npx @tailwindcss/cli -i ./static/src/input.css -o ./static/dist/output.css --watch",
    "build": "npx @tailwindcss/cli -i ./static/src/input.css -o ./static/dist/output.css --minify"
  }
}
```

`static/src/input.css`:

```css
@import "tailwindcss";
@import "flowbite";
```

This is the entire CSS config for Tailwind v4 — no `tailwind.config.js` needed.

### 2. Django static files settings

`settings/base.py`:

```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # for collectstatic in production

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'core' / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'core.context_processors.user_role',      # injects user_role
        ],
    },
}]
```

### 3. `base.html` — full app shell

`core/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en" class="">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{% block title %}TransitOps{% endblock %}</title>
  {% load static %}
  <link rel="stylesheet" href="{% static 'dist/output.css' %}">
</head>

<body class="bg-gray-50 dark:bg-gray-900 antialiased"
      hx-boost="true">

  {% include "partials/_sidebar.html" %}

  <!-- Main content -->
  <div class="sm:ml-64 min-h-screen">

    <!-- Topbar -->
    <nav class="bg-white border-b border-gray-200 dark:bg-gray-800 dark:border-gray-700 px-4 py-3 flex items-center justify-between">
      <span class="text-sm font-medium text-gray-500 dark:text-gray-400">
        {{ user_role }}
      </span>
      <div class="flex items-center gap-4">

        <!-- Dark mode toggle -->
        <button id="theme-toggle" type="button"
          class="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg text-sm p-2">
          <svg id="theme-toggle-dark-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path>
          </svg>
          <svg id="theme-toggle-light-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4.22 1.78a1 1 0 011.415 1.415l-.707.707A1 1 0 1113.513 4.9l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1z"></path>
          </svg>
        </button>

        <!-- Logout -->
        <a href="{% url 'logout' %}"
           class="text-sm text-gray-600 dark:text-gray-300 hover:text-red-500">
          Sign out
        </a>
      </div>
    </nav>

    <!-- Page content -->
    <main class="p-6">
      {% if messages %}
        {% for message in messages %}
          <div class="mb-4 p-4 rounded-lg text-sm
            {% if message.tags == 'error' %}bg-red-50 text-red-800 dark:bg-red-900 dark:text-red-300
            {% elif message.tags == 'success' %}bg-green-50 text-green-800 dark:bg-green-900 dark:text-green-300
            {% else %}bg-blue-50 text-blue-800 dark:bg-blue-900 dark:text-blue-300{% endif %}">
            {{ message }}
          </div>
        {% endfor %}
      {% endif %}

      {% block content %}{% endblock %}
    </main>
  </div>

  <!-- HTMX -->
  <script src="https://unpkg.com/htmx.org@1.9.12"></script>
  <!-- Flowbite JS -->
  <script src="https://cdn.jsdelivr.net/npm/flowbite@2.5.2/dist/flowbite.min.js"></script>

  <!-- Dark mode persistence -->
  <script>
    const toggle = document.getElementById('theme-toggle');
    const dark = document.getElementById('theme-toggle-dark-icon');
    const light = document.getElementById('theme-toggle-light-icon');

    if (localStorage.getItem('color-theme') === 'dark' ||
        (!localStorage.getItem('color-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
      light.classList.remove('hidden');
    } else {
      dark.classList.remove('hidden');
    }

    toggle.addEventListener('click', () => {
      dark.classList.toggle('hidden');
      light.classList.toggle('hidden');
      const isDark = document.documentElement.classList.toggle('dark');
      localStorage.setItem('color-theme', isDark ? 'dark' : 'light');
    });
  </script>

  {% block extra_scripts %}{% endblock %}
</body>
</html>
```

### 4. `_sidebar.html` — role-gated navigation

`core/templates/partials/_sidebar.html`:

```html
<aside class="fixed top-0 left-0 z-40 w-64 h-screen transition-transform -translate-x-full sm:translate-x-0"
       aria-label="Sidebar">
  <div class="h-full px-3 py-4 overflow-y-auto bg-white border-r border-gray-200 dark:bg-gray-800 dark:border-gray-700">

    <a href="{% url 'dashboard' %}" class="flex items-center ps-2.5 mb-6">
      <span class="self-center text-xl font-bold text-gray-900 dark:text-white">TransitOps</span>
    </a>

    <ul class="space-y-2 font-medium">

      <li>
        <a href="{% url 'dashboard' %}"
           class="flex items-center p-2 text-gray-700 rounded-lg dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700">
          Dashboard
        </a>
      </li>

      {% if user_role == 'Fleet Manager' or user_role == 'Driver' %}
      <li>
        <a href="{% url 'vehicle_list' %}"
           class="flex items-center p-2 text-gray-700 rounded-lg dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700">
          Vehicles
        </a>
      </li>
      <li>
        <a href="{% url 'trip_list' %}"
           class="flex items-center p-2 text-gray-700 rounded-lg dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700">
          Trips
        </a>
      </li>
      {% endif %}

      {% if user_role == 'Fleet Manager' %}
      <li>
        <a href="{% url 'maintenance_list' %}"
           class="flex items-center p-2 text-gray-700 rounded-lg dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700">
          Maintenance
        </a>
      </li>
      {% endif %}

      {% if user_role == 'Safety Officer' %}
      <li>
        <a href="{% url 'driver_list' %}"
           class="flex items-center p-2 text-gray-700 rounded-lg dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700">
          Drivers
        </a>
      </li>
      {% endif %}

      {% if user_role == 'Financial Analyst' %}
      <li>
        <a href="{% url 'finance_dashboard' %}"
           class="flex items-center p-2 text-gray-700 rounded-lg dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700">
          Finance
        </a>
      </li>
      <li>
        <a href="{% url 'reports' %}"
           class="flex items-center p-2 text-gray-700 rounded-lg dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700">
          Reports
        </a>
      </li>
      {% endif %}

    </ul>
  </div>
</aside>
```

> **Note:** URL names like `vehicle_list`, `trip_list`, etc. are stubs. Django will raise `NoReverseMatch` until feature apps register those URLs. Wrap in `{% url ... %}` with a `{% url 'vehicle_list' default '#' %}` fallback, or add the URL stubs early.

### 5. `base_auth.html` — no sidebar

`core/templates/base_auth.html`:

```html
<!DOCTYPE html>
<html lang="en" class="">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{% block title %}TransitOps{% endblock %}</title>
  {% load static %}
  <link rel="stylesheet" href="{% static 'dist/output.css' %}">
</head>
<body class="bg-gray-50 dark:bg-gray-900 antialiased">
  {% block content %}{% endblock %}
  <script src="https://cdn.jsdelivr.net/npm/flowbite@2.5.2/dist/flowbite.min.js"></script>
</body>
</html>
```

### 6. Dashboard stub

Until Phase 3 builds the real dashboard, provide a stub view so `LOGIN_REDIRECT_URL` resolves:

`core/views.py`:

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')
```

`core/templates/core/dashboard.html`:

```html
{% extends "base.html" %}
{% block title %}Dashboard — TransitOps{% endblock %}
{% block content %}
<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
<p class="text-gray-500 dark:text-gray-400 mt-2">Phase 3 will populate this view.</p>
{% endblock %}
```

`transitops/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    # Feature apps registered here as phases complete:
    # path('vehicles/', include('fleet.urls')),
    # path('drivers/', include('drivers.urls')),
    # path('trips/', include('trips.urls')),
]
```

## Success Scenario

1. `npm run dev` compiles `output.css` with no errors
2. `python manage.py runserver` starts; visiting `/dashboard/` (logged in) renders sidebar + topbar
3. Sidebar shows only the links appropriate for the logged-in user's role
4. Dark mode toggle switches the theme and persists on page refresh
5. An HTMX `hx-get` attribute on any link performs a partial swap without a full reload

## Definition of Done

- [ ] `npm run dev` and `npm run build` both succeed
- [ ] `output.css` is generated and served at `/static/dist/output.css`
- [ ] `base.html` renders in both light and dark mode with no broken styles
- [ ] Sidebar is hidden on mobile, visible on `sm:` and above (Flowbite responsive behaviour)
- [ ] Dark mode toggle works and persists across page reloads via `localStorage`
- [ ] HTMX `hx-boost` is active on `<body>`; navigation links work without full reloads
- [ ] Dashboard stub at `/dashboard/` renders without error for any authenticated user
- [ ] URL names referenced in the sidebar that don't exist yet use `#` as a safe fallback

## AI Instructions

- Tailwind v4 requires only `@import "tailwindcss"` in the CSS file — no `tailwind.config.js`, no `content:` array. Do not generate a config file.
- Flowbite JS should be loaded from CDN in Phase 1 to avoid NPM complexity; switch to bundled import in production if needed.
- HTMX must be loaded before `{% block extra_scripts %}` so feature pages can rely on it being available.
- The `dark` class is toggled on `<html>`, not `<body>`. Tailwind's class strategy requires this. Do not change it.
- Sidebar URL stubs (`vehicle_list`, etc.) will raise `NoReverseMatch` until feature apps exist. Use `{% url 'name' default '#' %}` or add placeholder `path()` entries in `urls.py` that return `HttpResponseNotFound` temporarily.
- `base_auth.html` must not include the sidebar or the `hx-boost` attribute — it is used only for unauthenticated pages.
- The `{% block extra_scripts %}` block at the bottom of `base.html` allows feature templates to add Chart.js, Leaflet, etc. without modifying the base template.
- `core/views.py` dashboard stub is replaced entirely in Phase 3 — do not build KPI logic here.
