from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cart.models import Cart, CartItem
from catalog.models import Category, Product
from orders.models import Order

User = get_user_model()

TEST_REST_FRAMEWORK = {
    **settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
}


@override_settings(REST_FRAMEWORK=TEST_REST_FRAMEWORK)
class APIInventoryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Electronics", slug="electronics")
        cls.product = Product.objects.create(
            category=cls.category,
            name="Wireless Phone",
            slug="wireless-phone",
            description="A compact phone",
            price=Decimal("499.99"),
            stock_quantity=20,
            is_active=True,
        )
        Product.objects.create(
            category=cls.category,
            name="Old Gadget",
            slug="old-gadget",
            price=Decimal("10.00"),
            stock_quantity=2,
            is_active=False,
        )
        cls.admin = User.objects.create_user(
            email="admin@test.com",
            full_name="Admin User",
            password="AdminPass123!",
            is_staff=True,
        )

    def _login(self, email, password):
        response = self.client.post(
            reverse("auth-login"),
            {"email": email, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data["access"], response.data["refresh"]

    def test_full_api_inventory(self):
        register = self.client.post(
            reverse("auth-register"),
            {
                "email": "customer@test.com",
                "full_name": "Customer One",
                "password": "CustomerPass123!",
            },
            format="json",
        )
        self.assertEqual(register.status_code, status.HTTP_201_CREATED)
        customer = User.objects.get(email="customer@test.com")
        self.assertFalse(customer.is_staff)

        access, refresh = self._login("customer@test.com", "CustomerPass123!")

        refresh_resp = self.client.post(
            reverse("auth-token-refresh"),
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_resp.data)

        self.client.force_authenticate(user=customer)
        me = self.client.get(reverse("users-me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], "customer@test.com")

        patch_me = self.client.patch(
            reverse("users-me"),
            {"full_name": "Customer Updated"},
            format="json",
        )
        self.assertEqual(patch_me.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_me.data["full_name"], "Customer Updated")

        pwd = self.client.patch(
            reverse("users-me-password"),
            {"old_password": "CustomerPass123!", "new_password": "NewCustomerPass123!"},
            format="json",
        )
        self.assertEqual(pwd.status_code, status.HTTP_200_OK)
        access, refresh = self._login("customer@test.com", "NewCustomerPass123!")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        logout = self.client.post(reverse("auth-logout"), {"refresh": refresh}, format="json")
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        access, refresh = self._login("customer@test.com", "NewCustomerPass123!")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        cat_list = self.client.get(reverse("category-list"))
        self.assertEqual(cat_list.status_code, status.HTTP_200_OK)

        cat_detail = self.client.get(reverse("category-detail", kwargs={"pk": self.category.pk}))
        self.assertEqual(cat_detail.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=customer)
        cat_create = self.client.post(
            reverse("category-list"),
            {"name": "Blocked", "slug": "blocked"},
            format="json",
        )
        self.assertEqual(cat_create.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        new_cat = self.client.post(
            reverse("category-list"),
            {"name": "Home", "slug": "home"},
            format="json",
        )
        self.assertEqual(new_cat.status_code, status.HTTP_201_CREATED)
        home_id = new_cat.data["id"]

        cat_patch = self.client.patch(
            reverse("category-detail", kwargs={"pk": home_id}),
            {"name": "Home & Living"},
            format="json",
        )
        self.assertEqual(cat_patch.status_code, status.HTTP_200_OK)

        empty_cat = self.client.post(
            reverse("category-list"),
            {"name": "Empty", "slug": "empty"},
            format="json",
        )
        empty_id = empty_cat.data["id"]
        cat_delete = self.client.delete(reverse("category-detail", kwargs={"pk": empty_id}))
        self.assertEqual(cat_delete.status_code, status.HTTP_204_NO_CONTENT)

        cat_delete_blocked = self.client.delete(
            reverse("category-detail", kwargs={"pk": self.category.pk})
        )
        self.assertEqual(cat_delete_blocked.status_code, status.HTTP_409_CONFLICT)

        self.client.force_authenticate(user=None)
        products = self.client.get(reverse("product-list"))
        self.assertEqual(products.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in products.data["results"]]
        self.assertIn("Wireless Phone", names)
        self.assertNotIn("Old Gadget", names)

        product_detail = self.client.get(reverse("product-detail", kwargs={"pk": self.product.pk}))
        self.assertEqual(product_detail.status_code, status.HTTP_200_OK)

        search = self.client.get(reverse("product-list"), {"q": "phone"})
        self.assertEqual(search.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(search.data["count"], 1)

        filtered = self.client.get(reverse("product-list"), {"category": self.category.pk})
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.admin)
        admin_product = self.client.post(
            reverse("product-list"),
            {
                "category": home_id,
                "name": "Desk Lamp",
                "slug": "desk-lamp",
                "description": "LED lamp",
                "price": "34.00",
                "stock_quantity": 4,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(admin_product.status_code, status.HTTP_201_CREATED)
        lamp_id = admin_product.data["id"]

        product_patch = self.client.patch(
            reverse("product-detail", kwargs={"pk": lamp_id}),
            {"price": "39.00"},
            format="json",
        )
        self.assertEqual(product_patch.status_code, status.HTTP_200_OK)

        low_stock = self.client.get(reverse("admin-products-low-stock"))
        self.assertEqual(low_stock.status_code, status.HTTP_200_OK)

        product_delete = self.client.delete(reverse("product-detail", kwargs={"pk": lamp_id}))
        self.assertEqual(product_delete.status_code, status.HTTP_204_NO_CONTENT)

        self.client.force_authenticate(user=customer)
        cart_get = self.client.get(reverse("cart-detail"))
        self.assertEqual(cart_get.status_code, status.HTTP_200_OK)

        add_item = self.client.post(
            reverse("cart-item-create"),
            {"product": self.product.pk, "quantity": 2},
            format="json",
        )
        self.assertEqual(add_item.status_code, status.HTTP_201_CREATED)
        item_id = add_item.data["id"]

        update_item = self.client.patch(
            reverse("cart-item-detail", kwargs={"pk": item_id}),
            {"quantity": 1},
            format="json",
        )
        self.assertEqual(update_item.status_code, status.HTTP_200_OK)

        checkout = self.client.post(reverse("order-list-create"), format="json")
        self.assertEqual(checkout.status_code, status.HTTP_201_CREATED)
        order_id = checkout.data["id"]
        self.assertEqual(checkout.data["total_amount"], "499.99")

        orders_list = self.client.get(reverse("order-list-create"))
        self.assertEqual(orders_list.status_code, status.HTTP_200_OK)

        order_detail = self.client.get(reverse("order-detail", kwargs={"pk": order_id}))
        self.assertEqual(order_detail.status_code, status.HTTP_200_OK)

        self.client.post(
            reverse("cart-item-create"),
            {"product": self.product.pk, "quantity": 1},
            format="json",
        )
        second_order = self.client.post(reverse("order-list-create"), format="json")
        self.assertEqual(second_order.status_code, status.HTTP_201_CREATED)
        second_id = second_order.data["id"]

        cancel = self.client.post(reverse("order-cancel", kwargs={"pk": second_id}), format="json")
        self.assertEqual(cancel.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel.data["status"], Order.Status.CANCELLED)

        clear = self.client.delete(reverse("cart-clear"))
        self.assertEqual(clear.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CartItem.objects.filter(cart__user=customer).count(), 0)

        self.client.force_authenticate(user=self.admin)
        users_list = self.client.get(reverse("admin-users-list"))
        self.assertEqual(users_list.status_code, status.HTTP_200_OK)

        status_patch = self.client.patch(
            reverse("admin-users-status", kwargs={"pk": customer.pk}),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(status_patch.status_code, status.HTTP_200_OK)

        self.client.patch(
            reverse("admin-users-status", kwargs={"pk": customer.pk}),
            {"is_active": True},
            format="json",
        )

        dashboard = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(dashboard.status_code, status.HTTP_200_OK)
        self.assertIn("orders_count", dashboard.data)

        admin_orders = self.client.get(reverse("admin-orders-list"))
        self.assertEqual(admin_orders.status_code, status.HTTP_200_OK)

        order_status = self.client.patch(
            reverse("admin-orders-status", kwargs={"pk": order_id}),
            {"status": Order.Status.CONFIRMED},
            format="json",
        )
        self.assertEqual(order_status.status_code, status.HTTP_200_OK)

        remove_item = self.client.delete(reverse("cart-item-detail", kwargs={"pk": item_id}))
        if remove_item.status_code == status.HTTP_404_NOT_FOUND:
            pass
        else:
            self.assertEqual(remove_item.status_code, status.HTTP_204_NO_CONTENT)

        schema = self.client.get(reverse("schema"))
        self.assertEqual(schema.status_code, status.HTTP_200_OK)

        docs = self.client.get(reverse("swagger-ui"))
        self.assertEqual(docs.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=None)
        anon_me = self.client.get(reverse("users-me"))
        self.assertEqual(anon_me.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=customer)
        admin_forbidden = self.client.get(reverse("admin-dashboard"))
        self.assertEqual(admin_forbidden.status_code, status.HTTP_403_FORBIDDEN)
