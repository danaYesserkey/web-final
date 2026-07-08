from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import APIView

class IsProfileOwner(BasePermission):
    """
    Полный доступ (и чтение, и изменение) только к СВОЕМУ профилю.
    Запрещает просмотр личных данных других студентов.
    """
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        # И GET, и PUT запросы пройдут, только если объект в базе — это сам текущий юзер
        return bool(request.user and request.user.is_authenticated and obj == request.user)


class IsTeacherOrAdminOrReadOnly(BasePermission):
    """
    Разрешает просмотр (GET) всем авторизованным пользователям.
    Создание, изменение и удаление (POST, PUT, DELETE) — только для Teacher и Admin.
    Идеально для медицинских датасетов и лабораторных работ.
    """
    def has_permission(self, request: Request, view: APIView) -> bool:
        # 1. Проверяем, что пользователь вообще залогинен
        if not (request.user and request.user.is_authenticated):
            return False

        # 2. Если метод безопасный (например, студент хочет скачать датасет для анализа) — пускаем
        if request.method in SAFE_METHODS:
            return True
        
        # 3. На изменение пускаем только преподавателей и админов
        user_role = getattr(request.user, 'role', '')
        return user_role in ['teacher', 'admin'] or request.user.is_staff