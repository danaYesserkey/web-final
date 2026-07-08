from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.cache import cache  # Импортируем кэш для проверок

from rest_framework.test import APITestCase
from rest_framework import status

from apps.courses.models import Course, Module

User = get_user_model()


class CourseAPITestCase(APITestCase):
    def setUp(self):
        # ОБЯЗАТЕЛЬНО: Очищаем кэш перед каждым тестом, чтобы они были изолированы
        cache.clear()

        # Создаем тестовый курс
        self.course = Course.objects.create(
            course_name="Тестовый курс", description="Описание"
        )

        self.url_list = reverse("course-list")
        self.url_detail = reverse("course-detail", kwargs={"pk": self.course.id})

        self.student = User.objects.create_user(
            username="test_student",
            email="stud@test.com",
            password="password",
            role="STUDENT",
        )
        self.teacher = User.objects.create_user(
            username="test_teacher",
            email="teach@test.com",
            password="password",
            role="TEACHER",
        )

    def tearDown(self):
        # Очищаем кэш после каждого теста
        cache.clear()

    def test_student_cannot_create_course(self):
        """Проверяем, что студент не может создать курс (Защита пермишна)"""
        self.client.force_authenticate(user=self.student)
        data = {"course_name": "Новый курс"}
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_teacher_can_create_course(self):
        """Проверяем, что препод может создать курс"""
        self.client.force_authenticate(user=self.teacher)
        data = {"course_name": "Курс от препода", "description": "Инфо"}
        response = self.client.post(self.url_list, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_anyone_can_view_course_detail(self):
        """Проверяем, что детальный просмотр доступен и возвращает структуру"""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(self.url_detail)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("modules", response.data)

    # ==========================================
    # НОВЫЕ ТЕСТЫ ДЛЯ ПРОВЕРКИ КЭШИРОВАНИЯ
    # ==========================================

    def test_course_detail_is_cached(self):
        """Проверяем, что данные деталки курса реально кэшируются"""
        self.client.force_authenticate(user=self.student)

        # 1. Делаем первый запрос (формирует кэш)
        response_1 = self.client.get(self.url_detail)
        self.assertEqual(response_1.status_code, status.HTTP_200_OK)

        # 2. Напрямую в БД меняем описание курса (в обход API)
        Course.objects.filter(id=self.course.id).update(
            description="Новое описание, скрытое от кэша"
        )

        # 3. Делаем повторный запрос
        response_2 = self.client.get(self.url_detail)

        # Данные должны вернуться ИЗ КЭША (то есть старое описание), а не из измененной БД
        self.assertEqual(response_2.data["description"], "Описание")
        self.assertNotEqual(
            response_2.data["description"], "Новое описание, скрытое от кэша"
        )

    def test_cache_invalidates_on_module_creation(self):
        """Проверяем, что кэш курса сбрасывается, если к нему добавляется модуль"""
        self.client.force_authenticate(user=self.teacher)

        # 1. Генерируем кэш курса первым запросом
        self.client.get(self.url_detail)

        # Убеждаемся, что в кэше сейчас что-то лежит
        cache_key = f"course_detail_{self.course.id}"
        self.assertIsNotNone(cache.get(cache_key))

        # 2. Через API (или дефолтный метод создания) создаем модуль для этого курса
        url_module_list = reverse("module-list")  # Предполагаем, что имя роута такое
        module_data = {
            "module_name": "Новый модуль",
            "course": self.course.id,
            "order": 1,
        }

        # Этот запрос триггерит perform_create в ModuleViewSet, где вызывается invalidate_course_cache
        response = self.client.post(url_module_list, module_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 3. ПРОВЕРКА: Кэш этого конкретного курса должен быть уничтожен (равен None)
        self.assertIsNone(cache.get(cache_key))
