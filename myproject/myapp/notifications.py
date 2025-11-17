"""
Notification utility functions for creating system notifications
"""
from django.utils import timezone
from .models import Notification, Message


def create_notification(recipient, notification_type, title, message, sender=None, related_order=None, related_product=None):
    """
    Create a notification for a user
    
    Args:
        recipient: User who will receive the notification
        notification_type: Type of notification (from NOTIFICATION_TYPES)
        title: Notification title
        message: Notification message
        sender: User who triggered the notification (optional)
        related_order: Related SupplierOrder (optional)
        related_product: Related SupplierProduct (optional)
    
    Returns:
        Created Notification object
    """
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=message,
        related_order=related_order,
        related_product=related_product
    )
    return notification


def notify_order_placed(order, sender):
    """Notify supplier when owner places an order"""
    supplier = order.supplier_product.supplier
    return create_notification(
        recipient=supplier,
        notification_type='order_placed',
        title=f'New Order #{order.id}',
        message=f'{sender.first_name or sender.username} placed an order for {order.quantity} {order.supplier_product.unit} of {order.supplier_product.name}. Total: ₱{order.total_amount}',
        sender=sender,
        related_order=order
    )


def notify_order_status_change(order, old_status, new_status, updated_by):
    """Notify owner when supplier updates order status"""
    owner = order.store_owner
    
    status_messages = {
        'confirmed': f'Your order #{order.id} has been confirmed by the supplier.',
        'processing': f'Your order #{order.id} is now being processed.',
        'completed': f'Your order #{order.id} has been completed!',
        'cancelled': f'Your order #{order.id} has been cancelled.',
    }
    
    return create_notification(
        recipient=owner,
        notification_type=f'order_{new_status}',
        title=f'Order #{order.id} Status Updated',
        message=status_messages.get(new_status, f'Order status changed to {new_status}'),
        sender=updated_by,
        related_order=order
    )


def notify_delivery_status_change(order, old_status, new_status, updated_by):
    """Notify owner when supplier updates delivery status"""
    owner = order.store_owner
    
    status_messages = {
        'out_for_delivery': f'Your order #{order.id} is out for delivery!',
        'delivered': f'Your order #{order.id} has been delivered successfully.',
        'returned': f'Your order #{order.id} has been returned.',
    }
    
    notification_type = 'delivery_' + new_status.replace('_', '')
    if notification_type not in ['delivery_shipped', 'delivery_out', 'delivery_delivered']:
        notification_type = 'system'
    
    return create_notification(
        recipient=owner,
        notification_type=notification_type,
        title=f'Delivery Update - Order #{order.id}',
        message=status_messages.get(new_status, f'Delivery status changed to {new_status}'),
        sender=updated_by,
        related_order=order
    )


def notify_payment_status_change(order, new_status, updated_by):
    """Notify supplier when owner marks payment as paid"""
    supplier = order.supplier_product.supplier
    
    if new_status == 'paid':
        return create_notification(
            recipient=supplier,
            notification_type='payment_paid',
            title=f'Payment Received - Order #{order.id}',
            message=f'{updated_by.first_name or updated_by.username} marked the payment for order #{order.id} as paid. Please verify the payment.',
            sender=updated_by,
            related_order=order
        )


def notify_payment_verified(order, verified_by):
    """Notify owner when supplier verifies payment"""
    owner = order.store_owner
    
    return create_notification(
        recipient=owner,
        notification_type='payment_verified',
        title=f'Payment Verified - Order #{order.id}',
        message=f'The supplier has verified receiving your payment for order #{order.id}.',
        sender=verified_by,
        related_order=order
    )


def notify_low_stock(product, owner):
    """Notify owner about low stock"""
    return create_notification(
        recipient=owner,
        notification_type='stock_low',
        title=f'Low Stock Alert: {product.name}',
        message=f'{product.name} is running low. Current stock: {product.available_stock} {product.unit}. Threshold: {product.low_stock_threshold} {product.unit}',
        related_product=product
    )


def notify_out_of_stock(product, owner):
    """Notify owner about out of stock"""
    return create_notification(
        recipient=owner,
        notification_type='stock_out',
        title=f'Out of Stock: {product.name}',
        message=f'{product.name} is out of stock! Please restock as soon as possible.',
        related_product=product
    )


def notify_new_message(message_obj):
    """Notify recipient about new message"""
    return create_notification(
        recipient=message_obj.recipient,
        notification_type='new_message',
        title=f'New Message from {message_obj.sender.first_name or message_obj.sender.username}',
        message=message_obj.body[:100] + ('...' if len(message_obj.body) > 100 else ''),
        sender=message_obj.sender,
        related_order=message_obj.related_order
    )


def get_unread_notification_count(user):
    """Get count of unread notifications for a user"""
    return Notification.objects.filter(recipient=user, is_read=False).count()


def get_unread_message_count(user):
    """Get count of unread messages for a user"""
    return Message.objects.filter(recipient=user, is_read=False).count()


def mark_all_notifications_read(user):
    """Mark all notifications as read for a user"""
    Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
