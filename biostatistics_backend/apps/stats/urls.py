from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CourseStatsViewSet


router = DefaultRouter()
router.register(r'', CourseStatsViewSet, basename='course-stats')

urlpatterns = [
    path("", include(router.urls)),
]