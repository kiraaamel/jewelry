from typing import Any, Type
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Model
from .models import User, Cart, Order


@receiver(post_save, sender=User)
def create_user_cart(sender: Type[User], instance: User, created: bool, **kwargs: Any) -> None:
    """
    При создании нового пользователя автоматически создаём для него корзину.

    Args:
        sender: Модель, отправившая сигнал (User)
        instance: Экземпляр созданного/сохранённого пользователя
        created: True если объект был создан, False если обновлён
        **kwargs: Дополнительные аргументы сигнала
    """
    if created:
        Cart.objects.get_or_create(user=instance)


@receiver(post_save, sender=Order)
def order_status_changed(sender: Type[Order], instance: Order, created: bool, **kwargs: Any) -> None:
    """
    При изменении статуса заказа отправляем уведомление.

    Args:
        sender: Модель, отправившая сигнал (Order)
        instance: Экземпляр сохранённого заказа
        created: True если объект был создан, False если обновлён
        **kwargs: Дополнительные аргументы сигнала

    Note:
        В текущей реализации уведомления закомментированы.
        Раскомментируйте вызов send_notification() при необходимости.
    """
    if not created and instance.pk:
        try:
            old_instance: Order = Order.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Здесь можно отправить email или push-уведомление
                # send_notification(instance.user, f"Статус заказа {instance.order_number} изменён на {instance.get_status_display()}")
                pass
        except Order.DoesNotExist:
            pass