// Canteen Dashboard JavaScript - External file for better security and maintainability
class CanteenDashboard {
  constructor() {
    this.csrfToken = document.querySelector('[name=csrf-token]')?.content || 
                     document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    this.isRefreshing = false;
    this.refreshTimer = null;
    this.loadingIndicator = document.getElementById('loading-indicator');
    
    this.initializeEventListeners();
    this.startAutoRefresh();
  }

  initializeEventListeners() {
    // Add event listeners for buttons
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('accept-btn')) {
        e.preventDefault();
        const orderId = e.target.getAttribute('data-order-id');
        this.acceptOrder(orderId);
      } else if (e.target.classList.contains('decline-btn')) {
        e.preventDefault();
        const orderId = e.target.getAttribute('data-order-id');
        this.declineOrder(orderId);
      } else if (e.target.classList.contains('ready-btn')) {
        e.preventDefault();
        const orderId = e.target.getAttribute('data-order-id');
        this.markReady(orderId);
      } else if (e.target.classList.contains('complete-btn')) {
        e.preventDefault();
        const orderId = e.target.getAttribute('data-order-id');
        this.markCompleted(orderId);
      } else if (e.target.id === 'refresh-btn' || e.target.closest('#refresh-btn')) {
        e.preventDefault();
        location.reload();
      }
    });

    // Global error handlers
    window.addEventListener('error', (e) => {
      console.error('Global error in canteen dashboard:', e.error);
      this.showNotification('An unexpected error occurred. Please check the console.', 'error');
    });

    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled promise rejection in canteen dashboard:', e.reason);
      this.showNotification('A network error occurred. Please try again.', 'error');
    });

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
      if (this.refreshTimer) {
        clearInterval(this.refreshTimer);
      }
    });
  }

  startAutoRefresh() {
    // Smart refresh every 30 seconds - no hard reloads
    this.refreshTimer = setInterval(async () => {
      if (!this.isRefreshing) {
        await this.smartRefresh();
      }
    }, 30000);
  }

  async smartRefresh() {
    try {
      const response = await fetch(`/api/orders/${this.getCollegeSlug()}/`);
      if (response.ok) {
        const data = await response.json();
        this.updateOrdersDisplay(data.orders);
      }
    } catch (error) {
      console.error('Smart refresh failed:', error);
    }
  }

  updateOrdersDisplay(orders) {
    const ordersContainer = document.getElementById('orders-container');
    if (ordersContainer && orders) {
      // Update orders without full page reload
      ordersContainer.innerHTML = orders.map(order => this.createOrderHTML(order)).join('');
    }
  }

  createOrderHTML(order) {
    return `
      <div class="order-item p-4 border rounded-lg mb-4" data-order-id="${order.id}">
        <div class="flex justify-between items-center">
          <div>
            <h3 class="font-semibold">Order #${order.id}</h3>
            <p class="text-gray-600">${order.customer_name}</p>
          </div>
          <div class="flex space-x-2">
            <button class="accept-btn bg-green-500 text-white px-4 py-2 rounded" data-order-id="${order.id}">
              <i class="fas fa-check mr-2"></i>Accept
            </button>
            <button class="decline-btn bg-red-500 text-white px-4 py-2 rounded" data-order-id="${order.id}">
              <i class="fas fa-times mr-2"></i>Decline
            </button>
          </div>
        </div>
      </div>
    `;
  }

  async acceptOrder(orderId) {
    if (this.isRefreshing) return;
    
    if (!orderId || isNaN(parseInt(orderId))) {
      this.showNotification('Invalid order ID', 'error');
      return;
    }
    
    this.isRefreshing = true;
    this.showLoading();
    
    const orderElement = document.querySelector(`[data-order-id="${orderId}"]`);
    const button = orderElement?.querySelector('.accept-btn');
    
    if (button) {
      button.disabled = true;
      button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Accepting...';
      button.setAttribute('aria-label', 'Accepting order...');
    }
    
    try {
      const response = await fetch(`/canteen/dashboard/${this.getCollegeSlug()}/accept-order/${orderId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': this.csrfToken
        },
        credentials: 'same-origin'
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          this.showNotification('Order accepted successfully!', 'success');
          // Smart update instead of reload
          setTimeout(() => this.smartRefresh(), 1000);
        } else {
          this.showNotification(data.error || 'Failed to accept order', 'error');
          this.resetButton(button, 'Accept Order', 'fas fa-check');
        }
      } else {
        this.showNotification('Failed to accept order', 'error');
        this.resetButton(button, 'Accept Order', 'fas fa-check');
      }
    } catch (error) {
      console.error('Error accepting order:', error);
      this.showNotification('Error accepting order', 'error');
      this.resetButton(button, 'Accept Order', 'fas fa-check');
    } finally {
      this.hideLoading();
      this.isRefreshing = false;
    }
  }

  async declineOrder(orderId) {
    if (this.isRefreshing) return;
    
    if (!orderId || isNaN(parseInt(orderId))) {
      this.showNotification('Invalid order ID', 'error');
      return;
    }
    
    if (!confirm('Are you sure you want to decline this order?')) return;
    
    this.isRefreshing = true;
    
    const orderElement = document.querySelector(`[data-order-id="${orderId}"]`);
    const button = orderElement?.querySelector('.decline-btn');
    
    if (button) {
      button.disabled = true;
      button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Declining...';
      button.setAttribute('aria-label', 'Declining order...');
    }
    
    try {
      const response = await fetch(`/canteen/dashboard/${this.getCollegeSlug()}/decline-order/${orderId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': this.csrfToken
        },
        credentials: 'same-origin'
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          this.showNotification('Order declined successfully!', 'success');
          // Smart update instead of reload
          setTimeout(() => this.smartRefresh(), 1000);
        } else {
          this.showNotification(data.error || 'Failed to decline order', 'error');
          this.resetButton(button, 'Decline', 'fas fa-times');
        }
      } else {
        this.showNotification('Failed to decline order', 'error');
        this.resetButton(button, 'Decline', 'fas fa-times');
      }
    } catch (error) {
      console.error('Error declining order:', error);
      this.showNotification('Error declining order', 'error');
      this.resetButton(button, 'Decline', 'fas fa-times');
    } finally {
      this.isRefreshing = false;
    }
  }

  async markReady(orderId) {
    if (this.isRefreshing) return;
    
    if (!orderId || isNaN(parseInt(orderId))) {
      this.showNotification('Invalid order ID', 'error');
      return;
    }
    
    this.isRefreshing = true;
    
    const orderElement = document.querySelector(`[data-order-id="${orderId}"]`);
    const button = orderElement?.querySelector('.ready-btn');
    
    if (button) {
      button.disabled = true;
      button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Marking Ready...';
      button.setAttribute('aria-label', 'Marking order as ready...');
    }
    
    try {
      const response = await fetch(`/canteen/dashboard/${this.getCollegeSlug()}/mark-ready/${orderId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': this.csrfToken
        },
        credentials: 'same-origin'
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          this.showNotification('Order marked as ready!', 'success');
          // Smart update instead of reload
          setTimeout(() => this.smartRefresh(), 1000);
        } else {
          this.showNotification(data.error || 'Failed to mark order as ready', 'error');
          this.resetButton(button, 'Mark Ready', 'fas fa-check');
        }
      } else {
        this.showNotification('Failed to mark order as ready', 'error');
        this.resetButton(button, 'Mark Ready', 'fas fa-check');
      }
    } catch (error) {
      console.error('Error marking order as ready:', error);
      this.showNotification('Error marking order as ready', 'error');
      this.resetButton(button, 'Mark Ready', 'fas fa-check');
    } finally {
      this.isRefreshing = false;
    }
  }

  async markCompleted(orderId) {
    if (this.isRefreshing) return;
    
    if (!orderId || isNaN(parseInt(orderId))) {
      this.showNotification('Invalid order ID', 'error');
      return;
    }
    
    this.isRefreshing = true;
    
    const orderElement = document.querySelector(`[data-order-id="${orderId}"]`);
    const button = orderElement?.querySelector('.complete-btn');
    
    if (button) {
      button.disabled = true;
      button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Marking Completed...';
      button.setAttribute('aria-label', 'Marking order as completed...');
    }
    
    try {
      const response = await fetch(`/canteen/dashboard/${this.getCollegeSlug()}/mark-completed/${orderId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': this.csrfToken
        },
        credentials: 'same-origin'
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          this.showNotification('Order marked as completed!', 'success');
          // Smart update instead of reload
          setTimeout(() => this.smartRefresh(), 1000);
        } else {
          this.showNotification(data.error || 'Failed to mark order as completed', 'error');
          this.resetButton(button, 'Mark Completed', 'fas fa-check-double');
        }
      } else {
        this.showNotification('Failed to mark order as completed', 'error');
        this.resetButton(button, 'Mark Completed', 'fas fa-check-double');
      }
    } catch (error) {
      console.error('Error marking order as completed:', error);
      this.showNotification('Error marking order as completed', 'error');
      this.resetButton(button, 'Mark Completed', 'fas fa-check-double');
    } finally {
      this.isRefreshing = false;
    }
  }

  resetButton(button, text, iconClass) {
    if (button) {
      button.disabled = false;
      button.innerHTML = `<i class="${iconClass} mr-2"></i>${text}`;
    }
  }

  showNotification(message, type = 'info') {
    if (typeof window.showNotification === 'function') {
      window.showNotification(message, type);
    } else {
      // Enhanced fallback notification with better performance
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
      
      // Use requestAnimationFrame for better performance
      requestAnimationFrame(() => {
        notification.classList.remove('translate-x-full');
      });
      
      // Auto remove after 5 seconds
      setTimeout(() => {
        if (notification.parentElement) {
          notification.classList.add('translate-x-full');
          setTimeout(() => {
            if (notification.parentElement) {
              notification.remove();
            }
          }, 300);
        }
      }, 5000);
    }
  }

  showLoading() {
    if (this.loadingIndicator) {
      this.loadingIndicator.classList.remove('hidden');
    }
  }

  hideLoading() {
    if (this.loadingIndicator) {
      this.loadingIndicator.classList.add('hidden');
    }
  }

  getCollegeSlug() {
    // Extract college slug from URL or data attribute
    const urlParts = window.location.pathname.split('/');
    return urlParts[2] || 'default';
  }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new CanteenDashboard();
});
