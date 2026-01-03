from main.models import Order, OrderItem

def create_order_from_cart(user):
    """
    Create a new order for the given user from their cart items.
    """
    cart = user.cart
    order = Order.objects.create(buyer=user)

    total = 0
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            book=item.book,
            quantity=item.quantity,
            price=item.book.price
        )
        total += item.book.price * item.quantity

    order.total_price = total
    order.save()

    cart.items.all().delete()

    return order



