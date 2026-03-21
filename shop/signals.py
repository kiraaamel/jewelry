from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Cart


@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    """
    При создании нового пользователя автоматически создаём для него корзину.
    """
    if created:
        Cart.objects.get_or_create(user=instance)