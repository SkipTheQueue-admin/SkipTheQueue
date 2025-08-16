// Performance monitoring and optimization script for SkipTheQueue

class PerformanceMonitor {
  constructor() {
    this.metrics = {};
    this.observers = [];
    this.thresholds = {
      fcp: 1800, // First Contentful Paint (ms)
      lcp: 2500, // Largest Contentful Paint (ms)
      fid: 100,  // First Input Delay (ms)
      cls: 0.1,  // Cumulative Layout Shift
      ttfb: 800  // Time to First Byte (ms)
    };
    this.init();
  }

  init() {
    this.setupPerformanceObservers();
    this.setupResourceTiming();
    this.setupUserTiming();
    this.setupErrorTracking();
    this.setupMemoryMonitoring();
    this.setupNetworkMonitoring();
    this.createPerformanceUI();
  }

  setupPerformanceObservers() {
    // First Contentful Paint
    if ('PerformanceObserver' in window) {
      try {
        const fcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            this.metrics.fcp = entry.startTime;
            this.checkThreshold('fcp', entry.startTime);
          });
        });
        fcpObserver.observe({ entryTypes: ['paint'] });

        // Largest Contentful Paint
        const lcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            this.metrics.lcp = entry.startTime;
            this.checkThreshold('lcp', entry.startTime);
          });
        });
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

        // First Input Delay
        const fidObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            this.metrics.fid = entry.processingStart - entry.startTime;
            this.checkThreshold('fid', this.metrics.fid);
          });
        });
        fidObserver.observe({ entryTypes: ['first-input'] });

        // Cumulative Layout Shift
        const clsObserver = new PerformanceObserver((list) => {
          let clsValue = 0;
          const entries = list.getEntries();
          entries.forEach((entry) => {
            if (!entry.hadRecentInput) {
              clsValue += entry.value;
            }
          });
          this.metrics.cls = clsValue;
          this.checkThreshold('cls', clsValue);
        });
        clsObserver.observe({ entryTypes: ['layout-shift'] });

        this.observers.push(fcpObserver, lcpObserver, fidObserver, clsObserver);
      } catch (error) {
        console.warn('PerformanceObserver setup failed:', error);
      }
    }
  }

  setupResourceTiming() {
    // Monitor resource loading performance
    if ('PerformanceObserver' in window) {
      try {
        const resourceObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            if (entry.initiatorType === 'img' || entry.initiatorType === 'css' || entry.initiatorType === 'script') {
              this.analyzeResource(entry);
            }
          });
        });
        resourceObserver.observe({ entryTypes: ['resource'] });
        this.observers.push(resourceObserver);
      } catch (error) {
        console.warn('Resource timing observer setup failed:', error);
      }
    }
  }

  setupUserTiming() {
    // Monitor custom performance marks
    if ('PerformanceObserver' in window) {
      try {
        const userTimingObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            this.metrics[entry.name] = entry.startTime;
          });
        });
        userTimingObserver.observe({ entryTypes: ['measure'] });
        this.observers.push(userTimingObserver);
      } catch (error) {
        console.warn('User timing observer setup failed:', error);
      }
    }
  }

  setupErrorTracking() {
    // Monitor JavaScript errors
    window.addEventListener('error', (event) => {
      this.metrics.errors = (this.metrics.errors || 0) + 1;
      this.logError('JavaScript Error', event.error);
    });

    // Monitor unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.metrics.promiseRejections = (this.metrics.promiseRejections || 0) + 1;
      this.logError('Unhandled Promise Rejection', event.reason);
    });
  }

  setupMemoryMonitoring() {
    // Monitor memory usage (if available)
    if ('memory' in performance) {
      setInterval(() => {
        const memory = performance.memory;
        this.metrics.memory = {
          used: memory.usedJSHeapSize,
          total: memory.totalJSHeapSize,
          limit: memory.jsHeapSizeLimit
        };
        
        // Alert if memory usage is high
        const memoryUsage = memory.usedJSHeapSize / memory.jsHeapSizeLimit;
        if (memoryUsage > 0.8) {
          this.showWarning('High memory usage detected');
        }
      }, 10000);
    }
  }

  setupNetworkMonitoring() {
    // Monitor network conditions
    if ('connection' in navigator) {
      const connection = navigator.connection;
      this.metrics.network = {
        effectiveType: connection.effectiveType,
        downlink: connection.downlink,
        rtt: connection.rtt
      };

      connection.addEventListener('change', () => {
        this.metrics.network = {
          effectiveType: connection.effectiveType,
          downlink: connection.downlink,
          rtt: connection.rtt
        };
        this.updateNetworkUI();
      });
    }
  }

  analyzeResource(entry) {
    const resourceMetrics = {
      name: entry.name,
      type: entry.initiatorType,
      duration: entry.duration,
      size: entry.transferSize,
      startTime: entry.startTime
    };

    // Check for slow resources
    if (entry.duration > 1000) {
      this.showWarning(`Slow resource: ${entry.name} (${Math.round(entry.duration)}ms)`);
    }

    // Store resource metrics
    if (!this.metrics.resources) {
      this.metrics.resources = [];
    }
    this.metrics.resources.push(resourceMetrics);
  }

  checkThreshold(metric, value) {
    const threshold = this.thresholds[metric];
    if (threshold && value > threshold) {
      this.showWarning(`${metric.toUpperCase()} threshold exceeded: ${Math.round(value)}ms`);
    }
  }

  logError(type, error) {
    console.error(`Performance Monitor - ${type}:`, error);
    
    // Send to analytics if available
    if (typeof gtag !== 'undefined') {
      gtag('event', 'exception', {
        description: `${type}: ${error.message || error}`,
        fatal: false
      });
    }
  }

  showWarning(message) {
    console.warn(`Performance Warning: ${message}`);
    
    // Show in UI
    const warningElement = document.getElementById('performance-warning');
    if (warningElement) {
      warningElement.textContent = message;
      warningElement.classList.add('show');
      setTimeout(() => {
        warningElement.classList.remove('show');
      }, 5000);
    }
  }

  createPerformanceUI() {
    // Create performance monitoring UI
    const monitorDiv = document.createElement('div');
    monitorDiv.id = 'performance-monitor';
    monitorDiv.className = 'performance-monitor';
    monitorDiv.innerHTML = `
      <div class="performance-header">
        <strong>Performance Monitor</strong>
        <button onclick="this.parentElement.parentElement.classList.toggle('expanded')" class="toggle-btn">+</button>
      </div>
      <div class="performance-metrics">
        <div class="metric">
          <span class="label">FCP:</span>
          <span class="value" id="fcp-value">-</span>
        </div>
        <div class="metric">
          <span class="label">LCP:</span>
          <span class="value" id="lcp-value">-</span>
        </div>
        <div class="metric">
          <span class="label">FID:</span>
          <span class="value" id="fid-value">-</span>
        </div>
        <div class="metric">
          <span class="label">CLS:</span>
          <span class="value" id="cls-value">-</span>
        </div>
      </div>
      <div class="performance-warnings" id="performance-warning"></div>
    `;

    document.body.appendChild(monitorDiv);

    // Update metrics display
    this.updateMetricsDisplay();
  }

  updateMetricsDisplay() {
    setInterval(() => {
      if (this.metrics.fcp) {
        document.getElementById('fcp-value').textContent = `${Math.round(this.metrics.fcp)}ms`;
      }
      if (this.metrics.lcp) {
        document.getElementById('lcp-value').textContent = `${Math.round(this.metrics.lcp)}ms`;
      }
      if (this.metrics.fid) {
        document.getElementById('fid-value').textContent = `${Math.round(this.metrics.fid)}ms`;
      }
      if (this.metrics.cls) {
        document.getElementById('cls-value').textContent = this.metrics.cls.toFixed(3);
      }
    }, 1000);
  }

  updateNetworkUI() {
    if (this.metrics.network) {
      const networkInfo = document.getElementById('network-info');
      if (networkInfo) {
        networkInfo.textContent = `${this.metrics.network.effectiveType} (${this.metrics.network.downlink}Mbps)`;
      }
    }
  }

  getMetrics() {
    return this.metrics;
  }

  mark(name) {
    if ('performance' in window) {
      performance.mark(name);
    }
  }

  measure(name, startMark, endMark) {
    if ('performance' in window) {
      try {
        performance.measure(name, startMark, endMark);
      } catch (error) {
        console.warn('Performance measure failed:', error);
      }
    }
  }

  disconnect() {
    this.observers.forEach(observer => {
      observer.disconnect();
    });
  }
}

// Initialize performance monitor
const performanceMonitor = new PerformanceMonitor();

// Performance optimization utilities
class PerformanceOptimizer {
  static optimizeImages() {
    const images = document.querySelectorAll('img');
    images.forEach(img => {
      // Lazy loading
      if (!img.loading) {
        img.loading = 'lazy';
      }
      
      // Add loading skeleton
      if (!img.complete) {
        img.classList.add('loading-skeleton');
        img.addEventListener('load', () => {
          img.classList.remove('loading-skeleton');
        });
      }
    });
  }

  static optimizeScroll() {
    // Throttle scroll events
    let ticking = false;
    const scrollHandler = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          // Handle scroll logic here
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', scrollHandler, { passive: true });
  }

  static optimizeResize() {
    // Debounce resize events
    let resizeTimeout;
    const resizeHandler = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        // Handle resize logic here
      }, 250);
    };

    window.addEventListener('resize', resizeHandler, { passive: true });
  }

  static preloadCriticalResources() {
    // Preload critical CSS and JS
    const criticalResources = [
      '/static/css/performance-optimized.css',
      '/static/js/canteen-dashboard.js'
    ];

    criticalResources.forEach(resource => {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.href = resource;
      link.as = resource.endsWith('.css') ? 'style' : 'script';
      document.head.appendChild(link);
    });
  }

  static optimizeAnimations() {
    // Use Intersection Observer for scroll-triggered animations
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('animate-fade-in-up');
          }
        });
      }, { threshold: 0.1 });

      // Observe elements that should animate on scroll
      document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
      });
    }
  }
}

// Initialize optimizations when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  PerformanceOptimizer.optimizeImages();
  PerformanceOptimizer.optimizeScroll();
  PerformanceOptimizer.optimizeResize();
  PerformanceOptimizer.optimizeAnimations();
});

// Preload critical resources
PerformanceOptimizer.preloadCriticalResources();

// Export for global use
window.PerformanceMonitor = PerformanceMonitor;
window.PerformanceOptimizer = PerformanceOptimizer;
window.performanceMonitor = performanceMonitor;
