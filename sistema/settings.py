"""
Django settings for sistema project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ════════════════════════════════════════════════════════════
# 🔐 SECURITY — Configuración base
# ════════════════════════════════════════════════════════════
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'default-unsafe-secret-key-for-dev')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

# Hosts permitidos (en producción NUNCA usar '*')
if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


INSTALLED_APPS = [
    # 🔐 axes debe ir ANTES de django.contrib.admin para que funcione
    'axes',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps del proyecto encomiendas
    'clientes',
    'rutas',
    'envios',

    # API - Sesión 05
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_spectacular',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # 🔐 axes debe ir AL FINAL (después de Authentication)
    'axes.middleware.AxesMiddleware',
]

# 🔐 Backend de autenticación con axes (intentos fallidos)
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',          # ← bloquea si hay lockout
    'django.contrib.auth.backends.ModelBackend',    # ← autenticación normal
]

ROOT_URLCONF = 'sistema.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'envios.context_processors.estadisticas_globales',
            ],
        },
    },
]

WSGI_APPLICATION = 'sistema.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'postgres'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}


# ════════════════════════════════════════════════════════════
# 🔐 PASSWORD VALIDATORS — Reforzados
# ════════════════════════════════════════════════════════════
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},  # Mínimo 8 caracteres
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'es-pe'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TEMPLATES[0]['DIRS'] = [BASE_DIR / 'templates']
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ════════════════════════════════════════════════════════════
# 🔐 AUTENTICACIÓN
# ════════════════════════════════════════════════════════════
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/inicio/'


# ════════════════════════════════════════════════════════════
# 🔐 SESIONES — Cookies seguras
# ════════════════════════════════════════════════════════════
SESSION_COOKIE_NAME = 'encomiendas_session'
SESSION_COOKIE_AGE = 60 * 30                     # 🔐 30 min de inactividad → logout
SESSION_SAVE_EVERY_REQUEST = True                # 🔐 Renueva el timeout en cada request
SESSION_EXPIRE_AT_BROWSER_CLOSE = True           # 🔐 Cierra sesión al cerrar el navegador
SESSION_COOKIE_HTTPONLY = True                   # 🔐 JS no puede leer la cookie (anti-XSS)
SESSION_COOKIE_SAMESITE = 'Lax'                  # 🔐 Anti-CSRF cross-site
CSRF_COOKIE_HTTPONLY = False                     # CSRF debe ser leído por JS para AJAX
CSRF_COOKIE_SAMESITE = 'Lax'

# 🔐 En producción (DEBUG=False) las cookies viajan SOLO por HTTPS
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


# ════════════════════════════════════════════════════════════
# 🔐 HEADERS DE SEGURIDAD HTTP
# ════════════════════════════════════════════════════════════
# Anti-clickjacking: nadie puede meter tu sitio en un <iframe>
X_FRAME_OPTIONS = 'DENY'

# Anti-XSS: el navegador detecta y bloquea scripts maliciosos
SECURE_BROWSER_XSS_FILTER = True

# Anti-MIME-sniffing: previene que el navegador "adivine" tipos de archivo
SECURE_CONTENT_TYPE_NOSNIFF = True

# Anti-MITM en producción
if not DEBUG:
    # Forzar HTTPS
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # HSTS — el navegador recordará por 1 año que solo HTTPS funciona
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Solo enviar referrer al mismo origen
    SECURE_REFERRER_POLICY = 'same-origin'


# ════════════════════════════════════════════════════════════
# 🔐 DJANGO-AXES — Protección contra fuerza bruta
# ════════════════════════════════════════════════════════════
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5                            # Después de 5 intentos fallidos
AXES_COOLOFF_TIME = 0.5                           # ...bloquea por 30 minutos
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']  # Bloquea por usuario E IP
AXES_RESET_ON_SUCCESS = True                      # Limpia contador al loguear bien
AXES_LOCKOUT_TEMPLATE = 'errors/locked.html'      # Página bonita cuando bloquea
AXES_VERBOSE = True                               # Log detallado de intentos


# ════════════════════════════════════════════════════════════
# 🔐 DJANGO REST FRAMEWORK
# ════════════════════════════════════════════════════════════
from datetime import timedelta

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 15,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # Sesión 06 — Throttling global
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon':       '20/min',
        'user':       '120/min',
        'dni_search': '10/min',
        'empleados':  '60/min',
    },
    # Sesión 06 — Versionamiento por URL (NamespaceVersioning)
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2'],
    # Sesión 06 — Manejo de errores personalizado
    'EXCEPTION_HANDLER': 'api.exceptions.custom_exception_handler',
}


# ════════════════════════════════════════════════════════════
# 🔐 JWT — Tokens más cortos y rotación
# ════════════════════════════════════════════════════════════
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),     # 🔐 30 min (antes 60)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),        # 🔐 1 día (antes 7)
    'ROTATE_REFRESH_TOKENS': True,                      # 🔐 Refresh nuevo en cada uso
    'BLACKLIST_AFTER_ROTATION': True,                   # 🔐 Invalida el viejo
    'AUTH_HEADER_TYPES': ('Bearer',),
    'UPDATE_LAST_LOGIN': True,                          # Registra último acceso
}


# ════════════════════════════════════════════════════════════
# 🔐 CORS — Restrictivo en producción
# ════════════════════════════════════════════════════════════
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = os.environ.get(
        'CORS_ALLOWED_ORIGINS', ''
    ).split(',') if os.environ.get('CORS_ALLOWED_ORIGINS') else []
    CORS_ALLOW_CREDENTIALS = True


# ════════════════════════════════════════════════════════════
# 📋 LOGGING — Auditoría de seguridad
# ════════════════════════════════════════════════════════════
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'axes': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}


# ════════════════════════════════════════════════════════════
# 📧 EMAIL — Notificaciones automáticas
# ════════════════════════════════════════════════════════════
# En desarrollo: backend de consola (los emails aparecen en docker logs)
# En producción: configurar SMTP real (Gmail, SendGrid, etc.)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    'Sistema de Encomiendas <noreply@encomiendas.pe>'
)


# ════════════════════════════════════════════════════════════
# Documentación API
# ════════════════════════════════════════════════════════════
SPECTACULAR_SETTINGS = {
    'TITLE': 'API Sistema de Encomiendas',
    'DESCRIPTION': 'API RESTful para gestión de encomiendas',
    'VERSION': '1.0.0',
}
