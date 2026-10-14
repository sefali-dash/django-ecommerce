from django.apps import AppConfig


class CartConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cart"

    def ready(self):
        from django.db.models.signals import post_save
        from django.dispatch import receiver

        from accounts.models import User
        from cart.models import Cart

        @receiver(post_save, sender=User)
        def create_cart_for_user(sender, instance, created, **kwargs):
            if created:
                Cart.objects.get_or_create(user=instance)
