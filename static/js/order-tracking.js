// Order Tracking JavaScript - External file for better security and maintainability
class OrderTrackingManager {
  constructor() {
    this.currentOrderId = null;
    this.trackingInterval = null;
    this.progressInterval = null;
    
    this.initializeEventListeners();
  }

  initializeEventListeners() {
    // Hide order tracking button
    document.addEventListener('click', (e) => {
      if (e.target.closest('[data-action="hide-order-tracking"]')) {
        e.preventDefault();
        this.hideOrderTracking();
      }
    });

    // Global error handlers - only show errors for critical issues
    window.addEventListener('error', (e) => {
      console.error('Global error in order tracking:', e.error);
      // Only show notification for critical errors, not all errors
      if (e.error && e.error.message && e.error.message.includes('fetch')) {
        this.showNotification('Network error. Please check your connection.', 'error');
      }
    });

    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled promise rejection in order tracking:', e.reason);
      // Only show notification for network errors
      if (e.reason && e.reason.message && e.reason.message.includes('fetch')) {
        this.showNotification('Network error. Please try again.', 'error');
      }
    });
  }

  showOrderTracking(orderId, status, estimatedTime) {
    this.currentOrderId = orderId;
    
    // Update tracking bar content
    const orderIdElement = document.getElementById('tracking-order-id');
    const statusElement = document.getElementById('tracking-status');
    const timeElement = document.getElementById('tracking-time');
    
    if (orderIdElement) orderIdElement.textContent = orderId;
    if (statusElement) statusElement.textContent = status;
    if (timeElement) timeElement.textContent = `Est. ${estimatedTime} min`;
    
    // Show tracking bar with smooth animation
    const trackingBar = document.getElementById('order-tracking-bar');
    if (trackingBar) {
      trackingBar.classList.remove('hidden');
      
      // Trigger animation after a small delay
      setTimeout(() => {
        trackingBar.classList.remove('-translate-y-full');
      }, 10);
    }
    
    // Start tracking updates
    this.startOrderTracking();
    this.startProgressAnimation(estimatedTime);
  }

  hideOrderTracking() {
    const trackingBar = document.getElementById('order-tracking-bar');
    if (trackingBar) {
      trackingBar.classList.add('-translate-y-full');
      
      // Hide after animation completes
      setTimeout(() => {
        trackingBar.classList.add('hidden');
      }, 500);
    }
    
    // Stop tracking updates
    if (this.trackingInterval) {
      clearInterval(this.trackingInterval);
      this.trackingInterval = null;
    }
    
    if (this.progressInterval) {
      clearInterval(this.progressInterval);
      this.progressInterval = null;
    }
    
    // Reset progress bar
    const progressBar = document.getElementById('tracking-progress');
    if (progressBar) {
      progressBar.style.width = '0%';
    }
    
    this.currentOrderId = null;
  }

  startProgressAnimation(estimatedTime) {
    const progressBar = document.getElementById('tracking-progress');
    if (!progressBar) return;
    
    // Reset progress
    progressBar.style.width = '0%';
    
    // Calculate progress increment per second
    const totalSeconds = estimatedTime * 60;
    const increment = 100 / totalSeconds;
    let currentProgress = 0;
    
    this.progressInterval = setInterval(() => {
      currentProgress += increment;
      if (currentProgress >= 100) {
        currentProgress = 100;
        clearInterval(this.progressInterval);
      }
      progressBar.style.width = `${currentProgress}%`;
    }, 1000);
  }

  startOrderTracking() {
    if (this.trackingInterval) {
      clearInterval(this.trackingInterval);
    }
    
    // Update order status every 10 seconds
    this.trackingInterval = setInterval(async () => {
      if (!this.currentOrderId) return;
      
      try {
        const response = await fetch(`/api/check-order-status/${this.currentOrderId}/`);
        if (response.ok) {
          const data = await response.json();
          
          if (data.status === 'Completed' || data.status === 'Cancelled') {
            // Show completion message
            if (data.status === 'Completed') {
              this.showNotification('Order completed successfully! 🎉', 'success', 5000);
            } else {
              this.showNotification('Order was cancelled', 'info', 5000);
            }
            
            // Hide tracking bar when order is completed
            this.hideOrderTracking();
            return;
          }
          
          // Update status display
          const statusElement = document.getElementById('tracking-status');
          if (statusElement) {
            statusElement.textContent = data.status;
            
            // Add status-specific styling
            statusElement.className = 'font-medium';
            if (data.status === 'Preparing') {
              statusElement.classList.add('text-yellow-200');
            } else if (data.status === 'Ready') {
              statusElement.classList.add('text-green-200');
            }
          }
          
          if (data.estimated_time) {
            const timeElement = document.getElementById('tracking-time');
            if (timeElement) {
              timeElement.textContent = `Est. ${data.estimated_time} min`;
            }
          }
        }
      } catch (error) {
        console.error('Error checking order status:', error);
      }
    }, 10000);
  }

  showNotification(message, type = 'info', duration = 3000) {
    if (typeof window.showNotification === 'function') {
      window.showNotification(message, type, duration);
    } else {
      // Fallback notification
      const notification = document.createElement('div');
      const bgColor = type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500';
      const icon = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';

      notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${bgColor} text-white transform transition-all duration-300 translate-x-full`;
      notification.innerHTML = `
        <div class="flex items-center">
          <span class="mr-2 text-lg">${icon}</span>
          <span class="flex-1">${message}</span>
          <button onclick="this.parentElement.parentElement.remove()" class="ml-3 text-white hover:text-gray-200 transition-colors">
            <i class="fas fa-times"></i>
          </button>
        </div>
      `;
      document.body.appendChild(notification);

      requestAnimationFrame(() => {
        notification.classList.remove('translate-x-full');
      });

      setTimeout(() => {
        if (notification.parentElement) {
          notification.classList.add('translate-x-full');
          setTimeout(() => {
            if (notification.parentElement) {
              notification.remove();
            }
          }, 300);
        }
      }, duration);
    }
  }
}

// Initialize order tracking manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.orderTrackingManager = new OrderTrackingManager();
});

// Make functions globally available for backward compatibility
window.showOrderTracking = function(orderId, status, estimatedTime) {
  if (window.orderTrackingManager) {
    window.orderTrackingManager.showOrderTracking(orderId, status, estimatedTime);
  }
};

window.hideOrderTracking = function() {
  if (window.orderTrackingManager) {
    window.orderTrackingManager.hideOrderTracking();
  }
};
