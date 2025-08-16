// Enhanced Notifications System for SkipTheQueue
// Provides toast notifications, alerts, and user feedback

class NotificationSystem {
    constructor() {
        this.notifications = [];
        this.maxNotifications = 5;
        this.defaultDuration = 5000;
        this.init();
    }
    
    init() {
        // Create notification container if it doesn't exist
        if (!document.getElementById('notification-container')) {
            this.createContainer();
        }
        
        // Set up global notification function
        window.showNotification = this.show.bind(this);
        window.hideNotification = this.hide.bind(this);
        window.clearAllNotifications = this.clearAll.bind(this);
    }
    
    createContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'fixed top-4 right-4 z-50 space-y-2 max-w-sm';
        document.body.appendChild(container);
    }
    
    show(message, type = 'info', duration = null, options = {}) {
        const notification = this.createNotification(message, type, options);
        this.notifications.push(notification);
        
        // Add to DOM
        const container = document.getElementById('notification-container');
        container.appendChild(notification);
        
        // Animate in
        requestAnimationFrame(() => {
            notification.classList.remove('translate-x-full', 'opacity-0');
        });
        
        // Auto-remove after duration
        const autoRemoveDuration = duration !== null ? duration : this.defaultDuration;
        if (autoRemoveDuration > 0) {
            setTimeout(() => {
                this.hide(notification);
            }, autoRemoveDuration);
        }
        
        // Limit number of notifications
        if (this.notifications.length > this.maxNotifications) {
            this.hide(this.notifications[0]);
        }
        
        return notification;
    }
    
    createNotification(message, type, options = {}) {
        const notification = document.createElement('div');
        
        // Determine colors and icons based on type
        const config = this.getTypeConfig(type);
        
        notification.className = `bg-${config.bgColor} border border-${config.borderColor} text-${config.textColor} p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full opacity-0 max-w-sm`;
        
        notification.innerHTML = `
            <div class="flex items-start space-x-3">
                <div class="flex-shrink-0">
                    <i class="fas ${config.icon} text-lg"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium">${this.escapeHtml(message)}</p>
                    ${options.description ? `<p class="text-xs mt-1 opacity-75">${this.escapeHtml(options.description)}</p>` : ''}
                </div>
                <div class="flex-shrink-0 ml-2">
                    <button onclick="window.notificationSystem.hide(this.closest('.notification'))" 
                            class="text-${config.textColor} hover:opacity-75 transition-opacity focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-${config.ringColor} rounded">
                        <i class="fas fa-times text-sm"></i>
                    </button>
                </div>
            </div>
            ${options.progress ? `<div class="mt-2 bg-${config.progressBg} rounded-full h-1"><div class="bg-${config.progressColor} h-1 rounded-full transition-all duration-300" style="width: ${options.progress}%"></div></div>` : ''}
        `;
        
        // Add custom classes
        if (options.className) {
            notification.classList.add(...options.className.split(' '));
        }
        
        // Add data attributes
        notification.dataset.type = type;
        notification.dataset.timestamp = Date.now();
        
        // Add click handler if provided
        if (options.onClick) {
            notification.style.cursor = 'pointer';
            notification.addEventListener('click', options.onClick);
        }
        
        return notification;
    }
    
    getTypeConfig(type) {
        const configs = {
            success: {
                bgColor: 'green-50',
                borderColor: 'green-200',
                textColor: 'green-800',
                ringColor: 'green-500',
                icon: 'fa-check-circle',
                progressBg: 'green-200',
                progressColor: 'green-500'
            },
            error: {
                bgColor: 'red-50',
                borderColor: 'red-200',
                textColor: 'red-800',
                ringColor: 'red-500',
                icon: 'fa-exclamation-circle',
                progressBg: 'red-200',
                progressColor: 'red-500'
            },
            warning: {
                bgColor: 'yellow-50',
                borderColor: 'yellow-200',
                textColor: 'yellow-800',
                ringColor: 'yellow-500',
                icon: 'fa-exclamation-triangle',
                progressBg: 'yellow-200',
                progressColor: 'yellow-500'
            },
            info: {
                bgColor: 'blue-50',
                borderColor: 'blue-200',
                textColor: 'blue-800',
                ringColor: 'blue-500',
                icon: 'fa-info-circle',
                progressBg: 'blue-200',
                progressColor: 'blue-500'
            }
        };
        
        return configs[type] || configs.info;
    }
    
    hide(notification) {
        if (!notification) return;
        
        // Animate out
        notification.classList.add('translate-x-full', 'opacity-0');
        
        // Remove from DOM after animation
        setTimeout(() => {
            if (notification.parentElement) {
                notification.parentElement.removeChild(notification);
            }
            
            // Remove from notifications array
            const index = this.notifications.indexOf(notification);
            if (index > -1) {
                this.notifications.splice(index, 1);
            }
        }, 300);
    }
    
    clearAll() {
        this.notifications.forEach(notification => {
            this.hide(notification);
        });
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Special notification types
    success(message, duration = null, options = {}) {
        return this.show(message, 'success', duration, options);
    }
    
    error(message, duration = null, options = {}) {
        return this.show(message, 'error', duration, options);
    }
    
    warning(message, duration = null, options = {}) {
        return this.show(message, 'warning', duration, options);
    }
    
    info(message, duration = null, options = {}) {
        return this.show(message, 'info', duration, options);
    }
    
    // Progress notification
    progress(message, progress = 0, options = {}) {
        return this.show(message, 'info', null, { ...options, progress });
    }
    
    // Update progress of existing notification
    updateProgress(notification, progress) {
        const progressBar = notification.querySelector('.bg-green-500, .bg-blue-500, .bg-yellow-500, .bg-red-500');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    }
    
    // Confirmation dialog
    confirm(message, onConfirm, onCancel = null, options = {}) {
        const notification = this.createNotification(message, 'info', {
            ...options,
            className: 'notification confirmation',
            duration: 0 // Don't auto-remove
        });
        
        // Add confirmation buttons
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'flex space-x-2 mt-3';
        buttonContainer.innerHTML = `
            <button class="btn-confirm bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm transition-colors">
                Confirm
            </button>
            <button class="btn-cancel bg-gray-600 hover:bg-gray-700 text-white px-3 py-1 rounded text-sm transition-colors">
                Cancel
            </button>
        `;
        
        notification.querySelector('.flex-1').appendChild(buttonContainer);
        
        // Add event listeners
        const confirmBtn = notification.querySelector('.btn-confirm');
        const cancelBtn = notification.querySelector('.btn-cancel');
        
        confirmBtn.addEventListener('click', () => {
            this.hide(notification);
            if (onConfirm) onConfirm();
        });
        
        cancelBtn.addEventListener('click', () => {
            this.hide(notification);
            if (onCancel) onCancel();
        });
        
        // Show the notification
        this.show(message, 'info', 0, { ...options, className: 'notification confirmation' });
        
        return notification;
    }
}

// Initialize notification system
window.notificationSystem = new NotificationSystem();

// Legacy support for existing code
function showNotification(message, type = 'info') {
    return window.notificationSystem.show(message, type);
}

function hideNotification(notification) {
    return window.notificationSystem.hide(notification);
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NotificationSystem;
}

