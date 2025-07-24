"""
Security Configuration for SkipTheQueue
This file contains all security-related settings and utilities
"""

import re
import hashlib
import hmac
import uuid
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

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
    """Comprehensive input validation and sanitization"""
    
    @staticmethod
    def sanitize_input(text):
        """Remove potentially dangerous characters"""
        if not text:
            return ""
        # Remove HTML tags and dangerous characters
        text = re.sub(r'[<>"\']', '', str(text))
        return text.strip()
    
    @staticmethod
    def validate_phone_number(phone):
        """Validate phone number format"""
        if not phone:
            return False, "Phone number is required"
        
        phone_clean = re.sub(r'\D', '', phone)
        if not PHONE_PATTERN.match(phone_clean):
            return False, "Phone number must be 10-12 digits"
        
        return True, phone_clean
    
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

class PaymentSecurity:
    """Payment-related security utilities"""
    
    @staticmethod
    def generate_payment_id():
        """Generate secure payment ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def validate_payment_data(data):
        """Validate payment data"""
        required_fields = ['amount', 'payment_method']
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate amount
        is_valid, amount = SecurityValidator.validate_price(data['amount'])
        if not is_valid:
            return False, amount
        
        # Validate payment method
        valid_methods = ['Online', 'Cash', 'UPI', 'Card', 'NetBanking']
        if data['payment_method'] not in valid_methods:
            return False, "Invalid payment method"
        
        return True, "Valid"
    
    @staticmethod
    def verify_payment_signature(data, signature, secret_key):
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
    def check_rate_limit(request, key, max_requests, window):
        """Check if request is within rate limit"""
        from django.utils import timezone
        now = timezone.now()
        request_key = f"{key}_{request.session.session_key}"
        
        request_count = request.session.get(request_key, 0)
        last_request = request.session.get(f"{request_key}_time")
        
        if last_request:
            time_diff = (now - last_request).seconds
            if time_diff > window:
                request_count = 0
        
        if request_count >= max_requests:
            return False
        
        request.session[request_key] = request_count + 1
        request.session[f"{request_key}_time"] = now
        
        return True

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