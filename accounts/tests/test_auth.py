from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthTests(APITestCase):
    def test_register_creates_non_staff_user(self):
        response = self.client.post(
            reverse("auth-register"),
            {"email": "new@example.com", "full_name": "New User", "password": "SecurePass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="new@example.com")
        self.assertFalse(user.is_staff)

    def test_login_returns_tokens(self):
        User.objects.create_user(email="login@example.com", full_name="Login", password="SecurePass123")
        response = self.client.post(
            reverse("auth-login"),
            {"email": "login@example.com", "password": "SecurePass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("users-me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh(self):
        user = User.objects.create_user(email="out@example.com", full_name="Out", password="SecurePass123")
        refresh = RefreshToken.for_user(user)
        self.client.force_authenticate(user=user)
        response = self.client.post(reverse("auth-logout"), {"refresh": str(refresh)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_admin_user_list_forbidden_for_customer(self):
        customer = User.objects.create_user(email="cust@example.com", full_name="Cust", password="SecurePass123")
        self.client.force_authenticate(user=customer)
        response = self.client.get(reverse("admin-users-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
