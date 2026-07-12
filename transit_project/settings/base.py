"""Shared settings for every TransitOps environment."""

import os
from pathlib import Path
from importlib.util import find_spec
from urllib.parse import unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent.parent.parent

try:
    import environ
except ModuleNotFoundError:
    class _FallbackEnv:
        def __init__(self, **defaults):
            self.defaults = defaults
            self.values = {}

        @classmethod
        def read_env(cls, path):
            if not path.exists():
                return
            with path.open() as env_file:
                for line in env_file:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    self = getattr(cls, "_instance", None)
                    if self is not None:
                        self.values[key.strip()] = value.strip().strip('"').strip("'")

        def __call__(self, key, default=None):
            value = os.environ.get(key, self.values.get(key))
            if value is None:
                value = default
            if value is None and key in self.defaults:
                caster, fallback = self.defaults[key]
                value = fallback
                return caster(value)
            if key in self.defaults and self.defaults[key][0] is bool:
                return str(value).lower() in {"1", "true", "yes", "on"}
            return value

        def list(self, key, default=None):
            value = self(key, default="")
            if not value:
                return default or []
            return [item.strip() for item in value.split(",") if item.strip()]

        def db(self, key):
            value = self(key)
            parsed = urlparse(value)
            if parsed.scheme == "sqlite":
                return {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": unquote(parsed.path.lstrip("/")) or BASE_DIR / "db.sqlite3",
                }
            return {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": parsed.path.lstrip("/"),
                "USER": unquote(parsed.username or ""),
                "PASSWORD": unquote(parsed.password or ""),
                "HOST": parsed.hostname or "",
                "PORT": parsed.port or "",
            }

    env = _FallbackEnv(DEBUG=(bool, False))
    _FallbackEnv._instance = env
    _FallbackEnv.read_env(BASE_DIR / '.env')
else:
    env = environ.Env(DEBUG=(bool, False))
    environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

THIRD_PARTY_APPS = [
    app
    for app in [
        'anymail',
        'crispy_forms',
        'crispy_tailwind',
        'import_export',
        'django_fsm',
        'admincharts',
    ]
    if find_spec(app) is not None
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    *THIRD_PARTY_APPS,
    'accounts',
    'core',
    'documents',
    'drivers',
    'fleet',
    'maintenance',
    'notifications',
    'trips',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'transit_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'core' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.user_role',
            ],
        },
    },
]

WSGI_APPLICATION = 'transit_project.wsgi.application'
ASGI_APPLICATION = 'transit_project.asgi.application'

DATABASES = {'default': env.db('DATABASE_URL')}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTHENTICATION_BACKENDS = ['accounts.backends.EmailBackend']
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# --- Anymail (Email) ---
EMAIL_BACKEND = (
    'anymail.backends.sendgrid.EmailBackend'
    if find_spec('anymail') is not None
    else 'django.core.mail.backends.console.EmailBackend'
)
ANYMAIL = {
    'SENDGRID_API_KEY': env('SENDGRID_API_KEY', default=''),
}
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='transitops@yourdomain.com')

# --- Twilio (SMS  optional) ---
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN  = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_FROM_NUMBER = env('TWILIO_FROM_NUMBER', default='')

# --- Notification thresholds ---
LICENSE_WARN_DAYS          = 30
LICENSE_REMINDER_DAYS      = [30, 15, 5]
LICENSE_CRITICAL_DAYS      = 7
MAINTENANCE_KM_THRESHOLD   = 15000
MAINTENANCE_OVERDUE_DAYS   = 7
