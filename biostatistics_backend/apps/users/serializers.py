# Python modules
from typing import Any

# Django modules
from django.contrib.auth import authenticate

# Third party modules
from rest_framework import serializers

# Local modules
from apps.users.models import CustomUser


class UserReadSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода данных пользователя.

    Используется для отображения информации, которую можно читать,
    но не изменять через API.
    """

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "university",
            "faculty",
            "group",
            "role",
        ]


class UserRegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации нового пользователя.

    При сохранении объект пользователя создается с хешированным паролем.
    """

    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "full_name",
            "email",
            "university",
            "faculty",
            "group",
            "role",
            "password",
        ]

    def create(self, validated_data):
        """Создаёт пользователя и хеширует пароль перед сохранением."""
        password = validated_data.pop("password")
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def validate_email(self, value):
        """Проверяет уникальность email при регистрации."""
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value


class UserRegisterResponseSerializer(serializers.ModelSerializer):
    """Сериализатор для ответа при успешной регистрации."""

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "university",
            "faculty",
            "group",
            "role",
        ]


class UserLoginSerializer(serializers.Serializer):
    """Сериализатор для аутентификации пользователя."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Проверяет учётные данные и возвращает объект пользователя."""

        email = data.get("email")
        password = data.get("password")

        if email and password:
            user = authenticate(email=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid email or password")
            if not user.is_active:
                raise serializers.ValidationError("Account is disabled")
        else:
            raise serializers.ValidationError("Email and password are required")

        data["user"] = user
        return data


class UserLoginResponseSerializer(serializers.ModelSerializer):
    """Сериализатор для ответа при успешной аутентификации."""

    refresh = serializers.CharField(read_only=True)
    access = serializers.CharField(read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "university",
            "faculty",
            "group",
            "role",
            "refresh",
            "access",
        ]


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления данных пользователя."""

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "full_name",
            "email",
            "university",
            "faculty",
            "group",
            "role",
        ]

    def validate_email(self, value):
        """Проверяет, что обновляемый email остаётся уникальным."""
        user = self.instance
        if user:
            if CustomUser.objects.filter(email=value).exclude(id=user.id).exists():
                raise serializers.ValidationError("Email already exists")
        return value
