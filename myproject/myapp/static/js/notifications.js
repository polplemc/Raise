/**
 * Real-time Notification and Message System
 * Polls server for new notifications and messages
 * Updates badge counts and dropdown content
 */

class RealTimeNotifications {
    constructor(options = {}) {
        this.pollInterval = options.pollInterval || 30000; // 30 seconds
        this.notificationUrl = options.notificationUrl || '/api/notifications/';
        this.messageUrl = options.messageUrl || '/api/messages/';
        this.isPolling = false;
        this.pollTimer = null;
        this.lastNotificationCheck = null;
        this.lastMessageCheck = null;
        
        this.init();
    }

    init() {
        // Start polling when page loads
        this.startPolling();
        
        // Load initial notifications and messages
        this.loadNotifications();
        this.loadMessages();
        
        // Stop polling when page is hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopPolling();
            } else {
                this.startPolling();
            }
        });
        
        // Stop polling before page unload
        window.addEventListener('beforeunload', () => {
            this.stopPolling();
        });
    }

    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.poll();
        this.pollTimer = setInterval(() => this.poll(), this.pollInterval);
    }

    stopPolling() {
        this.isPolling = false;
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }

    async poll() {
        if (!this.isPolling) return;
        
        try {
            await Promise.all([
                this.loadNotifications(),
                this.loadMessages()
            ]);
        } catch (error) {
            console.error('Polling error:', error);
        }
    }

    async loadNotifications() {
        try {
            const response = await fetch(this.notificationUrl);
            if (!response.ok) throw new Error('Failed to load notifications');
            
            const data = await response.json();
            this.updateNotificationBadge(data.unread_count);
            this.updateNotificationDropdown(data.notifications);
            
            // Show popup for new notifications
            if (this.lastNotificationCheck && data.notifications.length > 0) {
                const newNotifications = data.notifications.filter(n => 
                    new Date(n.created_at) > this.lastNotificationCheck
                );
                newNotifications.forEach(n => this.showNotificationPopup(n));
            }
            
            this.lastNotificationCheck = new Date();
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    async loadMessages() {
        try {
            const response = await fetch(this.messageUrl);
            if (!response.ok) throw new Error('Failed to load messages');
            
            const data = await response.json();
            this.updateMessageBadge(data.unread_count);
            this.updateMessageDropdown(data.messages);
            
            // Show popup for new messages
            if (this.lastMessageCheck && data.messages.length > 0) {
                const newMessages = data.messages.filter(m => 
                    new Date(m.created_at) > this.lastMessageCheck
                );
                newMessages.forEach(m => this.showMessagePopup(m));
            }
            
            this.lastMessageCheck = new Date();
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }

    updateNotificationBadge(count) {
        const displayCount = count > 99 ? '99+' : count;

        const badges = document.querySelectorAll('#notificationDropdown .badge');
        badges.forEach(badge => {
            if (count > 0) {
                badge.textContent = displayCount;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        });
        
        // Update notification count text
        const countElement = document.getElementById('notificationCount');
        if (countElement) {
            countElement.textContent = count;
        }

        // Update sidebar "Notifications" label as Notifications(1)
        const sidebarLabels = document.querySelectorAll('.sidebar-notification-label');
        sidebarLabels.forEach(label => {
            if (count > 0) {
                label.textContent = `Notifications(${displayCount})`;
            } else {
                label.textContent = 'Notifications';
            }
        });
    }

    updateMessageBadge(count) {
        const displayCount = count > 99 ? '99+' : count;

        const badges = document.querySelectorAll('#messageDropdown .badge');
        badges.forEach(badge => {
            if (count > 0) {
                badge.textContent = displayCount;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        });
        
        // Update message count text
        const countElement = document.getElementById('messageCount');
        if (countElement) {
            countElement.textContent = count;
        }

        // Update sidebar "Messages" label as Messages(1)
        const sidebarLabels = document.querySelectorAll('.sidebar-message-label');
        sidebarLabels.forEach(label => {
            if (count > 0) {
                label.textContent = `Messages(${displayCount})`;
            } else {
                label.textContent = 'Messages';
            }
        });
    }

    updateNotificationDropdown(notifications) {
        const dropdowns = document.querySelectorAll('#notificationDropdown + .dropdown-menu');
        dropdowns.forEach(dropdown => {
            const container = dropdown.querySelector('.notification-items');
            if (!container) return;
            
            if (notifications.length === 0) {
                container.innerHTML = `
                    <li class="dropdown-item text-center text-muted py-4">
                        <i class="bi bi-inbox fs-3"></i><br>
                        <span class="mt-2 d-block">No notifications</span>
                    </li>
                `;
                return;
            }
            
            container.innerHTML = notifications.slice(0, 5).map(n => {
                const iconData = this.getNotificationIconData(n.notification_type);
                return `
                <li>
                    <a class="dropdown-item ${n.is_read ? '' : 'bg-light'}" href="/notifications/${n.id}/" style="padding: 12px 20px; border-bottom: 1px solid #f0f0f0;">
                        <div class="d-flex align-items-start gap-3">
                            <div class="flex-shrink-0">
                                <div class="rounded-circle d-flex align-items-center justify-content-center" style="width: 40px; height: 40px; background-color: ${iconData.bgColor};">
                                    <i class="bi ${iconData.icon}" style="color: ${iconData.color}; font-size: 1.2rem;"></i>
                                </div>
                            </div>
                            <div class="flex-grow-1" style="min-width: 0;">
                                <div class="fw-semibold text-dark mb-1" style="font-size: 0.95rem;">${this.escapeHtml(n.title)}</div>
                                <div class="text-muted" style="font-size: 0.85rem; line-height: 1.4;">${this.escapeHtml(n.message.substring(0, 70))}${n.message.length > 70 ? '...' : ''}</div>
                                <div class="text-muted mt-1" style="font-size: 0.75rem;">${this.timeAgo(n.created_at)}</div>
                            </div>
                        </div>
                    </a>
                </li>
            `}).join('');
        });
    }

    updateMessageDropdown(messages) {
        const dropdowns = document.querySelectorAll('#messageDropdown + .dropdown-menu');
        dropdowns.forEach(dropdown => {
            const container = dropdown.querySelector('.message-items');
            if (!container) return;
            
            if (messages.length === 0) {
                container.innerHTML = `
                    <li class="dropdown-item text-center text-muted py-4">
                        <i class="bi bi-inbox fs-3"></i><br>
                        <span class="mt-2 d-block">No messages</span>
                    </li>
                `;
                return;
            }
            
            container.innerHTML = messages.slice(0, 5).map(m => `
                <li>
                    <a class="dropdown-item ${m.is_read ? '' : 'bg-light'}" href="/messages/conversation/${m.conversation_id}/" style="padding: 12px 20px; border-bottom: 1px solid #f0f0f0;">
                        <div class="d-flex align-items-start gap-3">
                            <div class="flex-shrink-0">
                                <div class="rounded-circle d-flex align-items-center justify-content-center" style="width: 40px; height: 40px; background-color: #e7f3ff;">
                                    <i class="bi bi-person-circle" style="color: #0d6efd; font-size: 1.5rem;"></i>
                                </div>
                            </div>
                            <div class="flex-grow-1" style="min-width: 0;">
                                <div class="fw-semibold text-dark mb-1" style="font-size: 0.95rem;">${this.escapeHtml(m.sender_name)}</div>
                                <div class="text-muted" style="font-size: 0.85rem; line-height: 1.4;">${this.escapeHtml(m.body.substring(0, 60))}${m.body.length > 60 ? '...' : ''}</div>
                                <div class="text-muted mt-1" style="font-size: 0.75rem;">${this.timeAgo(m.created_at)}</div>
                            </div>
                        </div>
                    </a>
                </li>
            `).join('');
        });
    }

    showNotificationPopup(notification) {
        if (window.notificationSystem) {
            const message = `${notification.title}: ${notification.message.substring(0, 100)}`;
            window.notificationSystem.info(message, 8000);
        }
    }

    showMessagePopup(message) {
        if (window.notificationSystem) {
            const msg = `New message from ${message.sender_name}: ${message.body.substring(0, 80)}`;
            window.notificationSystem.info(msg, 8000);
        }
    }

    getNotificationIcon(type) {
        const icons = {
            'order_placed': 'bi-cart-plus text-primary',
            'order_confirmed': 'bi-check-circle text-success',
            'order_processing': 'bi-hourglass-split text-warning',
            'order_completed': 'bi-check-all text-success',
            'order_cancelled': 'bi-x-circle text-danger',
            'delivery_shipped': 'bi-truck text-info',
            'delivery_out': 'bi-geo-alt text-warning',
            'delivery_delivered': 'bi-box-seam text-success',
            'payment_paid': 'bi-cash text-success',
            'payment_verified': 'bi-shield-check text-success',
            'stock_low': 'bi-exclamation-triangle text-warning',
            'stock_out': 'bi-exclamation-circle text-danger',
            'new_message': 'bi-envelope text-info',
            'system': 'bi-info-circle text-primary'
        };
        return icons[type] || 'bi-bell text-secondary';
    }

    getNotificationIconData(type) {
        const iconData = {
            'order_placed': { icon: 'bi-cart-plus', color: '#0d6efd', bgColor: '#cfe2ff' },
            'order_confirmed': { icon: 'bi-check-circle', color: '#198754', bgColor: '#d1e7dd' },
            'order_processing': { icon: 'bi-hourglass-split', color: '#ffc107', bgColor: '#fff3cd' },
            'order_completed': { icon: 'bi-check-all', color: '#198754', bgColor: '#d1e7dd' },
            'order_cancelled': { icon: 'bi-x-circle', color: '#dc3545', bgColor: '#f8d7da' },
            'delivery_shipped': { icon: 'bi-truck', color: '#0dcaf0', bgColor: '#cff4fc' },
            'delivery_out': { icon: 'bi-geo-alt', color: '#ffc107', bgColor: '#fff3cd' },
            'delivery_delivered': { icon: 'bi-box-seam', color: '#198754', bgColor: '#d1e7dd' },
            'payment_paid': { icon: 'bi-cash', color: '#198754', bgColor: '#d1e7dd' },
            'payment_verified': { icon: 'bi-shield-check', color: '#198754', bgColor: '#d1e7dd' },
            'stock_low': { icon: 'bi-exclamation-triangle', color: '#ffc107', bgColor: '#fff3cd' },
            'stock_out': { icon: 'bi-exclamation-circle', color: '#dc3545', bgColor: '#f8d7da' },
            'new_message': { icon: 'bi-envelope', color: '#0dcaf0', bgColor: '#cff4fc' },
            'system': { icon: 'bi-info-circle', color: '#0d6efd', bgColor: '#cfe2ff' }
        };
        return iconData[type] || { icon: 'bi-bell', color: '#6c757d', bgColor: '#e9ecef' };
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    timeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);
        
        if (seconds < 60) return 'Just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
        return date.toLocaleDateString();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.realTimeNotifications = new RealTimeNotifications({
        pollInterval: 30000, // 30 seconds
        notificationUrl: '/api/notifications/',
        messageUrl: '/api/messages/'
    });
});
