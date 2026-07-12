"""Shared settings for every TransitOps environment."""

from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'anymail',
    'crispy_forms',
    'crispy_tailwind',
    'import_export',
    'django_fsm',
    'admincharts',
    'accounts',
    'core',
    'drivers',
    'fleet',
    'finance',
    'trips',
    'maintenance',
    'notifications',
    # Map integrations ('djgeojson', 'leaflet') are registered in Phase 5.
    'reports',
    'dashboard',
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTHENTICATION_BACKENDS = ['accounts.backends.EmailBackend']
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard:home'
LOGOUT_REDIRECT_URL = 'login'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'tailwind'
CRISPY_TEMPLATE_PACK = 'tailwind'

# --- Anymail (Email) ---
EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'
ANYMAIL = {
    'SENDGRID_API_KEY': env('SENDGRID_API_KEY', default=''),
}
DEFAULT_FROM_EMAIL = 'transitops@yourdomain.com'

# --- Twilio (SMS  optional) ---
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN  = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_FROM_NUMBER = env('TWILIO_FROM_NUMBER', default='')

# --- Notification thresholds ---
LICENSE_WARN_DAYS          = 30
LICENSE_CRITICAL_DAYS      = 7
MAINTENANCE_KM_THRESHOLD   = 15000
MAINTENANCE_OVERDUE_DAYS   = 7
