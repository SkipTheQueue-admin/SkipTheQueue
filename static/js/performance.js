/**
 * Performance Optimization Utilities for SkipTheQueue
 * This file contains utilities to improve performance and user experience
 */

// Performance monitoring
class PerformanceMonitor {
    constructor() {
        this.metrics = {
            pageLoadTime: 0,
            domContentLoaded: 0,
            firstContentfulPaint: 0,
            largestContentfulPaint: 0,
            cumulativeLayoutShift: 0
        };
        this.init();
    }

    init() {
        this.measurePageLoad();
        this.measureCoreWebVitals();
        this.setupPerformanceObserver();
    }

    measurePageLoad() {
        window.addEventListener('load', () => {
            this.metrics.pageLoadTime = performance.now();
            this.logMetric('Page Load Time', this.metrics.pageLoadTime);
        });

        document.addEventListener('DOMContentLoaded', () => {
            this.metrics.domContentLoaded = performance.now();
            this.logMetric('DOM Content Loaded', this.metrics.domContentLoaded);
        });
    }

    measureCoreWebVitals() {
        // First Contentful Paint
        if ('PerformanceObserver' in window) {
            try {
                const paintObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.name === 'first-contentful-paint') {
                            this.metrics.firstContentfulPaint = entry.startTime;
                            this.logMetric('First Contentful Paint', entry.startTime);
                        }
                    }
                });
                paintObserver.observe({ entryTypes: ['paint'] });
            } catch (e) {
                console.warn('PerformanceObserver not supported');
            }
        }

        // Largest Contentful Paint
        if ('PerformanceObserver' in window) {
            try {
                const lcpObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    this.metrics.largestContentfulPaint = lastEntry.startTime;
                    this.logMetric('Largest Contentful Paint', lastEntry.startTime);
                });
                lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
            } catch (e) {
                console.warn('LCP observer not supported');
            }
        }
    }

    setupPerformanceObserver() {
        // Monitor long tasks
        if ('PerformanceObserver' in window) {
            try {
                const longTaskObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.duration > 50) { // 50ms threshold
                            console.warn('Long task detected:', entry.duration + 'ms');
                        }
                    }
                });
                longTaskObserver.observe({ entryTypes: ['longtask'] });
            } catch (e) {
                console.warn('Long task observer not supported');
            }
        }
    }

    logMetric(name, value) {
        console.log(`Performance Metric - ${name}: ${value.toFixed(2)}ms`);
        
        // Send to analytics if available
        if (window.gtag) {
            window.gtag('event', 'performance_metric', {
                metric_name: name,
                metric_value: value
            });
        }
    }

    getMetrics() {
        return this.metrics;
    }
}

// Image optimization
class ImageOptimizer {
    constructor() {
        this.init();
    }

    init() {
        this.setupLazyLoading();
        this.optimizeImages();
    }

    setupLazyLoading() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        this.loadImage(img);
                        observer.unobserve(img);
                    }
                });
            }, {
                rootMargin: '50px 0px',
                threshold: 0.01
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    loadImage(img) {
        const src = img.dataset.src;
        if (src) {
            img.src = src;
            img.classList.remove('lazy');
            img.classList.add('loaded');
        }
    }

    optimizeImages() {
        // Add loading="lazy" to images without it
        document.querySelectorAll('img:not([loading])').forEach(img => {
            if (!img.classList.contains('critical')) {
                img.loading = 'lazy';
            }
        });

        // Optimize image sizes for different viewports
        this.setupResponsiveImages();
    }

    setupResponsiveImages() {
        const images = document.querySelectorAll('img[data-srcset]');
        images.forEach(img => {
            if (img.dataset.srcset) {
                img.srcset = img.dataset.srcset;
                img.sizes = img.dataset.sizes || '100vw';
            }
        });
    }
}

// Resource optimization
class ResourceOptimizer {
    constructor() {
        this.init();
    }

    init() {
        this.preloadCriticalResources();
        this.deferNonCriticalScripts();
    }

    preloadCriticalResources() {
        // Preload critical CSS and fonts
        const criticalResources = [
            '/static/css/tailwind-fallback.css',
            '/static/js/notifications.js'
        ];

        criticalResources.forEach(resource => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.href = resource;
            link.as = resource.endsWith('.css') ? 'style' : 'script';
            document.head.appendChild(link);
        });
    }

    deferNonCriticalScripts() {
        // Defer non-critical scripts
        const scripts = document.querySelectorAll('script[data-defer]');
        scripts.forEach(script => {
            script.defer = true;
        });
    }
}

// Cache management
class CacheManager {
    constructor() {
        this.cache = new Map();
        this.maxSize = 100;
    }

    set(key, value, ttl = 300000) { // 5 minutes default
        if (this.cache.size >= this.maxSize) {
            // Remove oldest entry
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }

        this.cache.set(key, {
            value,
            timestamp: Date.now(),
            ttl
        });
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) return null;

        if (Date.now() - item.timestamp > item.ttl) {
            this.cache.delete(key);
            return null;
        }

        return item.value;
    }

    clear() {
        this.cache.clear();
    }

    size() {
        return this.cache.size;
    }
}

// Network optimization
class NetworkOptimizer {
    constructor() {
        this.retryAttempts = 3;
        this.retryDelay = 1000;
    }

    async fetchWithRetry(url, options = {}, retryCount = 0) {
        try {
            const response = await fetch(url, options);
            
            if (!response.ok && retryCount < this.retryAttempts) {
                await this.delay(this.retryDelay * Math.pow(2, retryCount));
                return this.fetchWithRetry(url, options, retryCount + 1);
            }
            
            return response;
        } catch (error) {
            if (retryCount < this.retryAttempts) {
                await this.delay(this.retryDelay * Math.pow(2, retryCount));
                return this.fetchWithRetry(url, options, retryCount + 1);
            }
            throw error;
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Batch API requests for better performance
    async batchRequests(requests) {
        const promises = requests.map(req => this.fetchWithRetry(req.url, req.options));
        return Promise.all(promises);
    }
}

// Initialize performance optimizations
document.addEventListener('DOMContentLoaded', () => {
    // Initialize performance monitoring
    window.performanceMonitor = new PerformanceMonitor();
    
    // Initialize image optimization
    window.imageOptimizer = new ImageOptimizer();
    
    // Initialize resource optimization
    window.resourceOptimizer = new ResourceOptimizer();
    
    // Initialize cache management
    window.cacheManager = new CacheManager();
    
    // Initialize network optimization
    window.networkOptimizer = new NetworkOptimizer();
    
    console.log('Performance optimizations initialized');
});

// Export for use in other modules
window.PerformanceOptimizer = {
    PerformanceMonitor,
    ImageOptimizer,
    ResourceOptimizer,
    CacheManager,
    NetworkOptimizer
};
