from .models import Order, OrderItem


def create_order_from_cart(cart, user, delivery_data):
    """
    Создаёт заказ из корзины.
    Возвращает созданный заказ.
    """
    if not cart.items.exists():
        raise ValueError("Корзина пуста")
    
    # Создаём заказ
    order = Order.objects.create(
        user=user,
        total_price=cart.total_price,
        **delivery_data
    )
    
    # Копируем товары из корзины в OrderItem и уменьшаем остатки
    for cart_item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            product_name=cart_item.product.name,
            price=cart_item.product.price,
            quantity=cart_item.quantity
        )
        
        # Уменьшаем количество товара на складе
        product = cart_item.product
        product.stock_quantity -= cart_item.quantity
        product.save()
    
    # Очищаем корзину
    cart.items.all().delete()
    
    return order