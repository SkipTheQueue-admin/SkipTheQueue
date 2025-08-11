/**
 * Enhanced Notification System for SkipTheQueue
 * Features:
 * - Persistent order ready notifications
 * - Real-time order status tracking
 * - Mobile-optimized UI
 * - Auto-dismiss and manual dismiss options
 * - Order status bars on all pages
 */

class NotificationManager {
    constructor() {
        this.notifications = [];
        this.orderStatusBars = new Map();
        this.orderReadyNotifications = new Map();
        this.isInitialized = false;
        this.checkInterval = null;
        this.userPhone = null;
        this.currentOrderId = null;
        
        this.init();
    }

    init() {
        if (this.isInitialized) return;
        
        // Get user phone from session storage or page data
        this.userPhone = this.getUserPhone();
        
        // Initialize notification container
        this.createNotificationContainer();
        
        // Start real-time order status checking
        this.startOrderStatusChecking();
        
        // Initialize existing notifications
        this.initializeExistingNotifications();
        
        // Set up event listeners
        this.setupEventListeners();
        
        this.isInitialized = true;
        console.log('NotificationManager initialized');
    }

    getUserPhone() {
        // Try to get phone from various sources
        const phoneFromStorage = sessionStorage.getItem('user_phone');
        if (phoneFromStorage) return phoneFromStorage;
        
        // Try to get from page data
        const phoneElement = document.querySelector('[data-user-phone]');
        if (phoneElement) return phoneElement.dataset.userPhone;
        
        // Try to get from order data
        const orderElement = document.querySelector('[data-order-phone]');
        if (orderElement) return orderElement.dataset.orderPhone;
        
        return null;
    }

    createNotificationContainer() {
        // Create main notification container
        if (!document.getElementById('notification-container')) {
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            document.body.appendChild(container);
        }

        // Create order status bar container
        if (!document.getElementById('order-status-container')) {
            const statusContainer = document.createElement('div');
            statusContainer.id = 'order-status-container';
            document.body.appendChild(statusContainer);
        }

        // Create order ready notification container
        if (!document.getElementById('order-ready-container')) {
            const readyContainer = document.createElement('div');
            readyContainer.id = 'order-ready-container';
            document.body.appendChild(readyContainer);
        }
    }

    initializeExistingNotifications() {
        // Initialize any existing Django messages
        const messages = document.querySelectorAll('.messages .message');
        messages.forEach(message => {
            this.showMessage(message);
        });

        // Initialize any existing order status
        this.checkCurrentOrderStatus();
    }

    setupEventListeners() {
        // Listen for order status updates
        document.addEventListener('orderStatusUpdated', (e) => {
            this.handleOrderStatusUpdate(e.detail);
        });

        // Listen for order ready notifications
        document.addEventListener('orderReady', (e) => {
            this.showOrderReadyNotification(e.detail);
        });

        // Listen for page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.refreshOrderStatus();
            }
        });

        // Listen for focus events
        window.addEventListener('focus', () => {
            this.refreshOrderStatus();
        });
    }

    startOrderStatusChecking() {
        if (!this.userPhone) return;
        
        // Check immediately
        this.checkOrderStatus();
        
        // Set up periodic checking
        this.checkInterval = setInterval(() => {
            this.checkOrderStatus();
        }, 10000); // Check every 10 seconds
    }

    async checkOrderStatus() {
        if (!this.userPhone) return;
        
        try {
            const response = await fetch(`/check-order-status/${this.userPhone}/`);
            if (!response.ok) throw new Error('Failed to check order status');
            
            const data = await response.json();
            
            if (data.has_active_order) {
                this.updateOrderStatusBar(data.order);
            } else {
                this.removeOrderStatusBar();
            }
            
            // Check for new notifications
            if (data.notifications && data.notifications.length > 0) {
                data.notifications.forEach(notification => {
                    this.showNotification(notification);
                });
            }
            
        } catch (error) {
            console.error('Error checking order status:', error);
        }
    }

    updateOrderStatusBar(order) {
        const container = document.getElementById('order-status-container');
        if (!container) return;
        
        // Remove existing status bar
        this.removeOrderStatusBar();
        
        // Create new status bar
        const statusBar = this.createOrderStatusBar(order);
        container.appendChild(statusBar);
        
        // Store reference
        this.orderStatusBars.set(order.id, statusBar);
        
        // Add to page
        document.body.insertBefore(statusBar, document.body.firstChild);
    }

    createOrderStatusBar(order) {
        const statusBar = document.createElement('div');
        statusBar.className = 'order-status-bar';
        statusBar.dataset.orderId = order.id;
        
        const statusColor = this.getStatusColor(order.status);
        const statusIcon = this.getStatusIcon(order.status);
        
        statusBar.innerHTML = `
            <div class="status-content">
                <div class="status-info">
                    <div class="status-icon" style="color: ${statusColor}">
                        ${statusIcon}
                    </div>
                    <div class="status-details">
                        <div class="status-title">Order #${order.id}</div>
                        <div class="status-message">${this.getStatusMessage(order.status)}</div>
                        <div class="status-time">${this.formatTime(order.updated_at)}</div>
                    </div>
                </div>
                <button class="status-close" onclick="notificationManager.removeOrderStatusBar()">
                    ×
                </button>
            </div>
        `;
        
        return statusBar;
    }

    removeOrderStatusBar() {
        const statusBars = document.querySelectorAll('.order-status-bar');
        statusBars.forEach(bar => {
            bar.classList.add('removing');
            setTimeout(() => {
                if (bar.parentNode) {
                    bar.parentNode.removeChild(bar);
                }
            }, 300);
        });
        
        this.orderStatusBars.clear();
    }

    showOrderReadyNotification(order) {
        const container = document.getElementById('order-ready-container');
        if (!container) return;
        
        // Remove existing notification
        this.removeOrderReadyNotification();
        
        // Create new notification
        const notification = this.createOrderReadyNotification(order);
        container.appendChild(notification);
        
        // Store reference
        this.orderReadyNotifications.set(order.id, notification);
        
        // Add to page
        document.body.insertBefore(notification, document.body.firstChild);
        
        // Play notification sound if available
        this.playNotificationSound();
        
        // Send browser notification
        this.sendBrowserNotification(order);
    }

    createOrderReadyNotification(order) {
        const notification = document.createElement('div');
        notification.className = 'order-ready-notification';
        notification.dataset.orderId = order.id;
        
        notification.innerHTML = `
            <div class="notification-header">
                <div class="notification-title">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    Order Ready!
                </div>
                <div class="notification-message">
                    Your order #${order.id} is ready for pickup at ${order.college_name || 'the canteen'}.
                </div>
            </div>
            <button class="notification-close" onclick="notificationManager.removeOrderReadyNotification()">
                ×
            </button>
        `;
        
        return notification;
    }

    removeOrderReadyNotification() {
        const notifications = document.querySelectorAll('.order-ready-notification');
        notifications.forEach(notification => {
            notification.classList.add('removing');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 400);
        });
        
        this.orderReadyNotifications.clear();
    }

    showNotification(notificationData) {
        const container = document.getElementById('notification-container');
        if (!container) return;
        
        const notification = this.createNotification(notificationData);
        container.appendChild(notification);
        
        // Auto-dismiss after 5 seconds (unless it's a persistent notification)
        if (!notificationData.persistent) {
            setTimeout(() => {
                this.dismissNotification(notification);
            }, 5000);
        }
        
        // Store reference
        this.notifications.push(notification);
        
        return notification;
    }

    createNotification(notificationData) {
        const notification = document.createElement('div');
        notification.className = `notification ${notificationData.type || 'info'}`;
        notification.dataset.notificationId = notificationData.id || Date.now();
        
        const icon = this.getNotificationIcon(notificationData.type);
        
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-icon">
                    ${icon}
                </div>
                <div class="notification-text">
                    <div class="notification-title">${notificationData.title || 'Notification'}</div>
                    <div class="notification-message">${notificationData.message || ''}</div>
                </div>
                <button class="notification-close" onclick="notificationManager.dismissNotification(this.parentElement.parentElement)">
                    ×
                </button>
            </div>
        `;
        
        return notification;
    }

    dismissNotification(notification) {
        if (!notification) return;
        
        notification.classList.add('removing');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            
            // Remove from array
            const index = this.notifications.indexOf(notification);
            if (index > -1) {
                this.notifications.splice(index, 1);
            }
        }, 300);
    }

    showMessage(messageElement) {
        if (!messageElement) return;
        
        const type = this.getMessageType(messageElement);
        const title = this.getMessageTitle(type);
        const message = messageElement.textContent.trim();
        
        this.showNotification({
            type: type,
            title: title,
            message: message,
            persistent: false
        });
        
        // Remove the original message
        messageElement.remove();
    }

    getMessageType(messageElement) {
        if (messageElement.classList.contains('success')) return 'success';
        if (messageElement.classList.contains('error')) return 'error';
        if (messageElement.classList.contains('warning')) return 'warning';
        if (messageElement.classList.contains('info')) return 'info';
        return 'info';
    }

    getMessageTitle(type) {
        const titles = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Information'
        };
        return titles[type] || 'Notification';
    }

    getStatusColor(status) {
        const colors = {
            'Pending': '#f59e0b',
            'Payment Pending': '#ef4444',
            'Paid': '#3b82f6',
            'In Progress': '#8b5cf6',
            'Ready': '#10b981',
            'Completed': '#059669',
            'Cancelled': '#6b7280'
        };
        return colors[status] || '#6b7280';
    }

    getStatusIcon(status) {
        const icons = {
            'Pending': '⏳',
            'Payment Pending': '💳',
            'Paid': '✅',
            'In Progress': '👨‍🍳',
            'Ready': '🎉',
            'Completed': '🎊',
            'Cancelled': '❌'
        };
        return icons[status] || 'ℹ️';
    }

    getStatusMessage(status) {
        const messages = {
            'Pending': 'Order received, waiting for confirmation',
            'Payment Pending': 'Payment required to proceed',
            'Paid': 'Payment confirmed, order queued',
            'In Progress': 'Your order is being prepared',
            'Ready': 'Order ready for pickup!',
            'Completed': 'Order completed successfully',
            'Cancelled': 'Order has been cancelled'
        };
        return messages[status] || 'Order status updated';
    }

    getNotificationIcon(type) {
        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };
        return icons[type] || 'ℹ️';
    }

    formatTime(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        
        return date.toLocaleDateString();
    }

    playNotificationSound() {
        // Try to play notification sound
        try {
            const audio = new Audio('/static/sounds/notification.mp3');
            audio.volume = 0.5;
            audio.play().catch(() => {
                // Fallback: create a simple beep
                this.createBeepSound();
            });
        } catch (error) {
            this.createBeepSound();
        }
    }

    createBeepSound() {
        // Create a simple beep sound using Web Audio API
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch (error) {
            console.log('Could not play notification sound');
        }
    }

    sendBrowserNotification(order) {
        if (!('Notification' in window)) return;
        
        if (Notification.permission === 'granted') {
            new Notification('Order Ready!', {
                body: `Your order #${order.id} is ready for pickup.`,
                icon: '/static/images/icon-192x192.png',
                badge: '/static/images/badge-72x72.png',
                tag: `order-${order.id}`,
                requireInteraction: true
            });
        } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(permission => {
                if (permission === 'granted') {
                    this.sendBrowserNotification(order);
                }
            });
        }
    }

    refreshOrderStatus() {
        this.checkOrderStatus();
    }

    handleOrderStatusUpdate(orderData) {
        // Update status bar if exists
        if (this.orderStatusBars.has(orderData.id)) {
            this.updateOrderStatusBar(orderData);
        }
        
        // Show order ready notification if status is 'Ready'
        if (orderData.status === 'Ready') {
            this.showOrderReadyNotification(orderData);
        }
    }

    // Public methods for external use
    showSuccess(message, title = 'Success') {
        return this.showNotification({
            type: 'success',
            title: title,
            message: message
        });
    }

    showError(message, title = 'Error') {
        return this.showNotification({
            type: 'error',
            title: title,
            message: message
        });
    }

    showWarning(message, title = 'Warning') {
        return this.showNotification({
            type: 'warning',
            title: title,
            message: message
        });
    }

    showInfo(message, title = 'Information') {
        return this.showNotification({
            type: 'info',
            title: title,
            message: message
        });
    }

    // Cleanup method
    destroy() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
        }
        
        // Remove all notifications
        this.notifications.forEach(notification => {
            this.dismissNotification(notification);
        });
        
        // Remove order status bars
        this.removeOrderStatusBar();
        
        // Remove order ready notifications
        this.removeOrderReadyNotification();
        
        this.isInitialized = false;
    }
}

// Initialize notification manager when DOM is ready
let notificationManager;

document.addEventListener('DOMContentLoaded', () => {
    notificationManager = new NotificationManager();
});

// Make it globally available
window.notificationManager = notificationManager;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationManager;
}

