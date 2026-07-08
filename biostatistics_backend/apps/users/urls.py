# Django modules
from django.urls import path, include

# Third-party modules
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Project modules
from apps.users.views import CustomUserViewSet


router = DefaultRouter()
router.register(r'', CustomUserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]