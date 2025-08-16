// 🚀 SkipTheQueue Performance Optimized JavaScript
// This file consolidates all inline scripts and implements performance optimizations

class PerformanceOptimizer {
  constructor() {
    this.cache = new Map();
    this.debounceTimers = new Map();
    this.throttleTimers = new Map();
    this.observers = [];
    this.cleanupFunctions = [];
    
    this.init();
  }

  init() {
    this.setupPerformanceMonitoring();
    this.setupGlobalEventListeners();
    this.initializePageSpecificOptimizations();
  }

  // 🎯 DEBOUNCING & THROTTLING
  debounce(func, delay = 300) {
    const key = func.toString();
    return (...args) => {
      clearTimeout(this.debounceTimers.get(key));
      const timer = setTimeout(() => func.apply(this, args), delay);
      this.debounceTimers.set(key, timer);
    };
  }

  throttle(func, delay = 100) {
    const key = func.toString();
    return (...args) => {
      if (this.throttleTimers.has(key)) return;
      
      func.apply(this, args);
      this.throttleTimers.set(key, true);
      setTimeout(() => this.throttleTimers.delete(key), delay);
    };
  }

  // 🗄️ DOM CACHING
  getCachedElement(selector) {
    if (!this.cache.has(selector)) {
      this.cache.set(selector, document.querySelector(selector));
    }
    return this.cache.get(selector);
  }

  getCachedElements(selector) {
    const cacheKey = `elements:${selector}`;
    if (!this.cache.has(cacheKey)) {
      this.cache.set(cacheKey, document.querySelectorAll(selector));
    }
    return this.cache.get(cacheKey);
  }

  // 🔄 SMART AJAX UPDATES (REPLACES HARD RELOADS)
  async smartUpdate(url, options = {}) {
    try {
      const response = await fetch(url, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': this.getCSRFToken(),
          ...options.headers
        },
        ...options
      });

      if (response.ok) {
        const data = await response.json();
        this.updatePageContent(data);
        return data;
      }
    } catch (error) {
      console.error('Smart update failed:', error);
      this.showNotification('Update failed. Please refresh the page.', 'error');
    }
  }

  updatePageContent(data) {
    // Update specific page content without full reload
    if (data.cart_count !== undefined) {
      this.updateCartCount(data.cart_count);
    }
    if (data.orders) {
      this.updateOrdersList(data.orders);
    }
    if (data.menu_items) {
      this.updateMenuItems(data.menu_items);
    }
  }

  // 🛒 OPTIMIZED CART MANAGEMENT
  updateCartCount = this.debounce(async (forceCount = null) => {
    try {
      let count = forceCount;
      
      if (count === null) {
        const response = await fetch('/api/cart-count/');
        if (response.ok) {
          const data = await response.json();
          count = data.count || 0;
        } else {
          // Fallback: count from DOM
          const cartItems = this.getCachedElements('[data-item-id]');
          count = cartItems.length;
        }
      }

      const cartCountElement = this.getCachedElement('#cart-count');
      if (cartCountElement) {
        const oldCount = parseInt(cartCountElement.textContent) || 0;
        cartCountElement.textContent = count;
        
        // Animate only if count increased
        if (count > oldCount) {
          cartCountElement.classList.add('animate-bounce');
          setTimeout(() => cartCountElement.classList.remove('animate-bounce'), 1000);
        }
        
        // Update cart badge visibility
        const cartBadge = this.getCachedElement('.cart-badge');
        if (cartBadge) {
          cartBadge.classList.toggle('hidden', count === 0);
        }
      }
    } catch (error) {
      console.error('Cart count update failed:', error);
    }
  }, 100);

  // 📊 PERFORMANCE MONITORING
  setupPerformanceMonitoring() {
    if ('PerformanceObserver' in window) {
      // Monitor Core Web Vitals
      const observer = new PerformanceObserver((list) => {
        list.getEntries().forEach((entry) => {
          if (entry.entryType === 'largest-contentful-paint') {
            this.metrics.lcp = entry.startTime;
          } else if (entry.entryType === 'first-input') {
            this.metrics.fid = entry.processingStart - entry.startTime;
          }
        });
      });
      
      observer.observe({ entryTypes: ['largest-contentful-paint', 'first-input'] });
      this.observers.push(observer);
    }
  }

  // 🌐 GLOBAL EVENT LISTENERS
  setupGlobalEventListeners() {
    // Optimized error handling
    window.addEventListener('error', this.throttle((e) => {
      console.error('Global error:', e.error);
      this.showNotification('An error occurred. Please try again.', 'error');
    }, 1000));

    window.addEventListener('unhandledrejection', this.throttle((e) => {
      console.error('Unhandled promise rejection:', e.reason);
      this.showNotification('Network error. Please check your connection.', 'error');
    }, 1000));

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
      this.cleanup();
    });
  }

  // 🎨 NOTIFICATION SYSTEM
  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const bgColor = {
      success: 'bg-green-500',
      error: 'bg-red-500',
      warning: 'bg-yellow-500',
      info: 'bg-blue-500'
    }[type] || 'bg-blue-500';

    const icon = {
      success: '✓',
      error: '✗',
      warning: '⚠',
      info: 'ℹ'
    }[type] || 'ℹ';

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
    
    // Use requestAnimationFrame for smooth animation
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

  // 🔧 UTILITY FUNCTIONS
  getCSRFToken() {
    return this.getCachedElement('[name=csrf-token]')?.content || 
           this.getCachedElement('[name=csrfmiddlewaretoken]')?.value;
  }

  // 🧹 CLEANUP
  cleanup() {
    // Clear all timers
    this.debounceTimers.forEach(timer => clearTimeout(timer));
    this.throttleTimers.clear();
    
    // Disconnect observers
    this.observers.forEach(observer => observer.disconnect());
    
    // Run cleanup functions
    this.cleanupFunctions.forEach(cleanup => cleanup());
    
    // Clear cache
    this.cache.clear();
  }

  // 📄 PAGE-SPECIFIC OPTIMIZATIONS
  initializePageSpecificOptimizations() {
    const path = window.location.pathname;
    
    if (path.includes('/canteen/dashboard/')) {
      this.initializeCanteenDashboard();
    } else if (path.includes('/canteen/manage-menu/')) {
      this.initializeMenuManagement();
    } else if (path.includes('/track-order/')) {
      this.initializeOrderTracking();
    } else if (path.includes('/cart/')) {
      this.initializeCartPage();
    } else if (path.includes('/menu/')) {
      this.initializeMenuPage();
    } else if (path.includes('/favorites/')) {
      this.initializeFavoritesPage();
    } else if (path.includes('/order-history/')) {
      this.initializeOrderHistory();
    } else if (path.includes('/profile/')) {
      this.initializeProfilePage();
    } else if (path.includes('/help/')) {
      this.initializeHelpPage();
    } else if (path.includes('/admin/')) {
      this.initializeAdminPages();
    } else {
      this.initializeGeneralPage();
    }
  }

  // 🏪 CANTEEN DASHBOARD OPTIMIZATIONS
  initializeCanteenDashboard() {
    // Replace hard reloads with smart updates
    const smartRefresh = this.debounce(async () => {
      await this.smartUpdate('/api/canteen/orders/');
    }, 5000);

    // Set up smart refresh instead of hard reload
    setInterval(smartRefresh, 30000);
    
    // Optimize order action buttons
    document.addEventListener('click', this.throttle((e) => {
      const target = e.target;
      
      if (target.classList.contains('accept-btn')) {
        this.handleOrderAction('accept', target.dataset.orderId);
      } else if (target.classList.contains('decline-btn')) {
        this.handleOrderAction('decline', target.dataset.orderId);
      } else if (target.classList.contains('ready-btn')) {
        this.handleOrderAction('ready', target.dataset.orderId);
      } else if (target.classList.contains('complete-btn')) {
        this.handleOrderAction('complete', target.dataset.orderId);
      }
    }, 300));
  }

  // 🍽️ MENU MANAGEMENT OPTIMIZATIONS
  initializeMenuManagement() {
    // Optimize form submissions
    const forms = this.getCachedElements('form');
    forms.forEach(form => {
      form.addEventListener('submit', this.debounce(async (e) => {
        e.preventDefault();
        await this.handleFormSubmission(form);
      }, 300));
    });

    // Optimize image uploads
    const fileInputs = this.getCachedElements('input[type="file"]');
    fileInputs.forEach(input => {
      input.addEventListener('change', this.throttle((e) => {
        this.handleImageUpload(e.target);
      }, 500));
    });
  }

  // 📦 ORDER TRACKING OPTIMIZATIONS
  initializeOrderTracking() {
    // Smart order status updates
    const updateOrderStatus = this.debounce(async () => {
      const orderId = this.getCachedElement('[data-order-id]')?.dataset.orderId;
      if (orderId) {
        await this.smartUpdate(`/api/order-status/${orderId}/`);
      }
    }, 2000);

    setInterval(updateOrderStatus, 10000);
  }

  // 🛒 CART PAGE OPTIMIZATIONS
  initializeCartPage() {
    // Optimize quantity changes
    const quantityInputs = this.getCachedElements('input[type="number"]');
    quantityInputs.forEach(input => {
      input.addEventListener('change', this.debounce(async (e) => {
        await this.updateCartItem(e.target);
      }, 500));
    });
  }

  // 🍽️ MENU PAGE OPTIMIZATIONS
  initializeMenuPage() {
    // Lazy load images
    this.setupLazyLoading();
    
    // Optimize search
    const searchInput = this.getCachedElement('#search-input');
    if (searchInput) {
      searchInput.addEventListener('input', this.debounce(async (e) => {
        await this.handleSearch(e.target.value);
      }, 300));
    }
  }

  // ❤️ FAVORITES PAGE OPTIMIZATIONS
  initializeFavoritesPage() {
    // Optimize favorite toggles
    document.addEventListener('click', this.throttle((e) => {
      if (e.target.classList.contains('favorite-btn')) {
        this.toggleFavorite(e.target);
      }
    }, 300));
  }

  // 📋 ORDER HISTORY OPTIMIZATIONS
  initializeOrderHistory() {
    // Lazy load order details
    this.setupLazyLoading();
    
    // Optimize pagination
    const paginationLinks = this.getCachedElements('.pagination a');
    paginationLinks.forEach(link => {
      link.addEventListener('click', this.debounce(async (e) => {
        e.preventDefault();
        await this.loadPage(link.href);
      }, 300));
    });
  }

  // 👤 PROFILE PAGE OPTIMIZATIONS
  initializeProfilePage() {
    // Optimize form validation
    const forms = this.getCachedElements('form');
    forms.forEach(form => {
      form.addEventListener('submit', this.debounce(async (e) => {
        if (!this.validateForm(form)) {
          e.preventDefault();
          return;
        }
      }, 300));
    });
  }

  // ❓ HELP PAGE OPTIMIZATIONS
  initializeHelpPage() {
    // Optimize search functionality
    const searchInput = this.getCachedElement('#help-search');
    if (searchInput) {
      searchInput.addEventListener('input', this.debounce(async (e) => {
        await this.searchHelp(e.target.value);
      }, 300));
    }
  }

  // 👨‍💼 ADMIN PAGES OPTIMIZATIONS
  initializeAdminPages() {
    // Optimize bulk operations
    const bulkCheckboxes = this.getCachedElements('input[type="checkbox"]');
    bulkCheckboxes.forEach(checkbox => {
      checkbox.addEventListener('change', this.debounce(() => {
        this.updateBulkActions();
      }, 300));
    });
  }

  // 🏠 GENERAL PAGE OPTIMIZATIONS
  initializeGeneralPage() {
    // Setup lazy loading for all pages
    this.setupLazyLoading();
    
    // Optimize mobile menu
    const mobileMenuToggle = this.getCachedElement('[data-mobile-menu-toggle]');
    if (mobileMenuToggle) {
      mobileMenuToggle.addEventListener('click', this.throttle(() => {
        this.toggleMobileMenu();
      }, 300));
    }
  }

  // 🖼️ LAZY LOADING SETUP
  setupLazyLoading() {
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.classList.remove('lazy');
            imageObserver.unobserve(img);
          }
        });
      });

      const lazyImages = this.getCachedElements('img[data-src]');
      lazyImages.forEach(img => imageObserver.observe(img));
      
      this.observers.push(imageObserver);
    }
  }

  // 🔍 SEARCH OPTIMIZATION
  async handleSearch(query) {
    try {
      const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`);
      if (response.ok) {
        const data = await response.json();
        this.updateSearchResults(data.results);
      }
    } catch (error) {
      console.error('Search failed:', error);
    }
  }

  // 📝 FORM VALIDATION
  validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
      if (!input.value.trim()) {
        this.showFieldError(input, 'This field is required');
        isValid = false;
      } else {
        this.clearFieldError(input);
      }
    });

    return isValid;
  }

  showFieldError(input, message) {
    const errorElement = input.parentNode.querySelector('.field-error') || 
                        document.createElement('div');
    errorElement.className = 'field-error text-red-500 text-sm mt-1';
    errorElement.textContent = message;
    
    if (!input.parentNode.querySelector('.field-error')) {
      input.parentNode.appendChild(errorElement);
    }
    
    input.classList.add('border-red-500');
  }

  clearFieldError(input) {
    const errorElement = input.parentNode.querySelector('.field-error');
    if (errorElement) {
      errorElement.remove();
    }
    input.classList.remove('border-red-500');
  }

  // 🎯 ORDER ACTION HANDLING
  async handleOrderAction(action, orderId) {
    if (!orderId) return;

    const button = this.getCachedElement(`[data-order-id="${orderId}"] .${action}-btn`);
    if (button) {
      button.disabled = true;
      button.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i>${action.charAt(0).toUpperCase() + action.slice(1)}ing...`;
    }

    try {
      const response = await fetch(`/canteen/dashboard/${this.getCollegeSlug()}/${action}-order/${orderId}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': this.getCSRFToken()
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          this.showNotification(`Order ${action}ed successfully!`, 'success');
          // Smart update instead of reload
          await this.smartUpdate('/api/canteen/orders/');
        } else {
          this.showNotification(data.error || `Failed to ${action} order`, 'error');
        }
      }
    } catch (error) {
      console.error(`Error ${action}ing order:`, error);
      this.showNotification(`Error ${action}ing order`, 'error');
    } finally {
      if (button) {
        button.disabled = false;
        button.innerHTML = `<i class="fas fa-${this.getActionIcon(action)} mr-2"></i>${this.getActionText(action)}`;
      }
    }
  }

  getActionIcon(action) {
    const icons = {
      accept: 'check',
      decline: 'times',
      ready: 'check',
      complete: 'check-double'
    };
    return icons[action] || 'check';
  }

  getActionText(action) {
    const texts = {
      accept: 'Accept Order',
      decline: 'Decline',
      ready: 'Mark Ready',
      complete: 'Mark Completed'
    };
    return texts[action] || 'Action';
  }

  getCollegeSlug() {
    const urlParts = window.location.pathname.split('/');
    return urlParts[2] || 'default';
  }

  // 🖼️ IMAGE UPLOAD HANDLING
  async handleImageUpload(input) {
    const file = input.files[0];
    if (!file) return;

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      this.showNotification('Image size must be less than 5MB', 'error');
      input.value = '';
      return;
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      this.showNotification('Please select a valid image file', 'error');
      input.value = '';
      return;
    }

    // Show preview
    const preview = this.getCachedElement('#image-preview');
    if (preview) {
      const reader = new FileReader();
      reader.onload = (e) => {
        preview.src = e.target.result;
        preview.classList.remove('hidden');
      };
      reader.readAsDataURL(file);
    }
  }

  // 🛒 CART ITEM UPDATE
  async updateCartItem(input) {
    const itemId = input.dataset.itemId;
    const quantity = parseInt(input.value);
    
    if (quantity < 1) {
      input.value = 1;
      return;
    }

    try {
      const response = await fetch('/api/cart/update/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify({ item_id: itemId, quantity: quantity })
      });

      if (response.ok) {
        const data = await response.json();
        this.updateCartCount(data.cart_count);
        this.updateCartTotal(data.total);
      }
    } catch (error) {
      console.error('Cart update failed:', error);
      this.showNotification('Failed to update cart', 'error');
    }
  }

  updateCartTotal(total) {
    const totalElement = this.getCachedElement('#cart-total');
    if (totalElement) {
      totalElement.textContent = `₹${total.toFixed(2)}`;
    }
  }

  // ❤️ FAVORITE TOGGLE
  async toggleFavorite(button) {
    const itemId = button.dataset.itemId;
    const isFavorited = button.classList.contains('favorited');

    try {
      const response = await fetch('/api/favorites/toggle/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify({ item_id: itemId })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          button.classList.toggle('favorited', !isFavorited);
          this.showNotification(
            isFavorited ? 'Removed from favorites' : 'Added to favorites',
            'success'
          );
        }
      }
    } catch (error) {
      console.error('Favorite toggle failed:', error);
      this.showNotification('Failed to update favorites', 'error');
    }
  }

  // 📄 PAGE LOADING
  async loadPage(url) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        const html = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Update main content
        const mainContent = this.getCachedElement('main');
        const newContent = doc.querySelector('main');
        if (mainContent && newContent) {
          mainContent.innerHTML = newContent.innerHTML;
        }
        
        // Update URL without reload
        window.history.pushState({}, '', url);
      }
    } catch (error) {
      console.error('Page load failed:', error);
      this.showNotification('Failed to load page', 'error');
    }
  }

  // 📱 MOBILE MENU TOGGLE
  toggleMobileMenu() {
    const mobileMenu = this.getCachedElement('[data-mobile-menu]');
    if (mobileMenu) {
      mobileMenu.classList.toggle('hidden');
    }
  }

  // 🔍 HELP SEARCH
  async searchHelp(query) {
    try {
      const response = await fetch(`/api/help/search/?q=${encodeURIComponent(query)}`);
      if (response.ok) {
        const data = await response.json();
        this.updateHelpResults(data.results);
      }
    } catch (error) {
      console.error('Help search failed:', error);
    }
  }

  updateHelpResults(results) {
    const resultsContainer = this.getCachedElement('#help-results');
    if (resultsContainer) {
      resultsContainer.innerHTML = results.map(result => `
        <div class="help-item p-4 border-b">
          <h3 class="font-semibold">${result.title}</h3>
          <p class="text-gray-600">${result.excerpt}</p>
        </div>
      `).join('');
    }
  }

  // 📊 BULK ACTIONS UPDATE
  updateBulkActions() {
    const checkboxes = this.getCachedElements('input[type="checkbox"]:checked');
    const bulkActions = this.getCachedElement('#bulk-actions');
    
    if (bulkActions) {
      bulkActions.classList.toggle('hidden', checkboxes.length === 0);
    }
  }

  // 📋 FORM SUBMISSION HANDLING
  async handleFormSubmission(form) {
    const formData = new FormData(form);
    
    try {
      const response = await fetch(form.action, {
        method: form.method || 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': this.getCSRFToken()
        }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          this.showNotification(data.message || 'Success!', 'success');
          if (data.redirect) {
            window.location.href = data.redirect;
          }
        } else {
          this.showNotification(data.error || 'Form submission failed', 'error');
        }
      }
    } catch (error) {
      console.error('Form submission failed:', error);
      this.showNotification('Form submission failed', 'error');
    }
  }

  // 📊 SEARCH RESULTS UPDATE
  updateSearchResults(results) {
    const resultsContainer = this.getCachedElement('#search-results');
    if (resultsContainer) {
      resultsContainer.innerHTML = results.map(item => `
        <div class="search-item p-4 border-b">
          <h3 class="font-semibold">${item.name}</h3>
          <p class="text-gray-600">${item.description}</p>
          <span class="text-green-600 font-semibold">₹${item.price}</span>
        </div>
      `).join('');
    }
  }

  // 📋 ORDERS LIST UPDATE
  updateOrdersList(orders) {
    const ordersContainer = this.getCachedElement('#orders-container');
    if (ordersContainer) {
      ordersContainer.innerHTML = orders.map(order => `
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
      `).join('');
    }
  }

  // 🍽️ MENU ITEMS UPDATE
  updateMenuItems(items) {
    const menuContainer = this.getCachedElement('#menu-container');
    if (menuContainer) {
      menuContainer.innerHTML = items.map(item => `
        <div class="menu-item p-4 border rounded-lg mb-4" data-item-id="${item.id}">
          <div class="flex justify-between items-center">
            <div>
              <h3 class="font-semibold">${item.name}</h3>
              <p class="text-gray-600">${item.description}</p>
            </div>
            <div class="flex items-center space-x-2">
              <span class="text-green-600 font-semibold">₹${item.price}</span>
              <button class="favorite-btn ${item.is_favorite ? 'favorited' : ''} text-red-500" data-item-id="${item.id}">
                <i class="fas fa-heart"></i>
              </button>
            </div>
          </div>
        </div>
      `).join('');
    }
  }
}

// 🚀 INITIALIZE PERFORMANCE OPTIMIZER
const performanceOptimizer = new PerformanceOptimizer();

// 📊 EXPORT FOR GLOBAL ACCESS
window.PerformanceOptimizer = performanceOptimizer;
window.showNotification = (message, type) => performanceOptimizer.showNotification(message, type);
window.debounce = (func, delay) => performanceOptimizer.debounce(func, delay);
window.throttle = (func, delay) => performanceOptimizer.throttle(func, delay);

// 🎯 AUTO-INITIALIZE ON DOM READY
document.addEventListener('DOMContentLoaded', () => {
  // Additional initialization if needed
  console.log('🚀 SkipTheQueue Performance Optimizer initialized');
});
