from decouple import config
from datetime import timedelta  # noqa
from pathlib import Path  # noqa
from dotenv import load_dotenv
from os import path # noqa  # noqa

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Environment
ENV_OPTIONS = ("local", "prod")

ENV_ID = config("ENVIRONMENT", default="local")

SECRET_KEY = config("DJANGO_SECRET_KEY")


try:
    settings_env_module = f"settings.env.{ENV_ID}"

    globals().update(__import__(settings_env_module, fromlist=["*"]).__dict__)
except ImportError as e:
    raise ImportError(f"Could not import settings for environment '{ENV_ID}': {e}")


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "biostat-local-cache",
    }
}

# Spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Biostatistics Platform API',
    'DESCRIPTION': 'API для платформы биостатистики',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # ХАК ТУТ: Говорим Swagger срезать префикс '/api/v1' или '/api' при создании групп!
    'SCHEMA_PATH_PREFIX': r'/api/', 
} 

# -- Media and Cloud storage settings --
USE_S3 = config('USE_S3', default=False, cast=bool)

# Максимальный размер загрузки (100MB), чтобы Django не падал на больших файлах
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024

if USE_S3:
    # Включаем интеграцию с S3 через django-storages
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage", # Статику пока оставляем локально
        },
    }
    
    # Креденшелы для подключения к облаку через decouple
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default=None)
    AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default=None)
    
    # Важные настройки безопасности и отдачи файлов
    AWS_DEFAULT_ACL = 'public-read'  # Файлы доступны по прямой ссылке на чтение
    AWS_QUERYSTRING_AUTH = False     # Отключаем генерацию временных токенов в URL (если бакет публичный)
    AWS_S3_FILE_OVERWRITE = False    # Запрещаем перезаписывать файлы с одинаковыми именами

else:
    # Локальная разработка: файлы сохраняются в папку медиа на твоем компе
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    
    MEDIA_URL = '/media/'
    MEDIA_ROOT = path.join(BASE_DIR, 'media')