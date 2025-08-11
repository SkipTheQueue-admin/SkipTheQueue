"""
Security Configuration for SkipTheQueue
This file contains all security-related settings and utilities
"""

import re
import hashlib
import hmac
import json
import logging
import time
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.crypto import constant_time_compare
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)

# Security Constants
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT = 300  # 5 minutes
MAX_ORDER_RATE = 5  # orders per 5 minutes
MAX_API_REQUESTS = 60  # API requests per minute
PAYMENT_TIMEOUT = 900  # 15 minutes for payment completion

# Input Validation Patterns
PHONE_PATTERN = re.compile(r'^[0-9]{10,12}$')
SLUG_PATTERN = re.compile(r'^[a-z0-9-]+$')
PRICE_PATTERN = re.compile(r'^\d+(\.\d{1,2})?$')
NAME_PATTERN = re.compile(r'^[a-zA-Z\s]{2,50}$')

class SecurityValidator:
    """Enhanced security validation utilities"""
    
    @staticmethod
    def sanitize_input(text):
        """Sanitize user input to prevent XSS"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = strip_tags(str(text))
        
        # Remove potentially dangerous characters
        text = re.sub(r'[<>"\']', '', text)
        
        # Limit length
        if len(text) > 1000:
            text = text[:1000]
        
        return text.strip()
    
    @staticmethod
    def validate_phone_number(phone):
        """Validate phone number format"""
        if not phone:
            return False, "Phone number is required"
        
        phone = str(phone).strip()
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        # Check if it's a valid Indian phone number
        if len(digits_only) == 10 and digits_only.startswith(('6', '7', '8', '9')):
            return True, f"+91-{digits_only}"
        elif len(digits_only) == 12 and digits_only.startswith('91'):
            return True, f"+{digits_only}"
        elif len(digits_only) == 13 and digits_only.startswith('+91'):
            return True, digits_only
        else:
            return False, "Please enter a valid 10-digit Indian phone number"
    
    @staticmethod
    def validate_email_address(email):
        """Validate email address"""
        if not email:
            return False, "Email is required"
        
        try:
            validate_email(email)
            return True, email.lower()
        except ValidationError:
            return False, "Invalid email format"
    
    @staticmethod
    def validate_college_slug(slug):
        """Validate college slug"""
        if not slug:
            return False, "College code is required"
        
        if not SLUG_PATTERN.match(slug):
            return False, "College code must contain only lowercase letters, numbers, and hyphens"
        
        if len(slug) < 2 or len(slug) > 20:
            return False, "College code must be 2-20 characters long"
        
        return True, slug.lower()
    
    @staticmethod
    def validate_price(price):
        """Validate price amount"""
        if not price:
            return False, "Price is required"
        
        try:
            price_float = float(price)
            if price_float <= 0:
                return False, "Price must be greater than 0"
            if price_float > 10000:
                return False, "Price cannot exceed ₹10,000"
            return True, price_float
        except ValueError:
            return False, "Invalid price format"
    
    @staticmethod
    def validate_name(name):
        """Validate name fields"""
        if not name:
            return False, "Name is required"
        
        name_clean = SecurityValidator.sanitize_input(name)
        if len(name_clean) < 2 or len(name_clean) > 50:
            return False, "Name must be 2-50 characters long"
        
        if not NAME_PATTERN.match(name_clean):
            return False, "Name can only contain letters and spaces"
        
        return True, name_clean

    @staticmethod
    def validate_payment_data(data):
        """Validate payment data"""
        required_fields = ['amount', 'currency', 'order_id']
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0:
                return False, "Amount must be greater than 0"
        except (ValueError, TypeError):
            return False, "Invalid amount format"
        
        # Validate currency
        if data['currency'] not in ['INR']:
            return False, "Unsupported currency"
        
        return True, "Valid payment data"
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        try:
            validate_email(email)
            return True, "Valid email"
        except ValidationError:
            return False, "Invalid email format"
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Strong password"
    
    @staticmethod
    def generate_secure_token(data, secret_key=None):
        """Generate secure token for data verification"""
        if not secret_key:
            secret_key = settings.SECRET_KEY
        
        # Convert data to JSON string
        data_str = json.dumps(data, sort_keys=True)
        
        # Generate HMAC signature
        signature = hmac.new(
            secret_key.encode(),
            data_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def verify_secure_token(data, signature, secret_key=None):
        """Verify secure token"""
        if not secret_key:
            secret_key = settings.SECRET_KEY
        
        expected_signature = SecurityValidator.generate_secure_token(data, secret_key)
        return constant_time_compare(signature, expected_signature)

class PaymentSecurity:
    """Payment-related security utilities"""
    
    @staticmethod
    def generate_payment_id():
        """Generate secure payment ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def validate_payment_signature(data, signature, secret_key):
        """Verify payment signature"""
        try:
            expected_signature = hmac.new(
                secret_key.encode(),
                str(data).encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False
    
    @staticmethod
    def create_payment_signature(data, secret_key):
        """Create payment signature"""
        return hmac.new(
            secret_key.encode(),
            str(data).encode(),
            hashlib.sha256
        ).hexdigest()

class RateLimiter:
    """Rate limiting utilities"""
    
    @staticmethod
    def check_rate_limit(request, key_prefix, max_requests, window):
        """Check rate limit for a specific key"""
        key = f"rate_limit:{key_prefix}:{request.META.get('REMOTE_ADDR', 'unknown')}"
        
        # Get current count
        current_count = request.session.get(key, 0)
        
        # Check if window has expired
        last_request = request.session.get(f"{key}_time", 0)
        current_time = int(time.time())
        
        if current_time - last_request > window:
            current_count = 0
        
        # Check if limit exceeded
        if current_count >= max_requests:
            return False, "Rate limit exceeded"
        
        # Update count
        request.session[key] = current_count + 1
        request.session[f"{key}_time"] = current_time
        request.session.modified = True
        
        return True, "Rate limit OK"

class CSRFProtection:
    """CSRF protection utilities"""
    
    @staticmethod
    def validate_csrf_token(request):
        """Validate CSRF token"""
        if request.method == 'POST':
            csrf_token = request.POST.get('csrfmiddlewaretoken')
            if not csrf_token:
                return False
            # Django handles CSRF validation automatically
            return True
        return True

class SessionSecurity:
    """Session security utilities"""
    
    @staticmethod
    def secure_session_data(request, data):
        """Securely store session data"""
        for key, value in data.items():
            if isinstance(value, str):
                request.session[key] = SecurityValidator.sanitize_input(value)
            else:
                request.session[key] = value
    
    @staticmethod
    def clear_sensitive_session_data(request):
        """Clear sensitive session data"""
        sensitive_keys = ['user_phone', 'payment_method', 'cart', 'special_instructions']
        for key in sensitive_keys:
            request.session.pop(key, None)
    
    @staticmethod
    def validate_session_integrity(request):
        """Validate session integrity"""
        if not request.session.session_key:
            return False
        
        # Check if user is authenticated when required
        if request.path.startswith('/place-order/') or request.path.startswith('/process-payment/'):
            if not request.user.is_authenticated:
                return False
        
        return True

    @staticmethod
    def validate_session(request):
        """Validate session security"""
        # Skip validation for PWA files and static content
        if (request.path.startswith('/static/') or 
            request.path.startswith('/admin/') or
            request.path in ['/manifest.json', '/sw.js'] or
            request.path.startswith('/manifest.json') or
            request.path.startswith('/sw.js')):
            return True, "PWA/Static file - skipping session validation"
        
        # Allow anonymous users to browse without enforcing a session key
        # Strict session integrity is enforced only for authenticated users
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return True, "Anonymous user - session validation relaxed"

        # Check if session is valid
        if not request.session.session_key:
            return False, "No active session"
        
        # Check session age
        session_age = request.session.get('_session_age', 0)
        max_age = settings.SESSION_COOKIE_AGE
        
        if session_age > max_age:
            return False, "Session expired"
        
        return True, "Valid session"
    
    @staticmethod
    def update_session_security(request):
        """Update session security parameters"""
        # Skip for PWA files and static content
        if (request.path.startswith('/static/') or 
            request.path.startswith('/admin/') or
            request.path in ['/manifest.json', '/sw.js'] or
            request.path.startswith('/manifest.json') or
            request.path.startswith('/sw.js')):
            return
        
        # Update session age
        request.session['_session_age'] = request.session.get('_session_age', 0) + 1
        
        # Add security headers
        request.session['_security_hash'] = SecurityValidator.generate_secure_token({
            'user_id': request.user.id if request.user.is_authenticated else None,
            'ip': request.META.get('REMOTE_ADDR', ''),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')
        })
        
        request.session.modified = True

class InputSanitizer:
    """Input sanitization utilities"""
    
    @staticmethod
    def sanitize_order_data(data):
        """Sanitize order-related data"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = SecurityValidator.sanitize_input(value)
            else:
                sanitized[key] = value
        return sanitized
    
    @staticmethod
    def sanitize_menu_data(data):
        """Sanitize menu-related data"""
        sanitized = {}
        for key, value in data.items():
            if key in ['name', 'description', 'category']:
                sanitized[key] = SecurityValidator.sanitize_input(value)
            elif key == 'price':
                is_valid, price = SecurityValidator.validate_price(value)
                if is_valid:
                    sanitized[key] = price
                else:
                    raise ValidationError(price)
            else:
                sanitized[key] = value
        return sanitized
    
    @staticmethod
    def sanitize_html(text):
        """Sanitize HTML content"""
        if not text:
            return ""
        
        # Remove script tags and their content
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove other potentially dangerous tags
        dangerous_tags = ['iframe', 'object', 'embed', 'form', 'input', 'textarea', 'select']
        for tag in dangerous_tags:
            text = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(rf'<{tag}[^>]*/?>', '', text, flags=re.IGNORECASE)
        
        # Remove dangerous attributes
        dangerous_attrs = ['onclick', 'onload', 'onerror', 'onmouseover', 'javascript:']
        for attr in dangerous_attrs:
            text = re.sub(rf'{attr}="[^"]*"', '', text, flags=re.IGNORECASE)
            text = re.sub(rf'{attr}=\'[^\']*\'', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def sanitize_sql_input(text):
        """Sanitize input to prevent SQL injection"""
        if not text:
            return ""
        
        # Remove SQL injection patterns
        sql_patterns = [
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
            r'(\b(and|or)\b\s+\w+\s*<>)\s*null)',
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
        
        for pattern in sql_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()

# Security decorators
def require_secure_connection(view_func):
    """Require HTTPS connection"""
    def wrapper(request, *args, **kwargs):
        if not request.is_secure() and not settings.DEBUG:
            return JsonResponse({'error': 'HTTPS required'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

def validate_user_permission(view_func):
    """Validate user permissions"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

def log_security_event(event_type, user_id, details):
    """Log security events"""
    # In production, this would log to a security monitoring system
    print(f"SECURITY EVENT: {event_type} - User: {user_id} - Details: {details}")

# Security middleware utilities
def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def is_suspicious_request(request):
    """Check if request is suspicious"""
    suspicious_indicators = [
        'script' in request.path.lower(),
        'eval(' in str(request.POST),
        'javascript:' in str(request.POST),
        len(request.POST) > 1000,  # Too much data
    ]
    return any(suspicious_indicators) 