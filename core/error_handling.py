"""
Comprehensive Error Handling and Monitoring System
Prevents 500 errors and provides detailed error tracking
"""

import logging
import traceback
import time
from functools import wraps
from django.http import JsonResponse, HttpResponseServerError
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import DatabaseError, IntegrityError
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)

class ErrorTracker:
    """Tracks and analyzes errors for prevention"""
    
    @staticmethod
    def log_error(error, context=None, user=None):
        """Log error with context for analysis"""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': timezone.now().isoformat(),
            'user_id': user.id if user and user.is_authenticated else None,
            'context': context or {},
            'traceback': traceback.format_exc()
        }
        
        # Log to file
        logger.error(f"Error tracked: {error_data}")
        
        # Store in cache for monitoring
        error_key = f"error_{int(time.time())}"
        cache.set(error_key, error_data, 3600)  # Keep for 1 hour
        
        return error_data
    
    @staticmethod
    def get_error_stats():
        """Get error statistics for monitoring"""
        # This would be implemented with a proper monitoring system
        # For now, we'll use cache-based tracking
        return {
            'total_errors': 0,
            'error_types': {},
            'recent_errors': []
        }

def safe_view(view_func):
    """Decorator to wrap views with comprehensive error handling"""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except ValidationError as e:
            ErrorTracker.log_error(e, {'view': view_func.__name__, 'request_path': request.path})
            return JsonResponse({
                'error': 'Validation error',
                'details': e.message_dict if hasattr(e, 'message_dict') else str(e)
            }, status=400)
        except ObjectDoesNotExist as e:
            ErrorTracker.log_error(e, {'view': view_func.__name__, 'request_path': request.path})
            return JsonResponse({
                'error': 'Resource not found',
                'message': 'The requested resource does not exist'
            }, status=404)
        except DatabaseError as e:
            ErrorTracker.log_error(e, {'view': view_func.__name__, 'request_path': request.path})
            return JsonResponse({
                'error': 'Database error',
                'message': 'A database error occurred. Please try again.'
            }, status=500)
        except IntegrityError as e:
            ErrorTracker.log_error(e, {'view': view_func.__name__, 'request_path': request.path})
            return JsonResponse({
                'error': 'Data integrity error',
                'message': 'The data provided conflicts with existing data.'
            }, status=400)
        except Exception as e:
            ErrorTracker.log_error(e, {'view': view_func.__name__, 'request_path': request.path}, request.user)
            if settings.DEBUG:
                return JsonResponse({
                    'error': 'Internal server error',
                    'message': str(e),
                    'traceback': traceback.format_exc()
                }, status=500)
            else:
                return JsonResponse({
                    'error': 'Internal server error',
                    'message': 'An unexpected error occurred. Please try again.'
                }, status=500)
    return wrapped

def database_safe(func):
    """Decorator for database operations with retry logic"""
    @wraps(func)
    def wrapped(*args, **kwargs):
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except DatabaseError as e:
                if attempt == max_retries - 1:
                    ErrorTracker.log_error(e, {'function': func.__name__, 'attempt': attempt})
                    raise
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
        return None
    return wrapped

class ErrorPreventionMiddleware:
    """Middleware to prevent common errors"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Pre-request validation
        if self._is_suspicious_request(request):
            return JsonResponse({
                'error': 'Suspicious request detected',
                'message': 'Request blocked for security reasons'
            }, status=403)
        
        response = self.get_response(request)
        
        # Post-response validation
        if response.status_code >= 500:
            ErrorTracker.log_error(
                Exception(f"HTTP {response.status_code} error"),
                {'request_path': request.path, 'method': request.method}
            )
        
        return response
    
    def _is_suspicious_request(self, request):
        """Check for suspicious request patterns"""
        # Check for extremely long URLs
        if len(request.path) > 2000:
            return True
        
        # Check for suspicious headers
        suspicious_headers = ['X-Forwarded-For', 'X-Real-IP']
        for header in suspicious_headers:
            if header in request.META:
                value = request.META[header]
                if len(value) > 100:  # Suspiciously long IP
                    return True
        
        return False

def validate_model_data(model_class, data):
    """Validate model data before saving"""
    try:
        instance = model_class(**data)
        instance.full_clean()
        return True, None
    except ValidationError as e:
        return False, e.message_dict

def safe_save_model(instance, **kwargs):
    """Safely save model with error handling"""
    try:
        instance.save(**kwargs)
        return True, None
    except (ValidationError, IntegrityError) as e:
        ErrorTracker.log_error(e, {'model': instance.__class__.__name__})
        return False, str(e)

# Error monitoring utilities
def monitor_performance(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    def wrapped(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log slow operations
            if execution_time > 1.0:  # More than 1 second
                logger.warning(f"Slow operation detected: {func.__name__} took {execution_time:.2f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            ErrorTracker.log_error(e, {
                'function': func.__name__,
                'execution_time': execution_time
            })
            raise
    return wrapped

# Health check utilities
def check_database_health():
    """Check database connectivity and health"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return True, "Database is healthy"
    except Exception as e:
        return False, f"Database error: {str(e)}"

def check_cache_health():
    """Check cache connectivity"""
    try:
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        return result == 'ok', "Cache is healthy"
    except Exception as e:
        return False, f"Cache error: {str(e)}"

def comprehensive_health_check():
    """Perform comprehensive health check"""
    health_status = {
        'timestamp': timezone.now().isoformat(),
        'overall_status': 'healthy',
        'checks': {}
    }
    
    # Database check
    db_healthy, db_message = check_database_health()
    health_status['checks']['database'] = {
        'status': 'healthy' if db_healthy else 'unhealthy',
        'message': db_message
    }
    
    # Cache check
    cache_healthy, cache_message = check_cache_health()
    health_status['checks']['cache'] = {
        'status': 'healthy' if cache_healthy else 'unhealthy',
        'message': cache_message
    }
    
    # Update overall status
    if not all([db_healthy, cache_healthy]):
        health_status['overall_status'] = 'unhealthy'
    
    return health_status
