from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cart.models import CartItem
from catalog.models import Category, Product

User = get_user_model()


class CartTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="cart@example.com", full_name="Cart", password="SecurePass123")
        self.other = User.objects.create_user(email="other@example.com", full_name="Other", password="SecurePass123")
        category = Category.objects.create(name="Cat", slug="cat")
        self.product = Product.objects.create(
            category=category,
            name="Item",
            slug="item",
            price=Decimal("10.00"),
            stock_quantity=5,
        )

    def test_add_to_cart(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("cart-item-create"),
            {"product": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cannot_access_other_users_cart_item(self):
        self.client.force_authenticate(user=self.user)
        create = self.client.post(
            reverse("cart-item-create"),
            {"product": self.product.id, "quantity": 1},
            format="json",
        )
        item_id = create.data["id"]
        self.client.force_authenticate(user=self.other)
        response = self.client.delete(reverse("cart-item-detail", kwargs={"pk": item_id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_clear_cart(self):
        self.client.force_authenticate(user=self.user)
        self.client.post(
            reverse("cart-item-create"),
            {"product": self.product.id, "quantity": 1},
            format="json",
        )
        response = self.client.delete(reverse("cart-clear"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.count(), 0)
