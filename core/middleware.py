"""
Security Middleware for SkipTheQueue
Protects against various hacking attempts and security threats
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
    """Comprehensive security middleware"""
    
    def process_request(self, request):
        """Process incoming requests for security checks"""
        
        # Skip security checks for PWA files and static files
        if (request.path.startswith('/static/') or 
            request.path.startswith('/admin/') or
            request.path in ['/manifest.json', '/sw.js'] or
            request.path.startswith('/manifest.json') or
            request.path.startswith('/sw.js')):
            return None
        
        # Update session security
        SessionSecurity.update_session_security(request)
        
        # Rate limiting for all requests
        if hasattr(settings, 'RATE_LIMIT_ENABLED') and settings.RATE_LIMIT_ENABLED:
            is_allowed, message = RateLimiter.check_rate_limit(
                request, 
                'global', 
                getattr(settings, 'RATE_LIMIT_REQUESTS', 100),
                getattr(settings, 'RATE_LIMIT_WINDOW', 60)
            )
            
            if not is_allowed:
                logger.warning(f"Rate limit exceeded for {request.META.get('REMOTE_ADDR', 'unknown')}")
                return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
        
        # Validate session security
        is_valid, message = SessionSecurity.validate_session(request)
        if not is_valid:
            logger.warning(f"Invalid session for {request.META.get('REMOTE_ADDR', 'unknown')}: {message}")
            return HttpResponseForbidden("Invalid session. Please login again.")
        
        # Add security headers
        request.META['HTTP_X_REQUESTED_WITH'] = 'XMLHttpRequest'
        
        return None
    
    def process_response(self, request, response):
        """Add security headers to responses"""
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy - allow Font Awesome CDN and inline for our templates
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
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
    """Enhanced authentication middleware"""
    
    def process_request(self, request):
        """Process authentication-related security"""
        
        # Skip for static files, admin, and PWA files
        if (request.path.startswith('/static/') or 
            request.path.startswith('/admin/') or
            request.path in ['/manifest.json', '/sw.js'] or
            request.path.startswith('/manifest.json') or
            request.path.startswith('/sw.js')):
            return None
        
        # Check for suspicious activity
        if self._is_suspicious_request(request):
            logger.warning(f"Suspicious request detected from {request.META.get('REMOTE_ADDR', 'unknown')}")
            return HttpResponseForbidden("Suspicious activity detected.")
        
        # Validate user session if authenticated
        if request.user.is_authenticated:
            if not self._validate_user_session(request):
                logger.warning(f"Invalid user session for {request.user.username}")
                return HttpResponseForbidden("Invalid session. Please login again.")
        
        return None
    
    def _is_suspicious_request(self, request):
        """Check for suspicious request patterns"""
        
        # Check for SQL injection attempts
        suspicious_patterns = [
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b)'
        ]
        
        for key, value in request.GET.items():
            for pattern in suspicious_patterns:
                if re.search(pattern, str(value), re.IGNORECASE):
                    return True
        
        if request.method == 'POST':
            for key, value in request.POST.items():
                for pattern in suspicious_patterns:
                    if re.search(pattern, str(value), re.IGNORECASE):
                        return True
        
        return False
    
    def _validate_user_session(self, request):
        """Validate user session security"""
        
        if not request.user.is_active:
            return False
        
        security_hash = request.session.get('_security_hash')
        if not security_hash:
            return False
        
        expected_hash = SecurityValidator.generate_secure_token({
            'user_id': request.user.id,
            'ip': request.META.get('REMOTE_ADDR', ''),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')
        })
        
        return security_hash == expected_hash

class LoggingMiddleware(MiddlewareMixin):
    """Enhanced logging middleware"""
    
    def process_request(self, request):
        request.start_time = time.time()
        logger.info(
            f"Request: {request.method} {request.path} "
            f"from {request.META.get('REMOTE_ADDR', 'unknown')} "
            f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}"
        )
        return None
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(
                f"Response: {response.status_code} "
                f"Duration: {duration:.3f}s "
                f"for {request.method} {request.path}"
            )
        return response
    
    def process_exception(self, request, exception):
        logger.error(
            f"Exception: {type(exception).__name__}: {str(exception)} "
            f"for {request.method} {request.path} "
            f"from {request.META.get('REMOTE_ADDR', 'unknown')}"
        )
        return None 