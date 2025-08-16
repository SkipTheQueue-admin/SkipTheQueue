// Performance Monitoring System for SkipTheQueue
// Monitors and optimizes application performance

class PerformanceMonitor {
    constructor() {
        this.metrics = {
            pageLoadTime: 0,
            domContentLoaded: 0,
            firstContentfulPaint: 0,
            largestContentfulPaint: 0,
            cumulativeLayoutShift: 0,
            firstInputDelay: 0,
            totalBlockingTime: 0
        };
        
        this.observers = [];
        this.init();
    }
    
    init() {
        // Monitor page load performance
        this.monitorPageLoad();
        
        // Monitor Core Web Vitals
        this.monitorCoreWebVitals();
        
        // Monitor user interactions
        this.monitorUserInteractions();
        
        // Monitor resource loading
        this.monitorResourceLoading();
        
        // Monitor memory usage
        this.monitorMemoryUsage();
        
        // Set up performance budget alerts
        this.setupPerformanceBudget();
    }
    
    monitorPageLoad() {
        window.addEventListener('load', () => {
            const navigation = performance.getEntriesByType('navigation')[0];
            if (navigation) {
                this.metrics.pageLoadTime = navigation.loadEventEnd - navigation.loadEventStart;
                this.metrics.domContentLoaded = navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart;
                
                // Log performance metrics
                console.log('Page Load Performance:', {
                    pageLoadTime: `${this.metrics.pageLoadTime}ms`,
                    domContentLoaded: `${this.metrics.domContentLoaded}ms`
                });
                
                // Alert if performance is poor
                if (this.metrics.pageLoadTime > 3000) {
                    this.alertPoorPerformance('Page load time', this.metrics.pageLoadTime);
                }
            }
        });
    }
    
    monitorCoreWebVitals() {
        // First Contentful Paint
        if ('PerformanceObserver' in window) {
            try {
                const paintObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.name === 'first-contentful-paint') {
                            this.metrics.firstContentfulPaint = entry.startTime;
                            this.checkPerformanceBudget('FCP', entry.startTime, 1800);
                        }
                    }
                });
                paintObserver.observe({ entryTypes: ['paint'] });
                this.observers.push(paintObserver);
            } catch (e) {
                console.warn('FCP monitoring not supported:', e);
            }
            
            // Largest Contentful Paint
            try {
                const lcpObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        this.metrics.largestContentfulPaint = entry.startTime;
                        this.checkPerformanceBudget('LCP', entry.startTime, 2500);
                    }
                });
                lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
                this.observers.push(lcpObserver);
            } catch (e) {
                console.warn('LCP monitoring not supported:', e);
            }
            
            // Cumulative Layout Shift
            try {
                const clsObserver = new PerformanceObserver((list) => {
                    let clsValue = 0;
                    for (const entry of list.getEntries()) {
                        clsValue += entry.value;
                    }
                    this.metrics.cumulativeLayoutShift = clsValue;
                    this.checkPerformanceBudget('CLS', clsValue, 0.1);
                });
                clsObserver.observe({ entryTypes: ['layout-shift'] });
                this.observers.push(clsObserver);
            } catch (e) {
                console.warn('CLS monitoring not supported:', e);
            }
            
            // First Input Delay
            try {
                const fidObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        this.metrics.firstInputDelay = entry.processingStart - entry.startTime;
                        this.checkPerformanceBudget('FID', this.metrics.firstInputDelay, 100);
                    }
                });
                fidObserver.observe({ entryTypes: ['first-input'] });
                this.observers.push(fidObserver);
            } catch (e) {
                console.warn('FID monitoring not supported:', e);
            }
            
            // Total Blocking Time
            try {
                const tbtObserver = new PerformanceObserver((list) => {
                    let totalBlockingTime = 0;
                    for (const entry of list.getEntries()) {
                        if (entry.duration > 50) {
                            totalBlockingTime += entry.duration - 50;
                        }
                    }
                    this.metrics.totalBlockingTime = totalBlockingTime;
                    this.checkPerformanceBudget('TBT', totalBlockingTime, 300);
                });
                tbtObserver.observe({ entryTypes: ['longtask'] });
                this.observers.push(tbtObserver);
            } catch (e) {
                console.warn('TBT monitoring not supported:', e);
            }
        }
    }
    
    monitorUserInteractions() {
        // Monitor button clicks and form submissions
        document.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
                this.trackInteraction('button_click', e.target);
            }
        });
        
        document.addEventListener('submit', (e) => {
            this.trackInteraction('form_submit', e.target);
        });
        
        // Monitor navigation
        let navigationStart = performance.now();
        document.addEventListener('click', (e) => {
            if (e.target.tagName === 'A' || e.target.closest('a')) {
                navigationStart = performance.now();
            }
        });
        
        window.addEventListener('beforeunload', () => {
            const navigationTime = performance.now() - navigationStart;
            if (navigationTime > 100) {
                console.log('Navigation took:', `${navigationTime}ms`);
            }
        });
    }
    
    monitorResourceLoading() {
        if ('PerformanceObserver' in window) {
            try {
                const resourceObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        // Alert for slow resources
                        if (entry.duration > 2000) {
                            console.warn('Slow resource loaded:', {
                                name: entry.name,
                                duration: `${entry.duration}ms`,
                                size: entry.transferSize ? `${entry.transferSize} bytes` : 'unknown'
                            });
                        }
                        
                        // Track large resources
                        if (entry.transferSize && entry.transferSize > 500000) {
                            console.warn('Large resource loaded:', {
                                name: entry.name,
                                size: `${(entry.transferSize / 1024 / 1024).toFixed(2)} MB`
                            });
                        }
                    }
                });
                resourceObserver.observe({ entryTypes: ['resource'] });
                this.observers.push(resourceObserver);
            } catch (e) {
                console.warn('Resource monitoring not supported:', e);
            }
        }
    }
    
    monitorMemoryUsage() {
        if ('memory' in performance) {
            setInterval(() => {
                const memory = performance.memory;
                const usedMB = (memory.usedJSHeapSize / 1024 / 1024).toFixed(2);
                const totalMB = (memory.totalJSHeapSize / 1024 / 1024).toFixed(2);
                
                // Alert if memory usage is high
                if (memory.usedJSHeapSize > memory.totalJSHeapSize * 0.8) {
                    console.warn('High memory usage:', `${usedMB}MB / ${totalMB}MB`);
                }
            }, 10000); // Check every 10 seconds
        }
    }
    
    setupPerformanceBudget() {
        this.performanceBudget = {
            FCP: 1800,    // First Contentful Paint: 1.8s
            LCP: 2500,    // Largest Contentful Paint: 2.5s
            FID: 100,     // First Input Delay: 100ms
            CLS: 0.1,     // Cumulative Layout Shift: 0.1
            TBT: 300      // Total Blocking Time: 300ms
        };
    }
    
    checkPerformanceBudget(metric, value, threshold) {
        if (value > threshold) {
            this.alertPoorPerformance(metric, value, threshold);
        }
    }
    
    alertPoorPerformance(metric, value, threshold = null) {
        const message = threshold 
            ? `${metric}: ${value} (threshold: ${threshold})`
            : `${metric}: ${value}`;
        
        console.warn('Performance Issue:', message);
        
        // Show user notification for critical issues
        if (window.showNotification) {
            window.showNotification(
                `Performance issue detected: ${metric}`,
                'warning',
                5000
            );
        }
        
        // Send to analytics if available
        if (window.gtag) {
            window.gtag('event', 'performance_issue', {
                event_category: 'performance',
                event_label: metric,
                value: Math.round(value)
            });
        }
    }
    
    trackInteraction(type, element) {
        const startTime = performance.now();
        
        // Create a performance mark
        const markName = `${type}_${Date.now()}`;
        performance.mark(markName);
        
        // Measure time to next frame
        requestAnimationFrame(() => {
            const endTime = performance.now();
            const duration = endTime - startTime;
            
            // Alert for slow interactions
            if (duration > 100) {
                console.warn('Slow interaction:', {
                    type,
                    element: element.tagName || element.className,
                    duration: `${duration}ms`
                });
            }
            
            // Clear the mark
            performance.clearMarks(markName);
        });
    }
    
    getMetrics() {
        return { ...this.metrics };
    }
    
    generateReport() {
        const report = {
            timestamp: new Date().toISOString(),
            metrics: this.getMetrics(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            performanceScore: this.calculatePerformanceScore()
        };
        
        console.log('Performance Report:', report);
        return report;
    }
    
    calculatePerformanceScore() {
        let score = 100;
        
        // Deduct points for poor performance
        if (this.metrics.firstContentfulPaint > 1800) score -= 20;
        if (this.metrics.largestContentfulPaint > 2500) score -= 20;
        if (this.metrics.firstInputDelay > 100) score -= 20;
        if (this.metrics.cumulativeLayoutShift > 0.1) score -= 20;
        if (this.metrics.totalBlockingTime > 300) score -= 20;
        
        return Math.max(0, score);
    }
    
    optimizePerformance() {
        // Optimize images
        this.optimizeImages();
        
        // Optimize fonts
        this.optimizeFonts();
        
        // Optimize CSS
        this.optimizeCSS();
        
        // Optimize JavaScript
        this.optimizeJavaScript();
    }
    
    optimizeImages() {
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            // Add loading="lazy" for images below the fold
            if (!img.loading) {
                img.loading = 'lazy';
            }
            
            // Add decoding="async" for better performance
            if (!img.decoding) {
                img.decoding = 'async';
            }
        });
    }
    
    optimizeFonts() {
        // Preload critical fonts
        const criticalFonts = document.querySelectorAll('link[rel="preload"][as="font"]');
        criticalFonts.forEach(font => {
            font.setAttribute('crossorigin', 'anonymous');
        });
    }
    
    optimizeCSS() {
        // Remove unused CSS rules
        const styleSheets = Array.from(document.styleSheets);
        styleSheets.forEach(sheet => {
            try {
                const rules = sheet.cssRules || sheet.rules;
                if (rules) {
                    // This is a simplified optimization - in practice, you'd want more sophisticated analysis
                    console.log(`Stylesheet ${sheet.href} has ${rules.length} rules`);
                }
            } catch (e) {
                // Cross-origin stylesheets will throw an error
            }
        });
    }
    
    optimizeJavaScript() {
        // Debounce scroll and resize events
        let scrollTimeout, resizeTimeout;
        
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                // Handle scroll events here
            }, 16); // ~60fps
        });
        
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                // Handle resize events here
            }, 100);
        });
    }
    
    destroy() {
        // Disconnect all observers
        this.observers.forEach(observer => {
            if (observer.disconnect) {
                observer.disconnect();
            }
        });
        this.observers = [];
    }
}

// Initialize performance monitor
window.performanceMonitor = new PerformanceMonitor();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PerformanceMonitor;
}
