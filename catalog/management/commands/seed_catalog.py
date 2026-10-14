from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Category, Product


class Command(BaseCommand):
    help = "Load sample categories and products for local development."

    def handle(self, *args, **options):
        electronics, _ = Category.objects.get_or_create(
            slug="electronics",
            defaults={"name": "Electronics"},
        )
        home, _ = Category.objects.get_or_create(
            slug="home",
            defaults={"name": "Home"},
        )

        samples = [
            ("wireless-phone", "Wireless Phone", electronics, "Compact smartphone", "499.99", 25),
            ("bluetooth-speaker", "Bluetooth Speaker", electronics, "Portable speaker", "79.50", 40),
            ("desk-lamp", "Desk Lamp", home, "LED desk lamp", "34.00", 8),
            ("coffee-mug", "Coffee Mug", home, "Ceramic mug", "12.99", 3),
        ]

        for slug, name, category, description, price, stock in samples:
            Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": category,
                    "description": description,
                    "price": Decimal(price),
                    "stock_quantity": stock,
                    "is_active": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Sample catalog data loaded."))
