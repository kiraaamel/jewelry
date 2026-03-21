from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Cart, Order


@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    """
    При создании нового пользователя автоматически создаём для него корзину.
    """
    if created:
        Cart.objects.get_or_create(user=instance)

@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    """
    При изменении статуса заказа отправляем уведомление.
    """
    if not created and instance.pk:
        # Получаем предыдущий статус
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Здесь можно отправить email или push-уведомление
                # send_notification(instance.user, f"Статус заказа {instance.order_number} изменён на {instance.get_status_display()}")
                pass
        except Order.DoesNotExist:
            pass