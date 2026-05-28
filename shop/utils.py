from .models import Order, OrderItem, ProductVariant


def create_order_from_cart(cart, user, delivery_data):
    """
    Создаёт заказ из корзины.
    Возвращает созданный заказ.
    
    Args:
        cart: Корзина пользователя
        user: Пользователь
        delivery_data: dict с данными доставки
        
    Returns:
        Order: Созданный заказ
        
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


def check_cart_items_availability(cart):
    """
    Проверяет доступность всех товаров в корзине.
    
    Args:
        cart: Корзина пользователя
        
    Returns:
        tuple: (is_available, list_of_unavailable_items)
    """
    unavailable_items = []
    
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


def reserve_cart_items(cart):
    """
    Резервирует товары в корзине (увеличивает reserved_quantity).
    
    Args:
        cart: Корзина пользователя
        
    Returns:
        bool: True если успешно, False если не хватает товара
    """
    for cart_item in cart.items.all():
        variant = cart_item.variant
        if variant.available_quantity < cart_item.quantity:
            return False
        
        variant.reserved_quantity += cart_item.quantity
        variant.save()
    
    return True


def release_reserved_items(order):
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