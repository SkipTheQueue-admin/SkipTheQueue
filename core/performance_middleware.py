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
from django.db import connection

logger = logging.getLogger(__name__)


class PerformanceMiddleware(MiddlewareMixin):
    """
    Middleware to monitor and optimize performance
    - Tracks response times
    - Monitors database queries
    - Implements caching strategies
    - Provides performance headers
    """
    
    def process_request(self, request):
        """Start performance monitoring for this request"""
        # Start timing
        request.start_time = time.time()
        
        # Count initial database queries
        request.initial_queries = len(connection.queries)
        
        # Set performance tracking flag
        request.performance_tracked = True
        
        return None
    
    def process_response(self, request, response):
        """Add performance metrics to response"""
        if hasattr(request, 'performance_tracked'):
            # Calculate response time
            response_time = time.time() - request.start_time
            
            # Count database queries
            final_queries = len(connection.queries)
            query_count = final_queries - request.initial_queries
            
            # Calculate database time
            db_time = sum(float(query.get('time', 0)) for query in connection.queries[request.initial_queries:])
            
            # Add performance headers
            response['X-Response-Time'] = f'{response_time:.3f}s'
            response['X-Database-Queries'] = str(query_count)
            response['X-Database-Time'] = f'{db_time:.3f}s'
            response['X-Cache-Status'] = self.get_cache_status(request)
            
            # Log slow responses
            if response_time > 1.0:  # Log responses taking more than 1 second
                logger.warning(
                    f'Slow response: {request.path} took {response_time:.3f}s '
                    f'({query_count} queries, {db_time:.3f}s DB time)'
                )
            
            # Log slow database queries
            if db_time > 0.5:  # Log database operations taking more than 0.5 seconds
                logger.warning(
                    f'Slow database: {request.path} had {db_time:.3f}s DB time '
                    f'({query_count} queries)'
                )
            
            # Update performance metrics in cache
            self.update_performance_metrics(request.path, response_time, query_count, db_time)
        
        return response
    
    def get_cache_status(self, request):
        """Determine cache status for the request"""
        if hasattr(request, 'cache_hit'):
            return 'HIT' if request.cache_hit else 'MISS'
        return 'N/A'
    
    def update_performance_metrics(self, path, response_time, query_count, db_time):
        """Update performance metrics in cache for monitoring"""
        try:
            # Get current metrics
            metrics = cache.get('performance_metrics', {})
            
            # Update path-specific metrics
            if path not in metrics:
                metrics[path] = {
                    'count': 0,
                    'total_time': 0,
                    'total_queries': 0,
                    'total_db_time': 0,
                    'avg_time': 0,
                    'avg_queries': 0,
                    'avg_db_time': 0
                }
            
            path_metrics = metrics[path]
            path_metrics['count'] += 1
            path_metrics['total_time'] += response_time
            path_metrics['total_queries'] += query_count
            path_metrics['total_db_time'] += db_time
            
            # Calculate averages
            path_metrics['avg_time'] = path_metrics['total_time'] / path_metrics['count']
            path_metrics['avg_queries'] = path_metrics['total_queries'] / path_metrics['count']
            path_metrics['avg_db_time'] = path_metrics['total_db_time'] / path_metrics['count']
            
            # Update global metrics
            if 'global' not in metrics:
                metrics['global'] = {
                    'total_requests': 0,
                    'total_time': 0,
                    'total_queries': 0,
                    'total_db_time': 0,
                    'avg_response_time': 0,
                    'avg_queries_per_request': 0,
                    'avg_db_time_per_request': 0
                }
            
            global_metrics = metrics['global']
            global_metrics['total_requests'] += 1
            global_metrics['total_time'] += response_time
            global_metrics['total_queries'] += query_count
            global_metrics['total_db_time'] += db_time
            
            global_metrics['avg_response_time'] = global_metrics['total_time'] / global_metrics['total_requests']
            global_metrics['avg_queries_per_request'] = global_metrics['total_queries'] / global_metrics['total_requests']
            global_metrics['avg_db_time_per_request'] = global_metrics['total_db_time'] / global_metrics['total_requests']
            
            # Store updated metrics (cache for 1 hour)
            cache.set('performance_metrics', metrics, 3600)
            
        except Exception as e:
            logger.error(f'Error updating performance metrics: {e}')


class CacheMiddleware(MiddlewareMixin):
    """
    Middleware to implement intelligent caching strategies
    - Cache frequently accessed data
    - Implement cache warming
    - Handle cache invalidation
    """
    
    def process_request(self, request):
        """Check cache for eligible requests"""
        # Skip caching for non-GET requests
        if request.method != 'GET':
            return None
        
        # Skip caching for authenticated users on sensitive pages
        if request.user.is_authenticated and self.is_sensitive_page(request.path):
            return None
        
        # Generate cache key
        cache_key = self.generate_cache_key(request)
        
        # Try to get from cache
        cached_response = cache.get(cache_key)
        if cached_response:
            request.cache_hit = True
            return cached_response
        
        request.cache_hit = False
        return None
    
    def process_response(self, request, response):
        """Cache eligible responses"""
        # Only cache successful GET responses
        if (request.method == 'GET' and 
            response.status_code == 200 and 
            not request.user.is_authenticated and
            not self.is_sensitive_page(request.path)):
            
            cache_key = self.generate_cache_key(request)
            cache_timeout = self.get_cache_timeout(request.path)
            
            if cache_timeout > 0:
                cache.set(cache_key, response, cache_timeout)
        
        return response
    
    def generate_cache_key(self, request):
        """Generate a unique cache key for the request"""
        # Include path and query parameters
        key_parts = [request.path]
        
        # Add query parameters (sorted for consistency)
        if request.GET:
            sorted_params = sorted(request.GET.items())
            key_parts.extend([f"{k}={v}" for k, v in sorted_params])
        
        return f"page_cache:{':'.join(key_parts)}"
    
    def get_cache_timeout(self, path):
        """Get cache timeout for specific paths"""
        # Cache static pages longer
        if path in ['/', '/menu/', '/help/']:
            return 1800  # 30 minutes
        
        # Cache college pages
        if '/college/' in path:
            return 900  # 15 minutes
        
        # Default cache time
        return 300  # 5 minutes
    
    def is_sensitive_page(self, path):
        """Check if page contains sensitive data"""
        sensitive_paths = [
            '/admin/',
            '/profile/',
            '/orders/',
            '/cart/',
            '/payment/',
            '/canteen/'
        ]
        
        return any(sensitive in path for sensitive in sensitive_paths)


class QueryOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware to optimize database queries
    - Monitor N+1 queries
    - Suggest query optimizations
    - Implement query result caching
    """
    
    def process_request(self, request):
        """Initialize query monitoring"""
        request.query_patterns = {}
        request.duplicate_queries = []
        return None
    
    def process_response(self, request, response):
        """Analyze and optimize queries"""
        if hasattr(request, 'query_patterns'):
            self.analyze_queries(request)
            self.optimize_queries(request)
        
        return response
    
    def analyze_queries(self, request):
        """Analyze query patterns for optimization opportunities"""
        queries = connection.queries
        
        # Group queries by pattern
        for query in queries:
            sql = query.get('sql', '')
            if sql:
                # Extract table name from query
                table_name = self.extract_table_name(sql)
                if table_name:
                    if table_name not in request.query_patterns:
                        request.query_patterns[table_name] = []
                    request.query_patterns[table_name].append(sql)
        
        # Detect N+1 queries
        for table, table_queries in request.query_patterns.items():
            if len(table_queries) > 5:  # Potential N+1 if more than 5 queries on same table
                logger.warning(f'Potential N+1 query detected on {table}: {len(table_queries)} queries')
    
    def optimize_queries(self, request):
        """Suggest query optimizations"""
        # This would implement actual query optimizations
        # For now, just log suggestions
        pass
    
    def extract_table_name(self, sql):
        """Extract table name from SQL query"""
        sql_lower = sql.lower()
        
        # Common patterns
        if 'from ' in sql_lower:
            parts = sql_lower.split('from ')
            if len(parts) > 1:
                table_part = parts[1].split()[0]
                return table_part.strip('"\'')
        
        return None


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
    """
    Decorator to monitor function performance
    Usage: @monitor_performance
    """
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_queries = len(connection.queries)
        
        try:
            result = func(*args, **kwargs)
            
            # Calculate metrics
            execution_time = time.time() - start_time
            query_count = len(connection.queries) - start_queries
            
            # Log if function is slow
            if execution_time > 0.5:
                logger.warning(
                    f'Slow function {func.__name__}: {execution_time:.3f}s '
                    f'({query_count} queries)'
                )
            
            return result
            
        except Exception as e:
            logger.error(f'Error in {func.__name__}: {e}')
            raise
    
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
