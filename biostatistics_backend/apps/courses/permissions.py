from rest_framework import permissions

from apps.users.models import CustomUser as User

class IsAdminOrTeacherOrReadOnly(permissions.BasePermission):
    """
    Разрешает просмотр всем, но изменять структуру могут только
    администраторы или пользователи с ролью 'teacher'.
    """

    def has_permission(self, request, view):
        # 1. Свободный доступ на чтение (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # 2. Проверяем, что пользователь вообще залогинен
        if not request.user or not request.user.is_authenticated:
            return False

        # 3. Админам и суперпользователям разрешено всё по умолчанию
        if request.user.is_staff or request.user.is_superuser:
            return True

        # 4. Проверяем роль преподавателя через текстовое поле.
        # Метод getattr() защитит от ошибок, если вдруг поля 'role' у юзера не окажется.
        user_role = getattr(request.user, "role", None)

        # Здесь укажите точную строку, которая хранится у вас в базе для учителей (например, 'teacher' или 'TEACHER')
        return user_role == User.Role.TEACHER