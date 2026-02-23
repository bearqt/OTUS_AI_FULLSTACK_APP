from django.urls import path

from .views import MeView, MiniTrelloTokenObtainPairView, MiniTrelloTokenRefreshView, RegisterView


urlpatterns = [
  path("auth/register/", RegisterView.as_view(), name="auth-register"),
  path("auth/login/", MiniTrelloTokenObtainPairView.as_view(), name="auth-login"),
  path("auth/refresh/", MiniTrelloTokenRefreshView.as_view(), name="auth-refresh"),
  path("auth/me/", MeView.as_view(), name="auth-me"),
]
