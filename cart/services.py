from django.db import transaction

from cart.models import Cart, CartItem
from catalog.models import Product


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@transaction.atomic
def add_item_to_cart(user, product, quantity):
    cart = get_or_create_cart(user)
    if product.stock_quantity < quantity:
        raise ValueError("Insufficient stock for requested quantity.")
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={"quantity": quantity})
    if not created:
        new_qty = item.quantity + quantity
        if product.stock_quantity < new_qty:
            raise ValueError("Insufficient stock for requested quantity.")
        item.quantity = new_qty
        item.save(update_fields=["quantity"])
    return item


def clear_cart(cart):
    cart.items.all().delete()
