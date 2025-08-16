// Favorites Management JavaScript - External file for better security and maintainability
class FavoritesManager {
  constructor() {
    this.initializeEventListeners();
  }

  initializeEventListeners() {
    // Add to cart functionality
    document.querySelectorAll('.add-to-cart-form').forEach(form => {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this.handleAddToCart(e, form);
      });
    });

    // Event delegation for favorite toggle buttons
    document.addEventListener('click', (e) => {
      if (e.target.closest('[data-action="toggle-favorite"]')) {
        e.preventDefault();
        const button = e.target.closest('[data-action="toggle-favorite"]');
        const itemId = button.getAttribute('data-item-id');
        this.toggleFavorite(itemId);
      }
    });

    // Global error handlers
    window.addEventListener('error', (e) => {
      console.error('Global error in favorites:', e.error);
      this.showNotification('An unexpected error occurred. Please check the console.', 'error');
    });

    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled promise rejection in favorites:', e.reason);
      this.showNotification('A network error occurred. Please try again.', 'error');
    });
  }

  async handleAddToCart(e, form) {
    const formData = new FormData(form);
    const itemCard = form.closest('[data-item-id]');
    const itemName = itemCard.querySelector('h3').textContent;
    const button = form.querySelector('button');
    const originalText = button.innerHTML;
    
    // Show loading state
    button.disabled = true;
    button.innerHTML = '<svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg> Adding...';
    
    // Show notification
    this.showNotification(`Adding ${itemName} to cart...`, 'info');
    
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': formData.get('csrfmiddlewaretoken')
        }
      });

      if (response.redirected) {
        // Redirect to login page
        window.location.href = response.url;
        return;
      }
      
      if (response.ok) {
        // Success animation
        this.showNotification(`${itemName} added to cart!`, 'success');
        
        // Add success animation to card
        itemCard.style.transform = 'scale(1.05)';
        setTimeout(() => {
          itemCard.style.transform = '';
        }, 200);
      } else {
        // Error handling
        this.showNotification(`Error adding ${itemName} to cart`, 'error');
        button.disabled = false;
        button.innerHTML = originalText;
      }
    } catch (error) {
      console.error('Error:', error);
      this.showNotification('Network error. Please try again.', 'error');
      button.disabled = false;
      button.innerHTML = originalText;
    }
  }

  async toggleFavorite(itemId) {
    const button = document.querySelector(`[data-item-id="${itemId}"].favorite-btn`);
    if (!button) return;
    
    const originalHTML = button.innerHTML;
    
    // Get CSRF token from the hidden form
    const csrfForm = document.getElementById('csrf-form');
    if (!csrfForm) {
      this.showNotification('Security token not found. Please refresh the page.', 'error');
      return;
    }
    
    const csrfToken = csrfForm.querySelector('input[name="csrfmiddlewaretoken"]').value;
    
    try {
      const response = await fetch(`/toggle-favorite/${itemId}/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
        }
      });

      const data = await response.json();
      
      if (data.success) {
        if (data.is_favorite) {
          button.className = 'bg-yellow-500 text-white p-2 rounded-lg hover:bg-yellow-600 transition duration-300 favorite-btn';
          button.innerHTML = '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>';
        } else {
          // Remove from favorites page
          const itemCard = button.closest('[data-item-id]');
          itemCard.style.transform = 'scale(0.95)';
          setTimeout(() => {
            itemCard.remove();
            // Check if no more items
            const remainingItems = document.querySelectorAll('[data-item-id]');
            if (remainingItems.length === 0) {
              location.reload(); // Reload to show empty state
            }
          }, 300);
        }
        
        // Show notification
        this.showNotification(data.message, 'success');
      } else {
        // Show error notification
        this.showNotification(data.error || 'Error updating favorite', 'error');
      }
    } catch (error) {
      console.error('Error:', error);
      button.innerHTML = originalHTML;
      this.showNotification('Network error. Please try again.', 'error');
    }
  }

  showNotification(message, type = 'info') {
    if (typeof window.showNotification === 'function') {
      window.showNotification(message, type);
    } else {
      // Fallback notification using existing notification element
      const notification = document.getElementById('cartNotification');
      const messageElement = document.getElementById('cartMessage');
      
      if (notification && messageElement) {
        messageElement.textContent = message;
        
        const bgColor = type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500';
        notification.className = `fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg transform transition-transform duration-300 z-50`;
        notification.classList.remove('translate-x-full');
        
        // Hide notification after 3 seconds
        setTimeout(() => {
          notification.classList.add('translate-x-full');
        }, 3000);
      }
    }
  }
}

// Initialize favorites manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  new FavoritesManager();
});
