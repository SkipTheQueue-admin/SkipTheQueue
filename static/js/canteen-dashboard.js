// Performance-optimized JavaScript for canteen dashboard

// Cache DOM elements and constants for better performance
const CACHE = {
  csrfToken: null,
  loadingIndicator: null,
  refreshTimer: null,
  isRefreshing: false,
  collegeSlug: null
};

// Debounce function to prevent excessive function calls
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Initialize dashboard on DOM load
document.addEventListener('DOMContentLoaded', function() {
  initializeDashboard();
});

function initializeDashboard() {
  // Cache frequently used DOM elements
  CACHE.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  CACHE.loadingIndicator = document.getElementById('loading-indicator');
  CACHE.collegeSlug = document.querySelector('[data-college-slug]')?.dataset.collegeSlug;
  
  if (!CACHE.csrfToken) {
    console.error('CSRF token not found on page load');
    showNotification('Security configuration error. Please refresh the page.', 'error');
    return;
  }
  
  console.log('Canteen dashboard initialized successfully');
  
  // Start smart auto-refresh
  startSmartRefresh();
}

// Smart auto-refresh that only refreshes when no operations are in progress
function startSmartRefresh() {
  CACHE.refreshTimer = setInterval(() => {
    if (!CACHE.isRefreshing) {
      location.reload();
    } else {
      console.log('Skipping auto-refresh - operations in progress');
    }
  }, 30000);
}

// Function to accept order - optimized with debouncing
const acceptOrder = debounce(async function(orderId) {
  if (CACHE.isRefreshing) return;
  
  CACHE.isRefreshing = true;
  showLoading();
  
  const orderElement = document.querySelector(`[data-order-id="${orderId}"]`);
  const button = orderElement?.querySelector('.accept-btn');
  
  if (button) {
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Accepting...';
  }
  
  try {
    const response = await fetch(`/canteen/dashboard/${CACHE.collegeSlug}/accept-order/${orderId}/`, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': CACHE.csrfToken
      },
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        showNotification('Order accepted successfully!', 'success');
        setTimeout(() => location.reload(), 1000);
      } else {
        showNotification(data.error || 'Failed to accept order', 'error');
        resetButton(button, 'Accept Order', 'fas fa-check');
      }
    } else {
      showNotification('Failed to accept order', 'error');
      resetButton(button, 'Accept Order', 'fas fa-check');
    }
  } catch (error) {
    console.error('Error accepting order:', error);
    showNotification('Error accepting order', 'error');
    resetButton(button, 'Accept Order', 'fas fa-check');
  } finally {
    hideLoading();
    CACHE.isRefreshing = false;
  }
}, 300);

// Function to decline order - optimized with debouncing
const declineOrder = debounce(async function(orderId) {
  if (CACHE.isRefreshing) return;
  if (!confirm('Are you sure you want to decline this order?')) return;
  
  CACHE.isRefreshing = true;
  
  const orderElement = document.querySelector(`[data-order-id="${orderId}"]`);
  const button = orderElement?.querySelector('.decline-btn');
  
  if (button) {
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Declining...';
  }
  
  try {
    const response = await fetch(`/canteen/dashboard/${CACHE.collegeSlug}/decline-order/${orderId}/`, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': CACHE.csrfToken
      },
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        showNotification('Order declined successfully!', 'success');
        setTimeout(() => location.reload(), 1000);
      } else {
        showNotification(data.error || 'Failed to decline order', 'error');
        resetButton(button, 'Decline', 'fas fa-times');
      }
    } else {
      showNotification('Failed to decline order', 'error');
      resetButton(button, 'Decline', 'fas fa-times');
    }
  } catch (error) {
    console.error('Error declining order:', error);
    showNotification('Error declining order', 'error');
    resetButton(button, 'Decline', 'fas fa-times');
  } finally {
    CACHE.isRefreshing = false;
  }
}, 300);

// Function to mark order as ready - optimized with debouncing
const markOrderReady = debounce(async function(orderId) {
  if (CACHE.isRefreshing) return;
  
  CACHE.isRefreshing = true;
  
  const orderElement = document.querySelector(`[data-order-id="${orderId}"]`);
  const button = orderElement?.querySelector('.mark-ready-btn');
  
  if (button) {
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Updating...';
  }
  
  try {
    const response = await fetch(`/canteen/dashboard/${CACHE.collegeSlug}/update-status/${orderId}/`, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': CACHE.csrfToken
      },
      body: `status=Ready`,
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        showNotification('Order marked as ready! Customer will be notified.', 'success');
        setTimeout(() => location.reload(), 1000);
      } else {
        showNotification(data.error || 'Failed to update order status', 'error');
        resetButton(button, 'Mark Ready', 'fas fa-check-circle');
      }
    } else {
      showNotification('Failed to update order status', 'error');
      resetButton(button, 'Mark Ready', 'fas fa-check-circle');
    }
  } catch (error) {
    console.error('Error updating order status:', error);
    showNotification('Error updating order status', 'error');
    resetButton(button, 'Mark Ready', 'fas fa-check-circle');
  } finally {
    CACHE.isRefreshing = false;
  }
}, 300);

// Function to mark order as completed - optimized with debouncing
const markOrderCompleted = debounce(async function(orderId) {
  if (CACHE.isRefreshing) return;
  
  CACHE.isRefreshing = true;
  
  const orderElement = document.querySelector(`[data-order-id="${orderId}"]`);
  const button = orderElement?.querySelector('.complete-order-btn');
  
  if (button) {
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Updating...';
  }
  
  try {
    const response = await fetch(`/canteen/dashboard/${CACHE.collegeSlug}/update-status/${orderId}/`, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': CACHE.csrfToken
      },
      body: `status=Completed`,
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        showNotification('Order marked as completed!', 'success');
        setTimeout(() => location.reload(), 1000);
      } else {
        showNotification(data.error || 'Failed to update order status', 'error');
        resetButton(button, 'Mark Completed', 'fas fa-check-double');
      }
    } else {
      showNotification('Failed to update order status', 'error');
      resetButton(button, 'Mark Completed', 'fas fa-check-double');
    }
  } catch (error) {
    console.error('Error updating order status:', error);
    showNotification('Error updating order status', 'error');
    resetButton(button, 'Mark Completed', 'fas fa-check-double');
  } finally {
    CACHE.isRefreshing = false;
  }
}, 300);

// Utility function to reset button state
function resetButton(button, text, iconClass) {
  if (button) {
    button.disabled = false;
    button.innerHTML = `<i class="${iconClass} mr-2"></i>${text}`;
  }
}

// Optimized notification system
function showNotification(message, type = 'info') {
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

// Optimized loading state management
function showLoading() {
  if (CACHE.loadingIndicator) {
    CACHE.loadingIndicator.classList.remove('hidden');
  }
}

function hideLoading() {
  if (CACHE.loadingIndicator) {
    CACHE.loadingIndicator.classList.add('hidden');
  }
}

// Global error handlers with better performance
window.addEventListener('error', function(e) {
  console.error('Global error in canteen dashboard:', e.error);
  showNotification('An unexpected error occurred. Please check the console.', 'error');
});

window.addEventListener('unhandledrejection', function(e) {
  console.error('Unhandled promise rejection in canteen dashboard:', e.reason);
  showNotification('A network error occurred. Please try again.', 'error');
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (CACHE.refreshTimer) {
    clearInterval(CACHE.refreshTimer);
  }
});

// Make functions globally available
window.acceptOrder = acceptOrder;
window.declineOrder = declineOrder;
window.markOrderReady = markOrderReady;
window.markOrderCompleted = markOrderCompleted;
