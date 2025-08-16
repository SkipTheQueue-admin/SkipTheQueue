"""
Security Middleware for SkipTheQueue
Protects against various hacking attempts and security threats
Optimized for performance
"""

import logging
import time
import re
from django.conf import settings
from django.http import HttpResponseForbidden, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from .security import SecurityValidator, SessionSecurity, RateLimiter

logger = logging.getLogger(__name__)

class SecurityMiddleware(MiddlewareMixin):
    """Comprehensive security middleware - optimized for performance"""
    
    def process_request(self, request):
        """Process incoming requests for security checks - optimized for performance"""
        
        # Skip security checks for static files, admin, and PWA files
        if (request.path.startswith('/static/') or 
            request.path.startswith('/admin/') or
            request.path in ['/manifest.json', '/sw.js'] or
            request.path.startswith('/manifest.json') or
            request.path.startswith('/sw.js') or
            request.path.startswith('/favicon.ico')):
            return None
        
        # Only perform heavy security checks for sensitive endpoints
        if request.path.startswith('/canteen/') or request.path.startswith('/admin-dashboard/'):
            # Update session security
            SessionSecurity.update_session_security(request)
            
            # Validate session security only for authenticated endpoints
            is_valid, message = SessionSecurity.validate_session(request)
            if not is_valid:
                logger.warning(f"Invalid session for {request.META.get('REMOTE_ADDR', 'unknown')}: {message}")
                return HttpResponseForbidden("Invalid session. Please login again.")
        
        # Add basic security header only for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        
        return None
    
    def process_response(self, request, response):
        """Add security headers to responses - optimized"""
        
        # Essential security headers only
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Simplified CSP policy for better performance
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "font-src 'self' https://cdnjs.cloudflare.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response['Content-Security-Policy'] = csp_policy
        
        # HSTS header (only for HTTPS)
        if not settings.DEBUG and getattr(request, 'is_secure', lambda: False)():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response

class AuthenticationMiddleware(MiddlewareMixin):
    """Enhanced authentication middleware - optimized for performance"""
    
    def process_request(self, request):
        """Process authentication-related security - optimized"""
        
        # Skip for static files, admin, and PWA files
        if (request.path.startswith('/static/') or 
            request.path.startswith('/admin/') or
            request.path in ['/manifest.json', '/sw.js'] or
            request.path.startswith('/manifest.json') or
            request.path.startswith('/sw.js')):
            return None
        
        # Only check for suspicious activity on POST requests
        if request.method == 'POST':
            if self._is_suspicious_request(request):
                logger.warning(f"Suspicious request detected from {request.META.get('REMOTE_ADDR', 'unknown')}")
                return HttpResponseForbidden("Suspicious activity detected.")
        
        # Validate user session if authenticated and accessing sensitive areas
        if (request.user.is_authenticated and 
            (request.path.startswith('/canteen/') or request.path.startswith('/admin-dashboard/'))):
            if not self._validate_user_session(request):
                logger.warning(f"Invalid user session for {request.user.username}")
                return HttpResponseForbidden("Invalid session. Please login again.")
        
        return None
    
    def _is_suspicious_request(self, request):
        """Check for suspicious request patterns - optimized"""
        
        # Only check POST data for SQL injection attempts
        if request.method == 'POST':
            suspicious_patterns = [
                r'(\b(union|select|insert|update|delete|drop|create|alter)\b)'
            ]
            
            for key, value in request.POST.items():
                for pattern in suspicious_patterns:
                    if re.search(pattern, str(value), re.IGNORECASE):
                        return True
        
        return False
    
    def _validate_user_session(self, request):
        """Validate user session security - optimized"""
        
        if not request.user.is_active:
            return False
        
        # Simplified session validation for better performance
        security_hash = request.session.get('_security_hash')
        if not security_hash:
            return False
        
        # Cache the validation result for better performance
        cache_key = f"session_validation_{request.user.id}_{request.META.get('REMOTE_ADDR', '')}"
        cached_result = cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        # Perform validation
        expected_hash = SecurityValidator.generate_secure_token({
            'user_id': request.user.id,
            'ip': request.META.get('REMOTE_ADDR', ''),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')
        })
        
        result = security_hash == expected_hash
        
        # Cache the result for 5 minutes
        cache.set(cache_key, result, 300)
        
        return result

class LoggingMiddleware(MiddlewareMixin):
    """Enhanced logging middleware - optimized for performance"""
    
    def process_request(self, request):
        # Only log for non-static requests to reduce overhead
        if not request.path.startswith('/static/'):
            request.start_time = time.time()
            # Only log in debug mode or for slow requests
            if settings.DEBUG:
                logger.info(
                    f"Request: {request.method} {request.path} "
                    f"from {request.META.get('REMOTE_ADDR', 'unknown')} "
                    f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}"
                )
        return None
    
    def process_response(self, request, response):
        # Only log for non-static requests to reduce overhead
        if (hasattr(request, 'start_time') and 
            not request.path.startswith('/static/')):
            duration = time.time() - request.start_time
            
            # Only log slow requests for performance monitoring
            if duration > 0.5:  # Reduced threshold for better performance monitoring
                logger.warning(
                    f"Slow request: {response.status_code} "
                    f"Duration: {duration:.3f}s "
                    f"for {request.method} {request.path}"
                )
        return response
    
    def process_exception(self, request, exception):
        # Only log exceptions for non-static requests
        if not request.path.startswith('/static/'):
            logger.error(
                f"Exception: {type(exception).__name__}: {str(exception)} "
                f"for {request.method} {request.path} "
                f"from {request.META.get('REMOTE_ADDR', 'unknown')}"
            )
        return None 