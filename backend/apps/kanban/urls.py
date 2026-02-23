from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .views import router


@api_view(["GET"])
@permission_classes([AllowAny])
def healthcheck(_request):
  return Response({"status": "ok"})


urlpatterns = [
  path("health/", healthcheck, name="health"),
  path("", include(router.urls)),
]
