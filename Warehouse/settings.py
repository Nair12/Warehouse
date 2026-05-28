import os
from pathlib import Path
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _

os.environ['PGCLIENTENCODING'] = 'utf8'
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-jv!8x+vx78217(v3#69m3ckaus2kr5)j$@sub!ysc+3_hltg=e')

# 2. Безопасное переключение DEBUG.
# В Azure мы передадим строку 'False'. Проверка '== "True"' превратит её в булево False.
# По умолчанию (если переменная не задана локально) — True для удобства разработки.
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'


ALLOWED_HOSTS = [os.getenv('ALLOWED_HOSTS', '*')]


CSRF_TRUSTED_ORIGINS = [os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000')]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'products',
    'warehouses',
    'trading',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
     'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',

    # Включает выбор языка через cookie/session/request.
    # Должен быть после SessionMiddleware и до CommonMiddleware.
    'django.middleware.locale.LocaleMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # Включает часовой пояс текущего пользователя.
    'users.middleware.TimezoneMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Warehouse.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'Warehouse.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),  # '127.0.0.1' — это запасной вариант
        'PORT': os.getenv('DB_PORT', '5432'),       # '5432' — стандартный порт Postgres
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'ru'

LANGUAGES = [
    ('ru', _('Русский')),
    ('en', _('English')),
    ('tr', _('Türkçe')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# База хранит время в UTC.
# Показывать пользователю его локальное время будет TimezoneMiddleware.
TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # <-- ДОБАВИЛИ ЭТУ СТРОКУ

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Хранилище для WhiteNoise (сжимает файлы и кэширует их для быстрой отдачи)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

AUTH_USER_MODEL = 'users.CustomUser'
LOGIN_REDIRECT_URL = '/redirect-by-role/'
LOGOUT_REDIRECT_URL = '/login/'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
