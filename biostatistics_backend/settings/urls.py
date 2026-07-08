"""
URL configuration for biostatistics project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

# Third-party modules
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Включаем URL-ы приложения users
    path('api/users/', include('apps.users.urls')),

    # Включаем URL-ы приложения courses
    path('api/', include('apps.courses.urls')),

    path('api/quizzes/', include('apps.quizzes.urls')),

    path('api/stats/', include('apps.stats.urls')),

    # --- НАСТРОЙКА SWAGGER ---
    # 1. Этот эндпоинт просто генерирует схему (файл json/yaml) со всеми твоими путями
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # 2. Этот эндпоинт рендерит саму красивую веб-страницу Swagger UI.
    # В url_name='schema' мы передаем имя пути из строчки выше, чтобы Swagger знал, откуда качать JSON-схему
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path("api/ai/", include("apps.ai.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)