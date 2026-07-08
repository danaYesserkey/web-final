from django.core.cache import cache
from django.shortcuts import get_object_or_404  # noqa
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action  # noqa
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny

from apps.courses.models import Course, Module, Lesson, Content
from apps.courses.serializers import (
    CourseSerializer,
    CourseDetailSerializer,
    ModuleSerializer,
    LessonSerializer,
    LessonDetailSerializer,
    ContentSerializer,
)
from apps.courses.permissions import IsAdminOrTeacherOrReadOnly
from apps.stats.models import CourseStatistics
from apps.users.models import CustomUser


# Выносим логику очистки в хелпер, так как курс может измениться через Модуль или Урок
def invalidate_course_cache(course_id):
    if course_id:
        cache.delete(f"course_detail_{course_id}")


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().prefetch_related("modules__lessons")
    permission_classes = [IsAdminOrTeacherOrReadOnly]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseSerializer

    def retrieve(self, request, *args, **kwargs):
        course_id = kwargs.get("pk")

        # Строим уникальный ключ для кэша, учитывая ID курса И статус пользователя (опционально)
        # Если данные курса для всех одинаковые (и для админа, и для студента):
        cache_key = f"course_detail_{course_id}"

        # Если данные отличаются для админа и гостя, добавляем маркер:
        # is_staff = request.user.is_staff if request.user.is_authenticated else False
        # cache_key = f"course_detail_{course_id}_staff_{is_staff}"

        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        # Если в кэше нет — выполняем стандартный retrieve
        response = super().retrieve(request, *args, **kwargs)

        # Сохраняем в кэш именно response.data (dict), а не сам объект Response
        cache.set(cache_key, response.data, 7200)

        return response

    # Если сам курс обновили/удалили — чистим только его кэш
    def perform_update(self, serializer):
        instance = serializer.save()
        invalidate_course_cache(instance.id)

    def perform_destroy(self, instance):
        invalidate_course_cache(instance.id)
        instance.delete()


class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [IsAdminOrTeacherOrReadOnly]

    def perform_create(self, serializer):
        instance = serializer.save()
        invalidate_course_cache(
            instance.course_id
        )  # Чистим только тот курс, куда добавлен модуль

    def perform_update(self, serializer):
        instance = serializer.save()
        invalidate_course_cache(instance.course_id)

    def perform_destroy(self, instance):
        course_id = instance.course_id
        instance.delete()
        invalidate_course_cache(course_id)


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAdminOrTeacherOrReadOnly]

    def perform_create(self, serializer):
        instance = serializer.save()
        # Урок привязан к модулю, а модуль к курсу
        course_id = instance.module.course_id if instance.module else None
        invalidate_course_cache(course_id)

    def perform_update(self, serializer):
        instance = serializer.save()
        course_id = instance.module.course_id if instance.module else None
        invalidate_course_cache(course_id)

    def perform_destroy(self, instance):
        course_id = instance.module.course_id if instance.module else None
        instance.delete()
        invalidate_course_cache(course_id)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = LessonDetailSerializer(instance=instance, context={'request': request})

        if not request.user.is_authenticated:
            return Response(serializer.data)

        try:
            user = CustomUser.objects.get(id=request.user.id)
        except CustomUser.DoesNotExist:
            return Response(serializer.data)

        previous_lesson = Lesson.objects.filter(id__lt=instance.id).order_by('-id').first()

        if not previous_lesson:
            return Response(serializer.data)

        try:
            statistics = CourseStatistics.objects.get(
                lesson=previous_lesson, 
                user=user
            )
            if not statistics.completed:
                return Response({"has_access": False})
        except CourseStatistics.DoesNotExist:
            return Response({"has_access": False})

        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        serializer_class=ContentSerializer,
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_file(self, request, pk=None):
        """Эндпоинт для загрузки файла к конкретному уроку"""
        lesson = self.get_object()

        # request.data при multipart-запросах неизменяемый, делаем копию
        serializer_data = (
            request.data.dict()
            if hasattr(request.data, "dict")
            else request.data.copy()
        )

        # Жестко привязываем загружаемый файл к текущему уроку
        serializer_data["lesson"] = lesson.id

        # Если препод не передал порядковый номер (order), ставим в конец
        if "order" not in serializer_data:
            serializer_data["order"] = lesson.contents.count() + 1

        serializer = ContentSerializer(data=serializer_data)

        if serializer.is_valid():
            serializer.save()

            # Сбрасываем кэш курса, так как контент урока изменился
            course_id = lesson.module.course_id if lesson.module else None
            invalidate_course_cache(course_id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=["get"],
        serializer_class=ContentSerializer,
        permission_classes=[AllowAny],
    )
    def contents(self, request, pk=None):
        lesson = self.get_object()
        contents = Content.objects.filter(lesson=lesson)  # noqa: F821
        serializer = ContentSerializer(contents, many=True)
        return Response(serializer.data)
