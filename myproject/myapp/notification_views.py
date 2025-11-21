"""
Views for Notifications and Messages system
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Notification, Message, Conversation, SupplierOrder, User, Supplier
from .forms import MessageForm, QuickMessageForm
from .notifications import create_notification, notify_new_message, get_unread_notification_count, get_unread_message_count


@login_required
def notification_list(request):
    """List all notifications for the current user"""
    notifications = Notification.objects.filter(recipient=request.user).select_related(
        'sender', 'related_order', 'related_product'
    )
    
    # Filter by read/unread
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_type == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Determine base template based on user role
    role = request.user.profile.role
    if role == 'owner':
        base_template = 'owner/base.html'
    elif role == 'supplier':
        base_template = 'supplier/base.html'
    else:
        base_template = 'staff/base.html'
    
    context = {
        'notifications': page_obj,
        'unread_count': get_unread_notification_count(request.user),
        'filter_type': filter_type,
        'base_template': base_template,
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
def notification_detail(request, pk):
    """View a single notification and mark as read"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    
    # Determine base template based on user role
    role = request.user.profile.role
    if role == 'owner':
        base_template = 'owner/base.html'
    elif role == 'supplier':
        base_template = 'supplier/base.html'
    else:
        base_template = 'staff/base.html'
    
    context = {
        'notification': notification,
        'base_template': base_template,
    }
    return render(request, 'notifications/notification_detail.html', context)


@login_required
def mark_notification_read(request, pk):
    """Mark a notification as read (AJAX)"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_as_read()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'unread_count': get_unread_notification_count(request.user)})
    return redirect('notification_list')


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    django_messages.success(request, 'All notifications marked as read.')
    return redirect('notification_list')


@login_required
def delete_notification(request, pk):
    """Delete a notification"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.delete()
    django_messages.success(request, 'Notification deleted.')
    return redirect('notification_list')


@login_required
def get_notifications_json(request):
    """Get recent notifications as JSON (for AJAX polling)"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender', 'related_order').order_by('-created_at')[:10]
    
    data = {
        'unread_count': get_unread_notification_count(request.user),
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'notification_type': n.notification_type,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
                'sender': n.sender.first_name or n.sender.username if n.sender else 'System',
            }
            for n in notifications
        ]
    }
    return JsonResponse(data)


# ========== MESSAGING VIEWS ==========

@login_required
def message_list(request):
    """List all conversations for the current user and show connected contacts"""
    # Get all conversations where user is either user1 or user2
    conversations = Conversation.objects.filter(
        Q(user1=request.user) | Q(user2=request.user)
    ).select_related('user1', 'user2', 'related_order')

    # Build conversation summary data
    conversation_data = []
    for conv in conversations:
        other_user = conv.get_other_user(request.user)
        unread_count = conv.get_unread_count(request.user)
        last_message = Message.objects.filter(
            Q(sender=conv.user1, recipient=conv.user2)
            | Q(sender=conv.user2, recipient=conv.user1)
        ).order_by('-created_at').first()

        conversation_data.append({
            'conversation': conv,
            'other_user': other_user,
            'unread_count': unread_count,
            'last_message': last_message,
        })

    # Determine base template and connected contacts based on user role
    role = request.user.profile.role
    contacts = []

    if role == 'owner':
        base_template = 'owner/base.html'
        owner_connections = Supplier.objects.filter(
            owner=request.user,
            supplier_profile__isnull=False,
            supplier_profile__user__isnull=False,
        ).select_related('supplier_profile__user')
        for conn in owner_connections:
            contacts.append({
                'user': conn.supplier_profile.user,
                'label': conn.name or conn.supplier_profile.business_name,
            })
    elif role == 'supplier':
        base_template = 'supplier/base.html'
        if hasattr(request.user, 'supplier_profile'):
            owner_connections = Supplier.objects.filter(
                supplier_profile=request.user.supplier_profile,
            ).select_related('owner')
            for conn in owner_connections:
                contacts.append({
                    'user': conn.owner,
                    'label': conn.owner.first_name or conn.owner.username,
                })
    else:
        base_template = 'staff/base.html'

    context = {
        'conversations': conversation_data,
        'total_unread': get_unread_message_count(request.user),
        'base_template': base_template,
        'contacts': contacts,
    }
    return render(request, 'messages/message_list.html', context)


@login_required
def conversation_detail(request, pk):
    """View a conversation and send messages"""
    conversation = get_object_or_404(
        Conversation,
        Q(user1=request.user) | Q(user2=request.user),
        pk=pk
    )
    
    other_user = conversation.get_other_user(request.user)
    
    # Mark all messages in this conversation as read
    Message.objects.filter(
        sender=other_user,
        recipient=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())
    
    # Handle message sending
    if request.method == 'POST':
        form = QuickMessageForm(request.POST)
        if form.is_valid():
            message = Message.objects.create(
                sender=request.user,
                recipient=other_user,
                body=form.cleaned_data['message'],
                related_order=conversation.related_order
            )
            
            # Create notification for recipient
            notify_new_message(message)
            
            # Update conversation timestamp
            conversation.last_message_at = timezone.now()
            conversation.save()
            
            django_messages.success(request, 'Message sent!')
            return redirect('conversation_detail', pk=conversation.pk)
    else:
        form = QuickMessageForm()
    
    # Get all messages in conversation
    conversation_messages = conversation.get_messages()
    
    # Determine base template based on user role
    role = request.user.profile.role
    if role == 'owner':
        base_template = 'owner/base.html'
    elif role == 'supplier':
        base_template = 'supplier/base.html'
    else:
        base_template = 'staff/base.html'
    
    context = {
        'conversation': conversation,
        'other_user': other_user,
        'messages': conversation_messages,
        'form': form,
        'base_template': base_template,
    }
    return render(request, 'messages/conversation_detail.html', context)


@login_required
def send_message_to_order(request, order_id):
    """Send a message related to a specific order"""
    order = get_object_or_404(SupplierOrder, pk=order_id)
    
    # Determine recipient based on user role
    if request.user == order.store_owner:
        recipient = order.supplier_product.supplier
    elif request.user == order.supplier_product.supplier:
        recipient = order.store_owner
    else:
        django_messages.error(request, 'You do not have permission to message about this order.')
        return redirect('owner_supplier_order_detail', pk=order_id)
    
    if request.method == 'POST':
        form = QuickMessageForm(request.POST)
        if form.is_valid():
            # Create or get conversation
            conversation, created = Conversation.objects.get_or_create(
                user1=min(request.user, recipient, key=lambda u: u.id),
                user2=max(request.user, recipient, key=lambda u: u.id),
                related_order=order
            )
            
            # Create message
            message = Message.objects.create(
                sender=request.user,
                recipient=recipient,
                body=form.cleaned_data['message'],
                related_order=order
            )
            
            # Create notification
            notify_new_message(message)
            
            # Update conversation
            conversation.last_message_at = timezone.now()
            conversation.save()
            
            django_messages.success(request, 'Message sent!')
            return redirect('conversation_detail', pk=conversation.pk)
    else:
        form = QuickMessageForm()
    
    context = {
        'order': order,
        'recipient': recipient,
        'form': form,
    }
    return render(request, 'messages/send_message.html', context)


@login_required
def start_conversation(request, user_id):
    """Start a new conversation with a user"""
    other_user = get_object_or_404(User, pk=user_id)
    user_profile = request.user.profile
    role = user_profile.role

    allowed = None
    if role == 'owner':
        owner_connections = Supplier.objects.filter(
            owner=request.user,
            supplier_profile__isnull=False,
            supplier_profile__user__isnull=False,
        ).select_related('supplier_profile__user')
        allowed = {s.supplier_profile.user for s in owner_connections}
    elif role == 'supplier':
        if hasattr(request.user, 'supplier_profile'):
            owner_connections = Supplier.objects.filter(
                supplier_profile=request.user.supplier_profile,
            ).select_related('owner')
            allowed = {s.owner for s in owner_connections}

    if allowed is not None and other_user not in allowed:
        django_messages.error(request, 'You can only message users you are connected with.')
        return redirect('message_list')
    
    # Check if conversation already exists
    existing_conv = Conversation.objects.filter(
        Q(user1=request.user, user2=other_user) |
        Q(user1=other_user, user2=request.user)
    ).first()
    
    if existing_conv:
        return redirect('conversation_detail', pk=existing_conv.pk)
    
    if request.method == 'POST':
        form = QuickMessageForm(request.POST)
        if form.is_valid():
            # Create conversation
            conversation = Conversation.objects.create(
                user1=min(request.user, other_user, key=lambda u: u.id),
                user2=max(request.user, other_user, key=lambda u: u.id)
            )
            
            # Create first message
            message = Message.objects.create(
                sender=request.user,
                recipient=other_user,
                body=form.cleaned_data['message']
            )
            
            # Create notification
            notify_new_message(message)
            
            django_messages.success(request, 'Conversation started!')
            return redirect('conversation_detail', pk=conversation.pk)
    else:
        form = QuickMessageForm()
    
    context = {
        'other_user': other_user,
        'form': form,
    }
    return render(request, 'messages/start_conversation.html', context)


@login_required
def delete_conversation(request, pk):
    conversation = get_object_or_404(
        Conversation,
        Q(user1=request.user) | Q(user2=request.user),
        pk=pk,
    )

    if request.method == 'POST':
        Message.objects.filter(
            Q(sender=conversation.user1, recipient=conversation.user2)
            | Q(sender=conversation.user2, recipient=conversation.user1)
        ).delete()
        conversation.delete()
        django_messages.success(request, 'Conversation deleted.')
        return redirect('message_list')

    return redirect('conversation_detail', pk=pk)


@login_required
def get_messages_json(request):
    """Get recent messages as JSON (for AJAX polling)"""
    # Get recent messages where user is recipient
    recent_messages = Message.objects.filter(
        recipient=request.user
    ).select_related('sender', 'related_order').order_by('-created_at')[:10]
    
    # Group messages by conversation
    conversations_dict = {}
    for msg in recent_messages:
        # Find or create conversation key
        conv = Conversation.objects.filter(
            Q(user1=request.user, user2=msg.sender) |
            Q(user1=msg.sender, user2=request.user)
        ).first()
        
        if conv and conv.id not in conversations_dict:
            conversations_dict[conv.id] = {
                'conversation_id': conv.id,
                'sender_name': msg.sender.first_name or msg.sender.username,
                'body': msg.body,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat(),
            }
    
    data = {
        'unread_count': get_unread_message_count(request.user),
        'messages': list(conversations_dict.values())
    }
    return JsonResponse(data)
