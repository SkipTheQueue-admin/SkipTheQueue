// Menu Management JavaScript - External file for better security and maintainability
class MenuManager {
  constructor() {
    this.currentItemId = null;
    this.currentQuantity = 1;
    this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    this.initializeEventListeners();
    this.initializeCartModal();
  }

  initializeEventListeners() {
    // Add to cart buttons
    document.addEventListener('click', (e) => {
      if (e.target.closest('[data-action="add-to-cart"]')) {
        e.preventDefault();
        const itemId = e.target.closest('[data-action="add-to-cart"]').getAttribute('data-item-id');
        this.addToCart(itemId);
      }
      
      // Toggle favorite buttons
      if (e.target.closest('[data-action="toggle-favorite"]')) {
        e.preventDefault();
        const itemId = e.target.closest('[data-action="toggle-favorite"]').getAttribute('data-item-id');
        this.toggleFavorite(itemId);
      }
      
      // Remove from favorites buttons
      if (e.target.closest('[data-action="remove-favorite"]')) {
        e.preventDefault();
        const itemId = e.target.closest('[data-action="remove-favorite"]').getAttribute('data-item-id');
        this.removeFromFavorites(itemId);
      }
    });

    // Cart modal controls
    document.addEventListener('click', (e) => {
      if (e.target.closest('[data-action="decrease-quantity"]')) {
        e.preventDefault();
        this.decreaseQuantity();
      }
      
      if (e.target.closest('[data-action="increase-quantity"]')) {
        e.preventDefault();
        this.increaseQuantity();
      }
      
      if (e.target.closest('[data-action="close-cart-modal"]')) {
        e.preventDefault();
        this.closeCartModal();
      }
      
      if (e.target.closest('[data-action="confirm-add-to-cart"]')) {
        e.preventDefault();
        this.confirmAddToCart();
      }
    });

    // Global error handlers - only show errors for critical issues
    window.addEventListener('error', (e) => {
      console.error('Global error in menu:', e.error);
      // Only show notification for critical errors, not all errors
      if (e.error && e.error.message && e.error.message.includes('fetch')) {
        this.showNotification('Network error. Please check your connection.', 'error');
      }
    });

    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled promise rejection in menu:', e.reason);
      // Only show notification for network errors
      if (e.reason && e.reason.message && e.reason.message.includes('fetch')) {
        this.showNotification('Network error. Please try again.', 'error');
      }
    });
  }

  initializeCartModal() {
    // Create modal if it doesn't exist
    if (!document.getElementById('cart-modal')) {
      this.createCartModal();
    }
  }

  createCartModal() {
    const modal = document.createElement('div');
    modal.id = 'cart-modal';
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 hidden';
    modal.innerHTML = `
      <div class="flex items-center justify-center min-h-screen p-4">
        <div class="bg-white rounded-lg max-w-md w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-900">Add to Cart</h3>
            <button data-action="close-cart-modal" class="text-gray-400 hover:text-gray-600 transition-colors">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
          
          <div id="modal-item-details" class="mb-4">
            <!-- Item details will be populated here -->
          </div>
          
          <div class="flex items-center justify-center gap-4 mb-6">
            <button data-action="decrease-quantity" class="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center hover:bg-gray-300 transition-colors">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"></path>
              </svg>
            </button>
            
            <span id="modal-quantity" class="text-2xl font-bold text-gray-900 mx-4">1</span>
            
            <button data-action="increase-quantity" class="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center hover:bg-gray-300 transition-colors">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
              </svg>
            </button>
          </div>
          
          <div class="flex gap-3">
            <button data-action="close-cart-modal" class="flex-1 bg-gray-200 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-300 transition-colors">
              Cancel
            </button>
            <button data-action="confirm-add-to-cart" class="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors">
              Add to Cart
            </button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  async addToCart(itemId) {
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
          // Update cart count
          this.updateCartCount(data.cart_count);
          
          // Show success message
          this.showNotification(data.message, 'success');
          
          // Update cart badge
          const cartBadge = document.querySelector('.cart-badge');
          if (cartBadge) {
            cartBadge.textContent = data.cart_count;
            cartBadge.classList.remove('hidden');
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

  async toggleFavorite(itemId) {
    if (!this.csrfToken) {
      this.showNotification('Security token not found. Please refresh the page.', 'error');
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
          // Update favorite button state
          const favoriteBtn = document.querySelector(`.favorite-btn-${itemId}`);
          if (favoriteBtn) {
            favoriteBtn.setAttribute('data-is-favorite', data.is_favorite);
            const icon = favoriteBtn.querySelector('svg');
            if (icon) {
              icon.setAttribute('fill', data.is_favorite ? 'currentColor' : 'none');
            }
          }
          
          this.showNotification(data.message, 'success');
        } else {
          this.showNotification(data.error || 'Failed to toggle favorite', 'error');
        }
      } else {
        this.showNotification('Failed to toggle favorite', 'error');
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
      this.showNotification('Error toggling favorite', 'error');
    }
  }

  async removeFromFavorites(itemId) {
    if (!this.csrfToken) {
      this.showNotification('Security token not found. Please refresh the page.', 'error');
      return;
    }

    try {
      const response = await fetch(`/remove-favorite/${itemId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': this.csrfToken
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          // Remove item from DOM
          const itemElement = document.querySelector(`[data-item-id="${itemId}"]`);
          if (itemElement) {
            itemElement.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
              itemElement.remove();
            }, 300);
          }
          
          this.showNotification(data.message, 'success');
        } else {
          this.showNotification(data.error || 'Failed to remove from favorites', 'error');
        }
      } else {
        this.showNotification('Failed to remove from favorites', 'error');
      }
    } catch (error) {
      console.error('Error removing from favorites:', error);
      this.showNotification('Error removing from favorites', 'error');
    }
  }

  showCartModal(itemId, itemName, itemPrice) {
    this.currentItemId = itemId;
    this.currentQuantity = 1;
    
    // Update modal content
    const modal = document.getElementById('cart-modal');
    const itemDetails = modal.querySelector('#modal-item-details');
    const quantityDisplay = modal.querySelector('#modal-quantity');
    
    itemDetails.innerHTML = `
      <div class="text-center">
        <h4 class="font-semibold text-gray-900 mb-2">${itemName}</h4>
        <p class="text-blue-600 font-bold">₹${itemPrice}</p>
      </div>
    `;
    
    quantityDisplay.textContent = this.currentQuantity;
    
    // Show modal
    modal.classList.remove('hidden');
    modal.style.animation = 'fadeIn 0.3s ease-out';
  }

  closeCartModal() {
    const modal = document.getElementById('cart-modal');
    modal.style.animation = 'fadeOut 0.3s ease-out';
    setTimeout(() => {
      modal.classList.add('hidden');
    }, 300);
    
    this.currentItemId = null;
    this.currentQuantity = 1;
  }

  decreaseQuantity() {
    if (this.currentQuantity > 1) {
      this.currentQuantity--;
      document.getElementById('modal-quantity').textContent = this.currentQuantity;
    }
  }

  increaseQuantity() {
    this.currentQuantity++;
    document.getElementById('modal-quantity').textContent = this.currentQuantity;
  }

  async confirmAddToCart() {
    if (!this.currentItemId) return;
    
    try {
      const response = await fetch(`/add-to-cart/${this.currentItemId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': this.csrfToken,
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: `quantity=${this.currentQuantity}`
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          this.updateCartCount(data.cart_count);
          this.showNotification(data.message, 'success');
          this.closeCartModal();
          
          // Update cart badge
          const cartBadge = document.querySelector('.cart-badge');
          if (cartBadge) {
            cartBadge.textContent = data.cart_count;
            cartBadge.classList.remove('hidden');
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

// Initialize menu manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new MenuManager();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  @keyframes fadeOut {
    from { opacity: 1; }
    to { opacity: 0; }
  }
`;
document.head.appendChild(style);
