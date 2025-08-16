"""
Performance optimization middleware for SkipTheQueue
"""

import gzip
import json
import time
from django.http import HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class PerformanceMiddleware(MiddlewareMixin):
    """
    Middleware for performance optimization including:
    - Response compression
    - Cache headers
    - Performance monitoring
    - Database query optimization
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
        self.start_time = None
        
    def process_request(self, request):
        """Process incoming request for performance optimization"""
        # Start timing
        self.start_time = time.time()
        
        # Add performance headers
        request.META['HTTP_X_REQUEST_START'] = str(int(self.start_time * 1000))
        
        # Check if response should be cached
        if self.should_cache_request(request):
            cache_key = self.generate_cache_key(request)
            cached_response = cache.get(cache_key)
            if cached_response:
                logger.info(f"Cache hit for {request.path}")
                return cached_response
        
        return None
    
    def process_response(self, request, response):
        """Process outgoing response for performance optimization"""
        if self.start_time:
            # Calculate response time
            response_time = time.time() - self.start_time
            response['X-Response-Time'] = f"{response_time:.3f}s"
            
            # Log slow responses
            if response_time > 1.0:
                logger.warning(f"Slow response: {request.path} took {response_time:.3f}s")
        
        # Add performance headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Add cache headers for static content
        if self.is_cacheable_response(request, response):
            response['Cache-Control'] = 'public, max-age=3600'
            response['ETag'] = self.generate_etag(response)
        
        # Compress response if possible
        if self.should_compress_response(request, response):
            response = self.compress_response(response)
        
        # Cache successful responses
        if self.should_cache_request(request) and response.status_code == 200:
            cache_key = self.generate_cache_key(request)
            cache.set(cache_key, response, 300)  # Cache for 5 minutes
        
        return response
    
    def should_cache_request(self, request):
        """Determine if request should be cached"""
        # Don't cache POST requests
        if request.method != 'GET':
            return False
        
        # Don't cache authenticated requests
        if request.user.is_authenticated:
            return False
        
        # Don't cache admin requests
        if request.path.startswith('/admin/'):
            return False
        
        # Cache menu and static content
        cacheable_paths = [
            '/menu/',
            '/static/',
            '/media/',
            '/api/menu/',
        ]
        
        return any(request.path.startswith(path) for path in cacheable_paths)
    
    def should_compress_response(self, request, response):
        """Determine if response should be compressed"""
        # Check if client accepts gzip
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if 'gzip' not in accept_encoding:
            return False
        
        # Check content type
        content_type = response.get('Content-Type', '')
        compressible_types = [
            'text/html',
            'text/css',
            'text/javascript',
            'application/javascript',
            'application/json',
            'text/plain',
        ]
        
        return any(ct in content_type for ct in compressible_types)
    
    def compress_response(self, response):
        """Compress response content using gzip"""
        try:
            content = response.content
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            compressed_content = gzip.compress(content)
            
            # Create new response with compressed content
            compressed_response = HttpResponse(compressed_content)
            
            # Copy headers
            for key, value in response.items():
                compressed_response[key] = value
            
            # Add compression headers
            compressed_response['Content-Encoding'] = 'gzip'
            compressed_response['Content-Length'] = len(compressed_content)
            compressed_response['Vary'] = 'Accept-Encoding'
            
            return compressed_response
            
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return response
    
    def generate_cache_key(self, request):
        """Generate cache key for request"""
        # Include path and query parameters
        key_parts = [request.path]
        
        # Include query parameters
        if request.GET:
            sorted_params = sorted(request.GET.items())
            key_parts.append('&'.join(f"{k}={v}" for k, v in sorted_params))
        
        # Include user agent for different device types
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if 'Mobile' in user_agent:
            key_parts.append('mobile')
        elif 'Tablet' in user_agent:
            key_parts.append('tablet')
        else:
            key_parts.append('desktop')
        
        return f"perf_cache:{':'.join(key_parts)}"
    
    def generate_etag(self, response):
        """Generate ETag for response"""
        import hashlib
        
        # Create hash from content and headers
        content = response.content
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        # Include important headers in hash
        headers = [
            response.get('Content-Type', ''),
            response.get('Last-Modified', ''),
        ]
        
        hash_input = content + b''.join(h.encode('utf-8') for h in headers)
        return hashlib.md5(hash_input).hexdigest()
    
    def is_cacheable_response(self, request, response):
        """Determine if response can be cached"""
        # Don't cache error responses
        if response.status_code >= 400:
            return False
        
        # Don't cache responses with no-cache headers
        if 'no-cache' in response.get('Cache-Control', ''):
            return False
        
        # Cache successful responses
        return response.status_code == 200


class DatabaseOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware for database query optimization
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.get_response = get_response
        self.query_count = 0
        self.query_time = 0
    
    def process_request(self, request):
        """Reset query counters for each request"""
        self.query_count = 0
        self.query_time = 0
        
        # Enable query logging in debug mode
        if settings.DEBUG:
            from django.db import connection
            connection.queries_log = True
            connection.queries = []
        
        return None
    
    def process_response(self, request, response):
        """Log database performance metrics"""
        if settings.DEBUG:
            from django.db import connection
            
            # Count queries
            self.query_count = len(connection.queries)
            
            # Calculate total query time
            self.query_time = sum(
                float(query.get('time', 0)) for query in connection.queries
            )
            
            # Log performance metrics
            if self.query_count > 0:
                logger.info(
                    f"Database: {self.query_count} queries in {self.query_time:.3f}s "
                    f"for {request.path}"
                )
                
                # Warn about slow queries
                if self.query_time > 0.5:
                    logger.warning(
                        f"Slow database queries: {self.query_time:.3f}s "
                        f"for {request.path}"
                    )
                
                # Add performance headers
                response['X-Database-Queries'] = str(self.query_count)
                response['X-Database-Time'] = f"{self.query_time:.3f}s"
        
        return response


class StaticFileOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware for static file optimization
    """
    
    def process_response(self, request, response):
        """Add optimization headers for static files"""
        if self.is_static_file(request.path):
            # Add long-term caching for static files
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            
            # Add security headers
            response['X-Content-Type-Options'] = 'nosniff'
            
            # Add compression headers
            if response.get('Content-Encoding') == 'gzip':
                response['Vary'] = 'Accept-Encoding'
        
        return response
    
    def is_static_file(self, path):
        """Check if path is a static file"""
        static_extensions = {
            '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg',
            '.woff', '.woff2', '.ttf', '.eot', '.ico'
        }
        
        return any(path.endswith(ext) for ext in static_extensions)


class APIOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware for API response optimization
    """
    
    def process_response(self, request, response):
        """Optimize API responses"""
        if self.is_api_request(request.path):
            # Add API-specific headers
            response['X-API-Version'] = '1.0'
            response['X-API-Cache'] = 'enabled'
            
            # Add CORS headers for API requests
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            
            # Optimize JSON responses
            if isinstance(response, JsonResponse):
                # Ensure JSON is properly formatted
                try:
                    data = response.content.decode('utf-8')
                    json.loads(data)  # Validate JSON
                except (json.JSONDecodeError, UnicodeDecodeError):
                    logger.warning(f"Invalid JSON response for {request.path}")
        
        return response
    
    def is_api_request(self, path):
        """Check if path is an API request"""
        return path.startswith('/api/') or path.startswith('/canteen/')


# Performance monitoring decorator
def monitor_performance(func):
    """Decorator to monitor function performance"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            execution_time = time.time() - start_time
            
            # Log slow functions
            if execution_time > 0.1:
                logger.warning(
                    f"Slow function: {func.__name__} took {execution_time:.3f}s"
                )
            
            # Add to cache for monitoring
            cache_key = f"perf_monitor:{func.__name__}"
            cache.set(cache_key, execution_time, 3600)
    
    return wrapper


# Performance utilities
class PerformanceUtils:
    """Utility class for performance optimization"""
    
    @staticmethod
    def batch_queries(queryset, batch_size=1000):
        """Process queryset in batches to avoid memory issues"""
        for i in range(0, queryset.count(), batch_size):
            yield queryset[i:i + batch_size]
    
    @staticmethod
    def prefetch_related_optimized(queryset, *fields):
        """Optimized prefetch_related with select_related"""
        return queryset.select_related(*fields).prefetch_related(*fields)
    
    @staticmethod
    def cache_key_generator(*args, **kwargs):
        """Generate consistent cache keys"""
        import hashlib
        
        # Convert args and kwargs to string
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        
        # Create hash
        key_string = ':'.join(key_parts)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    @staticmethod
    def rate_limit_key(request, action):
        """Generate rate limiting key"""
        user_id = request.user.id if request.user.is_authenticated else 'anonymous'
        return f"rate_limit:{action}:{user_id}"
    
    @staticmethod
    def check_rate_limit(request, action, max_requests=100, window=3600):
        """Check if rate limit is exceeded"""
        key = PerformanceUtils.rate_limit_key(request, action)
        current_count = cache.get(key, 0)
        
        if current_count >= max_requests:
            return False
        
        # Increment counter
        cache.set(key, current_count + 1, window)
        return True
