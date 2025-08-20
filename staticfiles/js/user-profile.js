// User Profile Management JavaScript - External file for better security and maintainability
class UserProfileManager {
  constructor() {
    this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    this.initializeEventListeners();
  }

  initializeEventListeners() {
    // Remove favorite buttons
    document.addEventListener('click', (e) => {
      if (e.target.closest('[data-action="remove-favorite"]')) {
        e.preventDefault();
        const itemId = e.target.closest('[data-action="remove-favorite"]').getAttribute('data-item-id');
        this.removeFavorite(itemId);
      }
      
      // Add to cart from favorites buttons
      if (e.target.closest('[data-action="add-to-cart-favorite"]')) {
        e.preventDefault();
        const itemId = e.target.closest('[data-action="add-to-cart-favorite"]').getAttribute('data-item-id');
        this.addToCartFromFavorites(itemId);
      }
    });

    // Global error handlers - only show errors for critical issues
    window.addEventListener('error', (e) => {
      console.error('Global error in user profile:', e.error);
      // Only show notification for critical errors, not all errors
      if (e.error && e.error.message && e.error.message.includes('fetch')) {
        this.showNotification('Network error. Please check your connection.', 'error');
      }
    });

    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled promise rejection in user profile:', e.reason);
      // Only show notification for network errors
      if (e.reason && e.reason.message && e.reason.message.includes('fetch')) {
        this.showNotification('Network error. Please try again.', 'error');
      }
    });
  }

  async removeFavorite(itemId) {
    if (!this.csrfToken) {
      this.showNotification('Security token not found. Please refresh the page.', 'error');
      return;
    }

    if (!confirm('Remove this item from favorites?')) {
      return;
    }
    
    try {
      const response = await fetch(`/toggle-favorite/${itemId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': this.csrfToken
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          // Remove the item from the DOM
          const itemElement = document.querySelector(`[data-item-id="${itemId}"]`);
          if (itemElement) {
            itemElement.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
              itemElement.remove();
            }, 300);
          }
          
          // Check if no more favorites
          const favoritesContainer = document.querySelector('.grid');
          if (favoritesContainer && favoritesContainer.children.length === 0) {
            location.reload(); // Reload to show empty state
          }
          
          this.showNotification('Item removed from favorites', 'success');
        } else {
          this.showNotification(data.error || 'Failed to remove favorite', 'error');
        }
      } else {
        this.showNotification('Failed to remove favorite', 'error');
      }
    } catch (error) {
      console.error('Error removing favorite:', error);
      this.showNotification('Error removing favorite', 'error');
    }
  }

  async addToCartFromFavorites(itemId) {
    if (!this.csrfToken) {
      this.showNotification('Security token not found. Please refresh the page.', 'error');
      return;
    }

    try {
      const response = await fetch(`/add-to-cart/${itemId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': this.csrfToken
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          this.showNotification('Item added to cart!', 'success');
          
          // Update cart count if available
          if (data.cart_count !== undefined) {
            this.updateCartCount(data.cart_count);
          }
        } else {
          this.showNotification(data.error || 'Failed to add item to cart', 'error');
        }
      } else {
        this.showNotification('Failed to add item to cart', 'error');
      }
    } catch (error) {
      console.error('Error adding to cart:', error);
      this.showNotification('Error adding item to cart', 'error');
    }
  }

  updateCartCount(count) {
    const cartCountElement = document.getElementById('cart-count');
    if (cartCountElement) {
      cartCountElement.textContent = count;
    }
    
    // Dispatch custom event for other components
    window.dispatchEvent(new CustomEvent('cartUpdated', { detail: { count } }));
  }

  showNotification(message, type = 'info') {
    if (typeof window.showNotification === 'function') {
      window.showNotification(message, type);
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
      }, 5000);
    }
  }
}

// Initialize user profile manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new UserProfileManager();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeOut {
    from { opacity: 1; }
    to { opacity: 0; }
  }
`;
document.head.appendChild(style);
