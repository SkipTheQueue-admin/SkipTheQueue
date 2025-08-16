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
        
        # Improved CSP policy for better security and performance
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
            "font-src 'self' https://cdnjs.cloudflare.com data:; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response['Content-Security-Policy'] = csp_policy
        
        # HSTS header (only for HTTPS)
        if not settings.DEBUG and getattr(request, 'is_secure', lambda: False)():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
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
                return HttpResponseForbidden("Invalid user session. Please login again.")
        
        return None
    
    def _is_suspicious_request(self, request):
        """Check for suspicious request patterns - optimized"""
        # Check for rapid successive requests
        user_id = request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR', 'anonymous')
        rate_key = f"suspicious_{user_id}_{request.path}"
        
        request_count = cache.get(rate_key, 0)
        if request_count > 10:  # More than 10 requests in 1 minute
            return True
        
        cache.set(rate_key, request_count + 1, 60)
        
        # Check for suspicious headers
        suspicious_headers = ['X-Forwarded-For', 'X-Real-IP', 'X-Client-IP']
        for header in suspicious_headers:
            if header in request.headers and request.headers[header] != request.META.get('REMOTE_ADDR'):
                return True
        
        return False
    
    def _validate_user_session(self, request):
        """Validate user session security - optimized"""
        try:
            # Check if user is still active
            if not request.user.is_active:
                return False
            
            # Check if user has required permissions for sensitive areas
            if request.path.startswith('/canteen/'):
                # For canteen staff, check if they have access to the specific college
                college_slug = request.path.split('/')[2] if len(request.path.split('/')) > 2 else None
                if college_slug:
                    from orders.models import CanteenStaff
                    try:
                        staff = CanteenStaff.objects.get(
                            user=request.user, 
                            college__slug=college_slug, 
                            is_active=True
                        )
                        return True
                    except CanteenStaff.DoesNotExist:
                        return False
            
            elif request.path.startswith('/admin-dashboard/'):
                # For admin dashboard, check if user is superuser
                return request.user.is_superuser
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating user session: {e}")
            return False

class LoggingMiddleware(MiddlewareMixin):
    """Enhanced logging middleware - optimized for performance"""
    
    def process_request(self, request):
        """Log request information - optimized"""
        # Only log for non-static, non-admin requests
        if (not request.path.startswith('/static/') and 
            not request.path.startswith('/admin/') and
            not request.path.startswith('/manifest.json') and
            not request.path.startswith('/sw.js')):
            
            # Add request start time for performance monitoring
            request.start_time = time.time()
            
            # Log only important requests
            if request.path.startswith('/canteen/') or request.path.startswith('/admin-dashboard/'):
                logger.info(f"Access to sensitive area: {request.path} by {request.user.username if request.user.is_authenticated else 'anonymous'}")
        
        return None
    
    def process_response(self, request, response):
        """Log response information - optimized"""
        # Only log for non-static, non-admin requests
        if (not request.path.startswith('/static/') and 
            not request.path.startswith('/admin/') and
            not request.path.startswith('/manifest.json') and
            not request.path.startswith('/sw.js')):
            
            # Calculate request duration
            if hasattr(request, 'start_time'):
                duration = time.time() - request.start_time
                
                # Log slow requests
                if duration > 1.0:  # Log requests slower than 1 second
                    logger.warning(f"Slow request: {request.path} took {duration:.2f}s")
                
                # Log errors
                if response.status_code >= 400:
                    logger.error(f"Error response: {request.path} - {response.status_code} in {duration:.2f}s")
        
        return response

class PerformanceMiddleware(MiddlewareMixin):
    """Performance monitoring middleware - optimized"""
    
    def process_request(self, request):
        """Monitor request performance - optimized"""
        # Only monitor for important requests
        if (request.path.startswith('/canteen/') or 
            request.path.startswith('/admin-dashboard/') or
            request.path.startswith('/api/')):
            
            request.start_time = time.time()
            request.query_count = 0
        
        return None
    
    def process_response(self, request, response):
        """Monitor response performance - optimized"""
        # Only monitor for important requests
        if (request.path.startswith('/canteen/') or 
            request.path.startswith('/admin-dashboard/') or
            request.path.startswith('/api/')):
            
            if hasattr(request, 'start_time'):
                duration = time.time() - request.start_time
                
                # Log performance metrics
                if duration > 0.5:  # Log requests slower than 0.5 seconds
                    logger.warning(f"Performance issue: {request.path} took {duration:.2f}s")
                
                # Add performance headers
                response['X-Request-Duration'] = f"{duration:.3f}"
        
        return response 