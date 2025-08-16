// UI Utilities JavaScript - External file for better security and maintainability
class UIUtilities {
  constructor() {
    this.initializeEventListeners();
  }

  initializeEventListeners() {
    // Close message buttons (login page)
    document.addEventListener('click', (e) => {
      if (e.target.closest('[data-action="close-message"]')) {
        e.preventDefault();
        const messageElement = e.target.closest('[data-action="close-message"]').parentElement;
        if (messageElement) {
          messageElement.remove();
        }
      }
      
      // Close edit modal buttons (manage menu items)
      if (e.target.closest('[data-action="close-edit-modal"]')) {
        e.preventDefault();
        this.closeEditModal();
      }
      
      // Close notification buttons
      if (e.target.closest('[data-action="close-notification"]')) {
        e.preventDefault();
        const notificationElement = e.target.closest('[data-action="close-notification"]').parentElement.parentElement;
        if (notificationElement) {
          notificationElement.remove();
        }
      }
    });

    // Global error handlers
    window.addEventListener('error', (e) => {
      console.error('Global error in UI utilities:', e.error);
    });

    window.addEventListener('unhandledrejection', (e) => {
      console.error('Unhandled promise rejection in UI utilities:', e.reason);
    });
  }

  closeEditModal() {
    const editModal = document.getElementById('editModal');
    if (editModal) {
      editModal.classList.add('hidden');
    }
  }

  // Enhanced notification system for canteen manage menu
  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const bgColor = type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500';
    const icon = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';
    
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${bgColor} text-white transform transition-all duration-300 translate-x-full`;
    notification.innerHTML = `
      <div class="flex items-center">
        <span class="mr-2 text-lg">${icon}</span>
        <span class="flex-1">${message}</span>
        <button data-action="close-notification" class="ml-3 text-white hover:text-gray-200 transition-colors">
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

// Initialize UI utilities when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.uiUtilities = new UIUtilities();
});

// Make functions globally available for backward compatibility
window.showNotification = function(message, type = 'info') {
  if (window.uiUtilities) {
    window.uiUtilities.showNotification(message, type);
  }
};

window.closeEditModal = function() {
  if (window.uiUtilities) {
    window.uiUtilities.closeEditModal();
  }
};
