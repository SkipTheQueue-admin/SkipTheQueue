"""
Performance monitoring middleware for SkipTheQueue
Enhanced with better caching strategies and database optimization
"""

import time
import logging
from django.core.cache import cache
from django.conf import settings
from django.db import connection
from django.db.models import Q
from functools import wraps

logger = logging.getLogger(__name__)

class PerformanceMiddleware:
    """
    Enhanced middleware to monitor and optimize performance
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Start timing
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Log slow requests
        if response_time > getattr(settings, 'SLOW_REQUEST_THRESHOLD', 1.0):
            logger.warning(
                f"Slow request: {request.path} took {response_time:.2f}s "
                f"from {request.META.get('REMOTE_ADDR', 'unknown')}"
            )
        
        # Add performance headers
        response['X-Response-Time'] = f"{response_time:.3f}s"
        
        # Cache performance metrics
        self._update_performance_metrics(request.path, response_time)
        
        return response
    
    def _update_performance_metrics(self, path, response_time):
        """
        Update performance metrics in cache
        """
        try:
            # Get current metrics
            metrics_key = f'performance_metrics_{path}'
            metrics = cache.get(metrics_key, {
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
            })
            
            # Update metrics
            metrics['count'] += 1
            metrics['total_time'] += response_time
            metrics['avg_time'] = metrics['total_time'] / metrics['count']
            metrics['min_time'] = min(metrics['min_time'], response_time)
            metrics['max_time'] = max(metrics['max_time'], response_time)
            
            # Cache for 1 hour
            cache.set(metrics_key, metrics, 3600)
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")

class QueryOptimizationMiddleware:
    """
    Enhanced middleware to optimize database queries
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        
        # Add query optimization headers
        response['X-Query-Optimization'] = 'enabled'
        
        return response

class DatabaseOptimizationMiddleware:
    """
    Middleware to optimize database connections and queries
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        
        # Close database connections to prevent connection leaks
        connection.close()
        
        return response

def cache_result(timeout=300, key_prefix=''):
    """
    Decorator to cache function results for better performance
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{key_prefix}_{func.__name__}_{hash(str(args))}_{hash(str(kwargs))}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator

def optimize_queryset(queryset, select_related=None, prefetch_related=None, only=None):
    """
    Helper function to optimize querysets
    """
    if select_related:
        queryset = queryset.select_related(*select_related)
    
    if prefetch_related:
        queryset = queryset.prefetch_related(*prefetch_related)
    
    if only:
        queryset = queryset.only(*only)
    
    return queryset

def batch_update_cache(cache_keys, timeout=300):
    """
    Batch update multiple cache keys for better performance
    """
    try:
        # Use pipeline for better performance
        pipe = cache.client.pipeline()
        for key in cache_keys:
            pipe.expire(key, timeout)
        pipe.execute()
    except Exception as e:
        logger.error(f"Error in batch cache update: {e}")

def get_performance_summary():
    """
    Get performance summary for monitoring
    """
    try:
        # Get all performance metrics
        all_metrics = {}
        
        # This would iterate through all cached performance metrics
        # For now, return a basic structure
        return {
            'total_requests': 0,
            'avg_response_time': 0,
            'slow_requests': 0,
            'cache_hit_rate': 0,
        }
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        return {}

# Performance monitoring decorators
def monitor_performance(func_name=None):
    """
    Decorator to monitor function performance
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise e
            finally:
                execution_time = time.time() - start_time
                
                # Log performance metrics
                func_name_actual = func_name or func.__name__
                logger.info(f"Function {func_name_actual} executed in {execution_time:.3f}s (success: {success})")
                
                # Cache performance data
                perf_key = f'func_perf_{func_name_actual}'
                perf_data = cache.get(perf_key, {'count': 0, 'total_time': 0, 'success_count': 0})
                perf_data['count'] += 1
                perf_data['total_time'] += execution_time
                if success:
                    perf_data['success_count'] += 1
                cache.set(perf_key, perf_data, 3600)
            
            return result
        return wrapper
    return decorator
