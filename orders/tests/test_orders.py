from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cart.models import Cart, CartItem
from catalog.models import Category, Product
from orders.models import Order

User = get_user_model()


class OrderTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="buy@example.com", full_name="Buy", password="SecurePass123")
        self.other = User.objects.create_user(email="other2@example.com", full_name="Other", password="SecurePass123")
        self.admin = User.objects.create_user(
            email="adm@example.com",
            full_name="Adm",
            password="SecurePass123",
            is_staff=True,
        )
        category = Category.objects.create(name="Shop", slug="shop")
        self.product = Product.objects.create(
            category=category,
            name="Widget",
            slug="widget",
            price=Decimal("25.00"),
            stock_quantity=10,
        )
        cart = Cart.objects.get(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

    def test_checkout_creates_order_and_clears_cart(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("order-list-create"), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["total_amount"], "50.00")
        self.assertEqual(CartItem.objects.filter(cart__user=self.user).count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_checkout_insufficient_stock(self):
        self.product.stock_quantity = 1
        self.product.save()
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("order-list-create"), format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_user_cannot_read_other_order(self):
        self.client.force_authenticate(user=self.user)
        created = self.client.post(reverse("order-list-create"), format="json")
        order_id = created.data["id"]
        self.client.force_authenticate(user=self.other)
        response = self.client.get(reverse("order-detail", kwargs={"pk": order_id}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_restores_stock_once(self):
        self.client.force_authenticate(user=self.user)
        created = self.client.post(reverse("order-list-create"), format="json")
        order_id = created.data["id"]
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)
        cancel = self.client.post(reverse("order-cancel", kwargs={"pk": order_id}), format="json")
        self.assertEqual(cancel.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        again = self.client.post(reverse("order-cancel", kwargs={"pk": order_id}), format="json")
        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

    def test_admin_status_transition(self):
        self.client.force_authenticate(user=self.user)
        created = self.client.post(reverse("order-list-create"), format="json")
        order_id = created.data["id"]
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("admin-orders-status", kwargs={"pk": order_id}),
            {"status": Order.Status.CONFIRMED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        bad = self.client.patch(
            reverse("admin-orders-status", kwargs={"pk": order_id}),
            {"status": Order.Status.PENDING},
            format="json",
        )
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
