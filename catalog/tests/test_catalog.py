from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, Product

User = get_user_model()


class CatalogTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Gadgets", slug="gadgets")
        self.product = Product.objects.create(
            category=self.category,
            name="Phone",
            slug="phone",
            description="A phone",
            price=Decimal("100.00"),
            stock_quantity=10,
            is_active=True,
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            full_name="Admin",
            password="SecurePass123",
            is_staff=True,
        )

    def test_public_product_list_hides_inactive(self):
        Product.objects.create(
            category=self.category,
            name="Hidden",
            slug="hidden",
            price=Decimal("1.00"),
            stock_quantity=1,
            is_active=False,
        )
        response = self.client.get(reverse("product-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["results"]]
        self.assertIn("Phone", names)
        self.assertNotIn("Hidden", names)

    def test_product_search(self):
        response = self.client.get(reverse("product-list"), {"q": "phone"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_category_filter(self):
        response = self.client.get(reverse("product-list"), {"category": self.category.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_customer_cannot_create_category(self):
        user = User.objects.create_user(email="u@example.com", full_name="U", password="SecurePass123")
        self.client.force_authenticate(user=user)
        response = self.client.post(
            reverse("category-list"),
            {"name": "New", "slug": "new"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_category(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse("category-list"),
            {"name": "Books", "slug": "books"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_category_with_products_returns_409(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(reverse("category-detail", kwargs={"pk": self.category.pk}))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
