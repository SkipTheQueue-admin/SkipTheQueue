/**
 * Performance-optimized JavaScript for SkipTheQueue
 * Focuses on improving loading speed, reducing blocking, and enhancing user experience
 */

(function() {
    'use strict';

    // Performance monitoring
    const performanceMetrics = {
        startTime: performance.now(),
        loadTime: 0,
        domReady: false,
        resourcesLoaded: 0,
        totalResources: 0
    };

    // Optimize image loading
    function optimizeImages() {
        const images = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    observer.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    }

    // Optimize CSS loading
    function optimizeCSS() {
        const criticalCSS = `
            /* Critical CSS for above-the-fold content */
            body { font-family: 'Inter', 'Arial', sans-serif; line-height: 1.6; }
            .container { max-width: 1200px; margin: 0 auto; padding: 0 1rem; }
            .btn { display: inline-block; padding: 0.5rem 1rem; border-radius: 0.375rem; text-decoration: none; }
            .btn-primary { background-color: #3B82F6; color: white; }
            .loading { opacity: 0.6; pointer-events: none; }
        `;

        const style = document.createElement('style');
        style.textContent = criticalCSS;
        document.head.appendChild(style);
    }

    // Optimize JavaScript loading
    function optimizeJS() {
        // Defer non-critical JavaScript
        const scripts = document.querySelectorAll('script[data-defer]');
        scripts.forEach(script => {
            script.defer = true;
        });
    }

    // Optimize font loading
    function optimizeFonts() {
        // Preload critical fonts
        const fontLink = document.createElement('link');
        fontLink.rel = 'preload';
        fontLink.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap';
        fontLink.as = 'style';
        document.head.appendChild(fontLink);
    }

    // Optimize resource loading
    function optimizeResources() {
        // Add resource hints
        const resourceHints = [
            { rel: 'dns-prefetch', href: '//cdnjs.cloudflare.com' },
            { rel: 'dns-prefetch', href: '//unpkg.com' },
            { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
            { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: true }
        ];

        resourceHints.forEach(hint => {
            const link = document.createElement('link');
            Object.assign(link, hint);
            document.head.appendChild(link);
        });
    }

    // Optimize animations
    function optimizeAnimations() {
        // Use requestAnimationFrame for smooth animations
        const animatedElements = document.querySelectorAll('.animate-fade-in-up, .animate-slide-in-right');
        
        animatedElements.forEach(element => {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                        observer.unobserve(entry.target);
                    }
                });
            });

            observer.observe(element);
        });
    }

    // Optimize form submissions
    function optimizeForms() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Processing...';
                }
            });
        });
    }

    // Optimize navigation
    function optimizeNavigation() {
        // Prefetch pages on hover
        const navLinks = document.querySelectorAll('a[href^="/"]');
        navLinks.forEach(link => {
            link.addEventListener('mouseenter', function() {
                const prefetchLink = document.createElement('link');
                prefetchLink.rel = 'prefetch';
                prefetchLink.href = this.href;
                document.head.appendChild(prefetchLink);
            });
        });
    }

    // Optimize caching
    function optimizeCaching() {
        // Cache frequently accessed elements
        const cache = new Map();
        
        function getCachedElement(selector) {
            if (!cache.has(selector)) {
                cache.set(selector, document.querySelector(selector));
            }
            return cache.get(selector);
        }

        // Expose cache to global scope for other scripts
        window.elementCache = getCachedElement;
    }

    // Optimize error handling
    function optimizeErrorHandling() {
        window.addEventListener('error', function(e) {
            console.warn('Performance: Error detected', e.error);
            // Send error to analytics if needed
        });

        window.addEventListener('unhandledrejection', function(e) {
            console.warn('Performance: Unhandled promise rejection', e.reason);
        });
    }

    // Optimize memory usage
    function optimizeMemory() {
        // Clean up event listeners when elements are removed
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.removedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Clean up any references to removed elements
                        node.removeEventListener && node.removeEventListener();
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Performance monitoring
    function monitorPerformance() {
        // Monitor Core Web Vitals
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                list.getEntries().forEach((entry) => {
                    if (entry.entryType === 'largest-contentful-paint') {
                        console.log('LCP:', entry.startTime);
                    }
                    if (entry.entryType === 'first-input') {
                        console.log('FID:', entry.processingStart - entry.startTime);
                    }
                });
            });

            observer.observe({ entryTypes: ['largest-contentful-paint', 'first-input'] });
        }

        // Monitor resource loading
        window.addEventListener('load', function() {
            performanceMetrics.loadTime = performance.now() - performanceMetrics.startTime;
            console.log('Page load time:', performanceMetrics.loadTime);
        });
    }

    // Initialize optimizations
    function init() {
        // Run critical optimizations immediately
        optimizeCSS();
        optimizeFonts();
        optimizeResources();
        optimizeErrorHandling();

        // Run optimizations after DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', runOptimizations);
        } else {
            runOptimizations();
        }

        // Run optimizations after page load
        window.addEventListener('load', runPostLoadOptimizations);
    }

    function runOptimizations() {
        performanceMetrics.domReady = true;
        optimizeImages();
        optimizeJS();
        optimizeAnimations();
        optimizeForms();
        optimizeNavigation();
        optimizeCaching();
        optimizeMemory();
        monitorPerformance();
    }

    function runPostLoadOptimizations() {
        // Defer non-critical operations
        setTimeout(() => {
            // Preload next likely pages
            const likelyPages = ['/menu/', '/cart/', '/favorites/'];
            likelyPages.forEach(page => {
                const link = document.createElement('link');
                link.rel = 'prefetch';
                link.href = page;
                document.head.appendChild(link);
            });
        }, 1000);
    }

    // Start optimizations
    init();

    // Export for use in other scripts
    window.PerformanceOptimizer = {
        metrics: performanceMetrics,
        optimizeImages,
        optimizeAnimations,
        optimizeForms
    };

})();
