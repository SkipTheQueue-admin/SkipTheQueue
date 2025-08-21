"""
Security Middleware for SkipTheQueue
Protects against various hacking attempts and security threats
"""

import re
import logging
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('django.security')

class SecurityMiddleware(MiddlewareMixin):
    """Comprehensive security middleware"""
    
    def process_request(self, request):
        """Process each request for security threats"""
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Check for suspicious requests
        if self.is_suspicious_request(request):
            logger.warning(f'Suspicious request detected from {client_ip}: {request.path}')
            return HttpResponseForbidden('Suspicious request detected')
        
        # Rate limiting
        if not self.check_rate_limit(request, client_ip):
            logger.warning(f'Rate limit exceeded from {client_ip}')
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
        
        # Check for SQL injection attempts
        if self.detect_sql_injection(request):
            logger.warning(f'SQL injection attempt detected from {client_ip}')
            return HttpResponseForbidden('Invalid request')
        
        # Check for XSS attempts
        if self.detect_xss_attempt(request):
            logger.warning(f'XSS attempt detected from {client_ip}')
            return HttpResponseForbidden('Invalid request')
        
        # Check for path traversal attempts
        if self.detect_path_traversal(request):
            logger.warning(f'Path traversal attempt detected from {client_ip}')
            return HttpResponseForbidden('Invalid request')
        
        return None
    
    def process_response(self, request, response):
        """Add security headers to response"""
        
        # Security Headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy
        csp_policy = self.get_csp_policy()
        response['Content-Security-Policy'] = csp_policy
        
        # HSTS Header (only for HTTPS)
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_suspicious_request(self, request):
        """Check if request is suspicious"""
        suspicious_patterns = [
            r'script\s*[<>]',
            r'javascript:',
            r'vbscript:',
            r'<iframe',
            r'<object',
            r'<embed',
            r'eval\s*\(',
            r'exec\s*\(',
            r'system\s*\(',
            r'cmd\s*\.',
            r'powershell',
            r'bash\s*-',
            r'\.\./',
            r'\.\.\\',
            r'%00',
            r'%0d',
            r'%0a',
        ]
        
        # Check URL path
        path = request.path.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        
        # Check POST data
        if request.method == 'POST':
            post_data = str(request.POST)
            for pattern in suspicious_patterns:
                if re.search(pattern, post_data, re.IGNORECASE):
                    return True
        
        # Check headers
        headers = str(request.headers)
        for pattern in suspicious_patterns:
            if re.search(pattern, headers, re.IGNORECASE):
                return True
        
        # Check for unusually large requests
        if len(str(request.POST)) > 10000:  # 10KB limit
            return True
        
        return False
    
    def check_rate_limit(self, request, client_ip):
        """Check rate limiting"""
        if not getattr(settings, 'RATE_LIMIT_ENABLED', True):
            return True
        
        max_requests = getattr(settings, 'RATE_LIMIT_MAX_REQUESTS', 100)
        window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)
        
        cache_key = f'rate_limit:{client_ip}'
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= max_requests:
            return False
        
        cache.set(cache_key, current_requests + 1, window)
        return True
    
    def detect_sql_injection(self, request):
        """Detect SQL injection attempts"""
        sql_patterns = [
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(or|and)\b\s+\d+\s*=\s*\d+)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\bfrom\b)',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b.*\bwhere\b)',
        ]
        
        # Check URL parameters
        for key, value in request.GET.items():
            for pattern in sql_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    return True
        
        # Check POST data
        if request.method == 'POST':
            for key, value in request.POST.items():
                for pattern in sql_patterns:
                    if re.search(pattern, str(value), re.IGNORECASE):
                        return True
        
        return False
    
    def detect_xss_attempt(self, request):
        """Detect XSS attempts"""
        xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<applet[^>]*>',
            r'<form[^>]*>',
            r'<input[^>]*>',
            r'<textarea[^>]*>',
            r'<select[^>]*>',
            r'<button[^>]*>',
        ]
        
        # Check URL parameters
        for key, value in request.GET.items():
            for pattern in xss_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    return True
        
        # Check POST data
        if request.method == 'POST':
            for key, value in request.POST.items():
                for pattern in xss_patterns:
                    if re.search(pattern, str(value), re.IGNORECASE):
                        return True
        
        return False
    
    def detect_path_traversal(self, request):
        """Detect path traversal attempts"""
        traversal_patterns = [
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            r'%252e%252e%252f',
            r'%252e%252e%255c',
        ]
        
        path = request.path
        for pattern in traversal_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        
        return False
    
    def get_csp_policy(self):
        """Get Content Security Policy"""
        return "; ".join([
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://pagead2.googlesyndication.com https://www.googletagmanager.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self'",
            "media-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests"
        ])

class PaymentSecurityMiddleware(MiddlewareMixin):
    """Payment-specific security middleware"""
    
    def process_request(self, request):
        """Process payment-related requests"""
        
        # Check if this is a payment-related request
        if self.is_payment_request(request):
            # Validate payment session
            if not self.validate_payment_session(request):
                logger.warning(f'Invalid payment session from {self.get_client_ip(request)}')
                return HttpResponseForbidden('Invalid payment session')
            
            # Check payment rate limiting
            if not self.check_payment_rate_limit(request):
                logger.warning(f'Payment rate limit exceeded from {self.get_client_ip(request)}')
                return JsonResponse({'error': 'Payment rate limit exceeded'}, status=429)
        
        return None
    
    def is_payment_request(self, request):
        """Check if request is payment-related"""
        payment_paths = [
            '/process-payment/',
            '/place-order/',
            '/collect-phone/',
        ]
        
        return any(path in request.path for path in payment_paths)
    
    def validate_payment_session(self, request):
        """Validate payment session"""
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return False
        
        # Check if cart exists
        if not request.session.get('cart'):
            return False
        
        # Only require payment_method for place-order and process-payment, not collect-phone
        if request.path.startswith('/place-order/') or request.path.startswith('/process-payment/'):
            if not request.session.get('payment_method'):
                return False
        
        return True
    
    def check_payment_rate_limit(self, request):
        """No payment rate limiting (unlimited payments per hour)"""
        return True
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class LoggingMiddleware(MiddlewareMixin):
    """Logging middleware for security events"""
    
    def process_request(self, request):
        """Log request details"""
        if self.should_log_request(request):
            logger.info(f'Request: {request.method} {request.path} from {self.get_client_ip(request)}')
        
        return None
    
    def process_response(self, request, response):
        """Log response details"""
        if self.should_log_response(request, response):
            logger.info(f'Response: {response.status_code} for {request.method} {request.path}')
        
        return response
    
    def should_log_request(self, request):
        """Check if request should be logged"""
        sensitive_paths = [
            '/admin/',
            '/process-payment/',
            '/place-order/',
            '/college-admin/',
            '/canteen/',
        ]
        
        return any(path in request.path for path in sensitive_paths)
    
    def should_log_response(self, request, response):
        """Check if response should be logged"""
        return response.status_code >= 400 or self.should_log_request(request)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 