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
        
        # Content Security Policy
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.google-analytics.com https://www.googletagmanager.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://www.google-analytics.com; "
            "frame-ancestors 'none';"
        )
        response['Content-Security-Policy'] = csp_policy
        
        # HSTS header (only for HTTPS)
        if not settings.DEBUG and request.is_secure():
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
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+)',
            r'(\b(and|or)\b\s+\'\w+\'\s*=\s*\'\w+\')',
            r'(\b(and|or)\b\s+\w+\s*=\s*\w+)',
            r'(\b(and|or)\b\s+\w+\s*like\s*\w+)',
            r'(\b(and|or)\b\s+\w+\s*in\s*\([^)]*\))',
            r'(\b(and|or)\b\s+\w+\s*between\s+\w+\s+and\s+\w+)',
            r'(\b(and|or)\b\s+\w+\s*exists\s*\([^)]*\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+exists\s*\([^)]*\))',
            r'(\b(and|or)\b\s+\w+\s*is\s+null)',
            r'(\b(and|or)\b\s+\w+\s*is\s+not\s+null)',
            r'(\b(and|or)\b\s+\w+\s*=\s*null)',
            r'(\b(and|or)\b\s+\w+\s*!=\s*null)',
            r'(\b(and|or)\b\s+\w+\s*<>\s*null)',
            r'(\b(and|or)\b\s+\w+\s*>\s*\d+)',
            r'(\b(and|or)\b\s+\w+\s*<\s*\d+)',
            r'(\b(and|or)\b\s+\w+\s*>=\s*\d+)',
            r'(\b(and|or)\b\s+\w+\s*<=\s*\d+)',
            r'(\b(and|or)\b\s+\w+\s*!=\s*\d+)',
            r'(\b(and|or)\b\s+\w+\s*<>\s*\d+)',
            r'(\b(and|or)\b\s+\w+\s*like\s*\'\w+\')',
            r'(\b(and|or)\b\s+\w+\s*not\s+like\s*\'\w+\')',
            r'(\b(and|or)\b\s+\w+\s*in\s*\(\'\w+\'\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+in\s*\(\'\w+\'\))',
            r'(\b(and|or)\b\s+\w+\s*between\s+\'\w+\'\s+and\s+\'\w+\')',
            r'(\b(and|or)\b\s+\w+\s*not\s+between\s+\'\w+\'\s+and\s+\'\w+\')',
            r'(\b(and|or)\b\s+\w+\s*exists\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+exists\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*=\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*!=\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*<>\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*>\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*<\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*>=\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*<=\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*like\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+like\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*in\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+in\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*between\s*\(select\s+\w+\s+from\s+\w+\)\s+and\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+between\s*\(select\s+\w+\s+from\s+\w+\)\s+and\s*\(select\s+\w+\s+from\s+\w+\))',
            r'(\b(and|or)\b\s+\w+\s*exists\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+exists\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*=\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*!=\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*<>\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*>\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*<\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*>=\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*<=\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*like\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+like\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*in\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+in\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*between\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\)\s+and\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
            r'(\b(and|or)\b\s+\w+\s*not\s+between\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\)\s+and\s*\(select\s+\w+\s+from\s+\w+\s+where\s+\w+\s*=\s*\d+\))',
        ]
        
        # Check query parameters
        for key, value in request.GET.items():
            for pattern in suspicious_patterns:
                if re.search(pattern, str(value), re.IGNORECASE):
                    return True
        
        # Check POST data
        if request.method == 'POST':
            for key, value in request.POST.items():
                for pattern in suspicious_patterns:
                    if re.search(pattern, str(value), re.IGNORECASE):
                        return True
        
        return False
    
    def _validate_user_session(self, request):
        """Validate user session security"""
        
        # Check if user is still active
        if not request.user.is_active:
            return False
        
        # Check session security hash
        security_hash = request.session.get('_security_hash')
        if not security_hash:
            return False
        
        # Verify security hash
        expected_hash = SecurityValidator.generate_secure_token({
            'user_id': request.user.id,
            'ip': request.META.get('REMOTE_ADDR', ''),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')
        })
        
        return security_hash == expected_hash

class LoggingMiddleware(MiddlewareMixin):
    """Enhanced logging middleware"""
    
    def process_request(self, request):
        """Log incoming requests"""
        request.start_time = time.time()
        
        # Log request details
        logger.info(
            f"Request: {request.method} {request.path} "
            f"from {request.META.get('REMOTE_ADDR', 'unknown')} "
            f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}"
        )
        
        return None
    
    def process_response(self, request, response):
        """Log response details"""
        
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            
            logger.info(
                f"Response: {response.status_code} "
                f"Duration: {duration:.3f}s "
                f"for {request.method} {request.path}"
            )
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions"""
        logger.error(
            f"Exception: {type(exception).__name__}: {str(exception)} "
            f"for {request.method} {request.path} "
            f"from {request.META.get('REMOTE_ADDR', 'unknown')}"
        )
        
        return None 