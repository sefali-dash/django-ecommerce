from decimal import Decimal

from django.db import transaction
from django.db.models import F

from cart.models import Cart
from cart.services import clear_cart
from catalog.models import Product
from orders.models import Order, OrderItem

CANCELLABLE_STATUSES = {Order.Status.PENDING, Order.Status.CONFIRMED}

ADMIN_STATUS_TRANSITIONS = {
    Order.Status.PENDING: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.SHIPPED, Order.Status.CANCELLED},
    Order.Status.SHIPPED: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: set(),
    Order.Status.CANCELLED: set(),
}


class CheckoutError(Exception):
    def __init__(self, message, code="checkout_error"):
        self.message = message
        self.code = code
        super().__init__(message)


@transaction.atomic
def place_order_from_cart(user):
    try:
        cart = Cart.objects.select_for_update().get(user=user)
    except Cart.DoesNotExist:
        raise CheckoutError("Cart is empty.", code="empty_cart")

    items = list(cart.items.select_related("product").select_for_update())
    if not items:
        raise CheckoutError("Cart is empty.", code="empty_cart")

    product_ids = [item.product_id for item in items]
    products = {
        p.id: p
        for p in Product.objects.select_for_update().filter(id__in=product_ids, is_active=True)
    }

    total = Decimal("0.00")
    snapshots = []
    for item in items:
        product = products.get(item.product_id)
        if not product:
            raise CheckoutError(f"Product {item.product_id} is unavailable.", code="invalid_product")
        if product.stock_quantity < item.quantity:
            raise CheckoutError(
                f"Not enough stock for {product.name}.",
                code="insufficient_stock",
            )
        line_total = product.price * item.quantity
        total += line_total
        snapshots.append((product, item.quantity, line_total))

    order = Order.objects.create(user=user, status=Order.Status.PENDING, total_amount=total)

    for product, quantity, line_total in snapshots:
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit_price=product.price,
            quantity=quantity,
            line_total=line_total,
        )
        updated = Product.objects.filter(
            pk=product.pk,
            stock_quantity__gte=quantity,
        ).update(stock_quantity=F("stock_quantity") - quantity)
        if updated == 0:
            raise CheckoutError(
                f"Not enough stock for {product.name}.",
                code="insufficient_stock",
            )

    clear_cart(cart)
    return order


def _restore_stock(order):
    if order.stock_restored:
        return
    for line in order.items.select_related("product"):
        if line.product_id:
            Product.objects.filter(pk=line.product_id).update(
                stock_quantity=F("stock_quantity") + line.quantity
            )
    order.stock_restored = True
    order.save(update_fields=["stock_restored", "updated_at"])


@transaction.atomic
def cancel_order(order, *, by_user=False):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == Order.Status.CANCELLED:
        return order
    if by_user and order.status not in CANCELLABLE_STATUSES:
        raise CheckoutError("This order cannot be cancelled.", code="not_cancellable")
    if order.status not in CANCELLABLE_STATUSES and not by_user:
        raise CheckoutError("Invalid status transition.", code="invalid_transition")

    _restore_stock(order)
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def update_order_status(order, new_status):
    order = Order.objects.select_for_update().get(pk=order.pk)
    allowed = ADMIN_STATUS_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise CheckoutError(
            f"Cannot change status from {order.status} to {new_status}.",
            code="invalid_transition",
        )
    if new_status == Order.Status.CANCELLED:
        return cancel_order(order, by_user=False)
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    return order
