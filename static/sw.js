// SkipTheQueue Service Worker
// Version: 1.0.0

const CACHE_NAME = 'skipthequeue-v1';
const STATIC_CACHE = 'skipqueue-static-v1.0.0';
const DYNAMIC_CACHE = 'skipqueue-dynamic-v1.0.0';

// Files to cache immediately
const STATIC_FILES = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/images/zap-icon.svg',
  'https://cdn.tailwindcss.com',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
  '/manifest.json'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing...');
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(STATIC_FILES);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating...');
  self.clients.claim();
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  
  if (request.method !== 'GET') {
    return;
  }

  event.respondWith(
    caches.match(request)
      .then(response => {
        // Return cached version or fetch from network
        return response || fetch(request);
      })
  );
});

// Push notifications
self.addEventListener('push', (event) => {
  const options = {
    body: event.data ? event.data.text() : 'New order received!',
    icon: '/static/images/zap-icon.svg',
          badge: '/static/images/zap-icon.svg',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View Order',
        icon: '/static/images/zap-icon.svg'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/images/zap-icon.svg'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('SkipTheQueue', options)
  );
});

// Notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/canteen-dashboard/')
    );
  }
});

// Background sync for offline orders
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    console.log('Service Worker: Background sync triggered');
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  try {
    // Sync offline orders when connection is restored
    const offlineOrders = await getOfflineOrders();
    for (const order of offlineOrders) {
      await syncOrder(order);
    }
  } catch (error) {
    console.error('Background sync error:', error);
  }
}

// Utility functions
async function getOfflineOrders() {
  // Get orders stored in IndexedDB or localStorage
  // This would be implemented based on your storage strategy
  return [];
}

async function syncOrder(order) {
  // Sync order with server
  // This would be implemented based on your API
  console.log('Syncing order:', order);
}

// Message handling
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Error handling
self.addEventListener('error', (event) => {
  console.error('Service Worker error:', event.error);
});

self.addEventListener('unhandledrejection', (event) => {
  console.error('Service Worker unhandled rejection:', event.reason);
}); 