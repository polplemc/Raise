"""
Email Notification System
Sends email notifications for critical events
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_email_notification(subject, recipient_email, template_name, context, fail_silently=True):
    """
    Send HTML email notification
    
    Args:
        subject: Email subject line
        recipient_email: Recipient's email address
        template_name: Template file name (without path)
        context: Context dictionary for template
        fail_silently: Whether to suppress errors
    
    Returns:
        Boolean indicating success
    """
    try:
        # Render HTML content
        html_content = render_to_string(f'emails/{template_name}', context)
        text_content = strip_tags(html_content)
        
        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send(fail_silently=fail_silently)
        logger.info(f"Email sent to {recipient_email}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
        if not fail_silently:
            raise
        return False


# Order-related email notifications
def send_order_placed_email(order, owner, supplier):
    """Notify supplier when owner places an order"""
    context = {
        'order': order,
        'owner': owner,
        'supplier': supplier,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject=f'New Order #{order.id} from {owner.first_name}',
        recipient_email=supplier.email,
        template_name='order_placed.html',
        context=context
    )


def send_order_confirmed_email(order, owner, supplier):
    """Notify owner when supplier confirms order"""
    context = {
        'order': order,
        'owner': owner,
        'supplier': supplier,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject=f'Order #{order.id} Confirmed',
        recipient_email=owner.email,
        template_name='order_confirmed.html',
        context=context
    )


def send_order_delivered_email(order, owner, supplier):
    """Notify owner when order is delivered"""
    context = {
        'order': order,
        'owner': owner,
        'supplier': supplier,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject=f'Order #{order.id} Delivered',
        recipient_email=owner.email,
        template_name='order_delivered.html',
        context=context
    )


# Payment-related email notifications
def send_payment_received_email(order, owner, supplier):
    """Notify supplier when payment is marked as paid"""
    context = {
        'order': order,
        'owner': owner,
        'supplier': supplier,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject=f'Payment Received for Order #{order.id}',
        recipient_email=supplier.email,
        template_name='payment_received.html',
        context=context
    )


def send_payment_verified_email(order, owner, supplier):
    """Notify owner when supplier verifies payment"""
    context = {
        'order': order,
        'owner': owner,
        'supplier': supplier,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject=f'Payment Verified for Order #{order.id}',
        recipient_email=owner.email,
        template_name='payment_verified.html',
        context=context
    )


# Stock-related email notifications
def send_low_stock_alert_email(product, supplier):
    """Notify supplier when product stock is low"""
    context = {
        'product': product,
        'supplier': supplier,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject=f'Low Stock Alert: {product.name}',
        recipient_email=supplier.email,
        template_name='low_stock_alert.html',
        context=context
    )


def send_out_of_stock_alert_email(product, supplier):
    """Notify supplier when product is out of stock"""
    context = {
        'product': product,
        'supplier': supplier,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject=f'OUT OF STOCK: {product.name}',
        recipient_email=supplier.email,
        template_name='out_of_stock_alert.html',
        context=context
    )


# Connection-related email notifications
def send_connection_request_email(connection_request, owner, supplier):
    """Notify supplier of new connection request"""
    context = {
        'connection_request': connection_request,
        'owner': owner,
        'supplier': supplier,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject=f'New Connection Request from {owner.first_name}',
        recipient_email=supplier.email,
        template_name='connection_request.html',
        context=context
    )


def send_connection_accepted_email(connection_request, owner, supplier):
    """Notify owner when connection is accepted"""
    context = {
        'connection_request': connection_request,
        'owner': owner,
        'supplier': supplier,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject=f'Connection Accepted by {supplier.first_name}',
        recipient_email=owner.email,
        template_name='connection_accepted.html',
        context=context
    )


# Staff-related email notifications
def send_staff_account_created_email(staff_user, owner, temp_password):
    """Notify staff member when account is created"""
    context = {
        'staff_user': staff_user,
        'owner': owner,
        'temp_password': temp_password,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject='Your Staff Account Has Been Created',
        recipient_email=staff_user.email,
        template_name='staff_account_created.html',
        context=context
    )


def send_password_reset_email(user, new_password):
    """Notify user when password is reset"""
    context = {
        'user': user,
        'new_password': new_password,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject='Your Password Has Been Reset',
        recipient_email=user.email,
        template_name='password_reset.html',
        context=context
    )


# Welcome email
def send_welcome_email(user, role):
    """Send welcome email to new users"""
    context = {
        'user': user,
        'role': role,
        'site_name': 'Raise Inventory System'
    }
    return send_email_notification(
        subject='Welcome to Raise Inventory System',
        recipient_email=user.email,
        template_name='welcome.html',
        context=context
    )


def send_user_approval_email(user, approved=True, rejection_reason=None):
    """
    Send email notification for user approval/rejection
    
    Args:
        user: User object
        approved: Boolean indicating if user was approved
        rejection_reason: String with rejection reason (if rejected)
    
    Returns:
        Boolean indicating success
    """
    if approved:
        subject = 'Account Approved - Welcome to Raise Inventory System'
        template_name = 'user_approved.html'
        context = {
            'user': user,
            'full_name': user.first_name or user.username,
            'login_url': f"{settings.DEFAULT_FROM_EMAIL.split('@')[1]}/login/",  # Basic URL construction
        }
    else:
        subject = 'Account Registration Update - Raise Inventory System'
        template_name = 'user_rejected.html'
        context = {
            'user': user,
            'full_name': user.first_name or user.username,
            'rejection_reason': rejection_reason,
            'signup_url': f"{settings.DEFAULT_FROM_EMAIL.split('@')[1]}/signup/",  # Basic URL construction
        }
    
    return send_email_notification(
        subject=subject,
        recipient_email=user.email,
        template_name=template_name,
        context=context
    )


def send_admin_new_user_notification(user):
    """
    Send email notification to admin about new user registration
    
    Args:
        user: User object who registered
    
    Returns:
        Boolean indicating success
    """
    from django.contrib.auth.models import User
    
    # Get all superusers
    admin_emails = User.objects.filter(is_superuser=True).values_list('email', flat=True)
    
    if not admin_emails:
        logger.warning("No admin emails found for new user notification")
        return False
    
    subject = f'New User Registration Pending Approval - {user.username}'
    template_name = 'admin_new_user.html'
    context = {
        'user': user,
        'profile': user.profile,
        'full_name': user.first_name or user.username,
        'admin_url': f"{settings.DEFAULT_FROM_EMAIL.split('@')[1]}/sysadmin/pending-users/",
    }
    
    success = True
    for admin_email in admin_emails:
        if admin_email:  # Skip empty emails
            result = send_email_notification(
                subject=subject,
                recipient_email=admin_email,
                template_name=template_name,
                context=context
            )
            if not result:
                success = False
    
    return success
