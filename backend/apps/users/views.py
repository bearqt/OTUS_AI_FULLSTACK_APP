from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import MiniTrelloTokenObtainPairSerializer, RegisterSerializer, UserSerializer


class RegisterView(APIView):
  permission_classes = [permissions.AllowAny]

  @extend_schema(
    tags=["Auth"],
    request=RegisterSerializer,
    responses={201: UserSerializer},
    examples=[
      OpenApiExample(
        "Register",
        value={
          "username": "alex",
          "email": "alex@example.com",
          "full_name": "Alex Doe",
          "password": "password123",
          "password_confirm": "password123",
        },
      )
    ],
  )
  def post(self, request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
  @extend_schema(tags=["Auth"], responses={200: UserSerializer})
  def get(self, request):
    return Response(UserSerializer(request.user).data)


class MiniTrelloTokenObtainPairView(TokenObtainPairView):
  permission_classes = [permissions.AllowAny]
  serializer_class = MiniTrelloTokenObtainPairSerializer

  @extend_schema(tags=["Auth"])
  def post(self, request, *args, **kwargs):
    return super().post(request, *args, **kwargs)


class MiniTrelloTokenRefreshView(TokenRefreshView):
  permission_classes = [permissions.AllowAny]

  @extend_schema(tags=["Auth"])
  def post(self, request, *args, **kwargs):
    return super().post(request, *args, **kwargs)
