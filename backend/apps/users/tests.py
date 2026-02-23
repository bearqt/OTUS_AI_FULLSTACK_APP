from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class AuthApiTests(APITestCase):
  def test_register_user_success(self):
    response = self.client.post(
      reverse("auth-register"),
      {
        "username": "tester",
        "email": "tester@example.com",
        "full_name": "Test User",
        "password": "S3curePass!123",
        "password_confirm": "S3curePass!123",
      },
      format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertTrue(User.objects.filter(username="tester").exists())

  def test_register_user_password_mismatch(self):
    response = self.client.post(
      reverse("auth-register"),
      {
        "username": "tester",
        "email": "tester@example.com",
        "password": "password123",
        "password_confirm": "different123",
      },
      format="json",
    )
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("password_confirm", response.data)

  def test_login_returns_jwt_pair_and_user(self):
    user = User.objects.create_user(username="alex", email="alex@example.com", password="password123")
    response = self.client.post(reverse("auth-login"), {"username": "alex", "password": "password123"}, format="json")
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertIn("access", response.data)
    self.assertIn("refresh", response.data)
    self.assertEqual(response.data["user"]["id"], user.id)

  def test_me_requires_authentication(self):
    response = self.client.get(reverse("auth-me"))
    self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
