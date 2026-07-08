# Python modules
# import logging

# Django modules
# from django.shortcuts import render

# Third party modules
from rest_framework import status
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request as DRFRequest
from rest_framework.response import Response as DRFResponse
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import RefreshToken

# Local modules
from apps.users.serializers import (
    UserLoginSerializer,
    UserLoginResponseSerializer,
    UserRegisterResponseSerializer,
    UserRegisterSerializer,
    UserUpdateSerializer,
)
from apps.users.permissions import IsProfileOwner, IsTeacherOrAdminOrReadOnly
from apps.users.models import CustomUser  # Исправили путь импорта


@extend_schema_view(
    register=extend_schema(
        summary="Регистрация нового пользователя",
        request=UserRegisterSerializer,
        responses={status.HTTP_201_CREATED: UserRegisterResponseSerializer},
    ),
    login=extend_schema(
        summary="Аутентификация (Логин)",
        request=UserLoginSerializer,
        responses={status.HTTP_200_OK: UserLoginResponseSerializer},
    ),
    update=extend_schema(
        summary="Обновление профиля",
        request=UserUpdateSerializer,
        responses={status.HTTP_200_OK: UserRegisterResponseSerializer},
    ),
    get_info=extend_schema(
        summary="Получение профиля текущего пользователя",
        responses={status.HTTP_200_OK: UserRegisterResponseSerializer},
    ),
)

class CustomUserViewSet(GenericViewSet):
    """ViewSet для управления пользователями платформы биостатистики."""

    parser_classes = [JSONParser]
    # Все запросы принимаются как JSON. Это важно для корректной обработки тела POST/PUT/PATCH.

    # Базовый QuerySet для работы с пользователями.
    queryset = CustomUser.objects.all()


    def get_permissions(self):
        """Возвращает список разрешений в зависимости от действия.

        - register/login: разрешён любой пользователь.
        - update/partial_update/get_info: только аутентифицированный владелец профиля.
        - list/retrieve: только аутентифицированные пользователи с правами учителя/админа или просмотр в режиме только для чтения.
        """
        if self.action in ["register", "login"]:
            permission_classes = [AllowAny]
        elif self.action in ["update", "partial_update", "get_info"]:
            permission_classes = [IsAuthenticated, IsProfileOwner]
        else:  # list, retrieve
            permission_classes = [IsAuthenticated, IsTeacherOrAdminOrReadOnly]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request: DRFRequest) -> DRFResponse:
        """Регистрирует нового пользователя и возвращает данные созданной записи."""
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        response_serializer = UserRegisterResponseSerializer(user)
        return DRFResponse(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request: DRFRequest) -> DRFResponse:
            serializer = UserLoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            
            # 1. Генерируем токены во View
            refresh = RefreshToken.for_user(user)
            
            # 2. Динамически добавляем их как атрибуты к объекту юзера
            user.access = str(refresh.access_token)
            user.refresh = str(refresh)
            
            # 3. Прямо скармливаем объект юзера в сериализатор ответа!
            response_serializer = UserLoginResponseSerializer(user)
            
            return DRFResponse(response_serializer.data, status=status.HTTP_200_OK)

    def update(self, request: DRFRequest, pk=None) -> DRFResponse:
        """Обновляет профиль пользователя по переданному идентификатору."""
        user = self.get_object()
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()
        response_serializer = UserRegisterResponseSerializer(updated_user)
        return DRFResponse(response_serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request: DRFRequest, pk=None) -> DRFResponse:
        """Частичное обновление профиля пользователя (PATCH)."""
        return self.update(request, pk)

    def list(self, request: DRFRequest) -> DRFResponse:
        """Возвращает список всех пользователей."""
        users = CustomUser.objects.all()
        serializer = UserRegisterResponseSerializer(users, many=True)
        return DRFResponse(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request: DRFRequest, pk=None) -> DRFResponse:
        """Возвращает данные одного пользователя по его идентификатору."""
        user = self.get_object()
        serializer = UserRegisterResponseSerializer(user)
        return DRFResponse(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="me")
    def get_info(self, request: DRFRequest) -> DRFResponse:
        """Эндпоинт /users/me/ для получения инфы о себе по токену."""
        serializer = UserRegisterResponseSerializer(request.user)
        return DRFResponse(serializer.data, status=status.HTTP_200_OK)

    def get_queryset(self):
        """Базовый QuerySet для работы с пользователями."""
        return CustomUser.objects.all()
