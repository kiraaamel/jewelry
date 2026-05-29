from typing import Tuple, List, Dict, Any, Union
from .models import Order, OrderItem, ProductVariant, Cart
from django.contrib.auth import get_user_model

User = get_user_model()


def create_order_from_cart(cart: Cart, user: User, delivery_data: Dict[str, Any]) -> Order:
    """
    Создаёт заказ из корзины.

    Args:
        cart: Корзина пользователя
        user: Пользователь
        delivery_data: dict с данными доставки

    Returns:
        Созданный заказ

    Raises:
        ValueError: Если корзина пуста или недостаточно товара
    """
    if not cart.items.exists():
        raise ValueError("Корзина пуста")

    for cart_item in cart.items.all():
        variant = cart_item.variant
        if not variant:
            raise ValueError(f"У товара {cart_item.product.name} не указан вариант")

        if variant.available_quantity < cart_item.quantity:
            raise ValueError(
                f"Товара {cart_item.product.name} (размер {variant.size}) "
                f"доступно только {variant.available_quantity} шт."
            )

    order = Order.objects.create(
        user=user,
        total_price=cart.total_price,
        **delivery_data
    )

    for cart_item in cart.items.all():
        variant = cart_item.variant

        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            variant=variant,
            product_name=cart_item.product.name,
            size=variant.size,
            price=cart_item.product.price,
            quantity=cart_item.quantity
        )

        variant.stock_quantity -= cart_item.quantity
        variant.save()

    cart.items.all().delete()

    return order


def check_cart_items_availability(cart: Cart) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Проверяет доступность всех товаров в корзине.

    Args:
        cart: Корзина пользователя

    Returns:
        Кортеж (is_available, list_of_unavailable_items)
        - is_available: True если все товары доступны, иначе False
        - list_of_unavailable_items: Список недоступных товаров с деталями
    """
    unavailable_items: List[Dict[str, Any]] = []

    for cart_item in cart.items.all():
        variant = cart_item.variant
        if not variant or variant.available_quantity < cart_item.quantity:
            unavailable_items.append({
                'product_name': cart_item.product.name,
                'size': variant.size if variant else 'Не указан',
                'requested_quantity': cart_item.quantity,
                'available_quantity': variant.available_quantity if variant else 0
            })

    return len(unavailable_items) == 0, unavailable_items


def reserve_cart_items(cart: Cart) -> bool:
    """
    Резервирует товары в корзине (увеличивает reserved_quantity).

    Args:
        cart: Корзина пользователя

    Returns:
        True если успешно, False если не хватает товара
    """
    for cart_item in cart.items.all():
        variant = cart_item.variant
        if variant.available_quantity < cart_item.quantity:
            return False

        variant.reserved_quantity += cart_item.quantity
        variant.save()

    return True


def release_reserved_items(order: Order) -> None:
    """
    Освобождает зарезервированные товары (при отмене заказа).

    Args:
        order: Заказ, который отменяется
    """
    for order_item in order.items.all():
        variant = order_item.variant
        if variant:
            variant.reserved_quantity = max(0, variant.reserved_quantity - order_item.quantity)
            variant.save()


def clean_cart_before_order(cart: Cart) -> List[str]:
    """
    Удаляет из корзины товары, которых недостаточно на складе.

    Args:
        cart: Корзина пользователя

    Returns:
        Список названий удалённых товаров
    """
    removed_items: List[str] = []
    for item in cart.items.all():
        if item.variant.available_quantity < item.quantity:
            removed_items.append(item.product.name)
            item.delete()
    return removed_items