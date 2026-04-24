from pathlib import Path
import os
from decouple import config # Necesitas instalar python-decouple

BASE_DIR = Path(__file__).resolve().parent.parent

# --- SEGURIDAD (Desde .env) ---
SECRET_KEY = config('SECRET_KEY', default='tu-clave-secreta-de-emergencia')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0').split(',')

# --- APLICACIONES ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Tus apps del sistema
    'envios',
    'clientes',
    'rutas',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # <-- Faltaba este
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',  # <-- Faltaba este
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sistema.urls'

# ... (Middlewares y ROOT_URLCONF se mantienen igual)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Habilitamos la carpeta global para base.html
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- BASE DE DATOS POSTGRESQL (Desde .env) ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='postgres'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='db'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# --- LOCALIZACIÓN PERÚ ---
LANGUAGE_CODE = 'es-pe' # [cite: 372, 749]
TIME_ZONE = 'America/Lima' # [cite: 373, 750]
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
# Esta línea le dice a Django dónde reunir todos los estilos
STATIC_ROOT = BASE_DIR / 'static'