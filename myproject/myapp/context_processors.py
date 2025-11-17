"""
Context processors to make data available in all templates
"""
from .notifications import get_unread_notification_count, get_unread_message_count


def notifications_context(request):
    """Add notification and message counts to all templates"""
    if request.user.is_authenticated:
        return {
            'unread_notifications_count': get_unread_notification_count(request.user),
            'unread_messages_count': get_unread_message_count(request.user),
        }
    return {
        'unread_notifications_count': 0,
        'unread_messages_count': 0,
    }
