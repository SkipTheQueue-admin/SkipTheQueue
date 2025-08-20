from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import MenuItem, Order, OrderItem, College, Payment, UserProfile, CanteenStaff

from django.contrib import messages

from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.urls import reverse
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.conf import settings
from django.views.decorators.cache import never_cache, cache_page
from django.views.decorators.vary import vary_on_cookie
from django.core.cache import cache
from datetime import timedelta
import json
import uuid
import re
import hashlib
import hmac
from functools import wraps
import logging
from core.security import SecurityValidator, SessionSecurity
from core.error_handling import ErrorTracker, comprehensive_health_check, safe_view

logger = logging.getLogger(__name__)

# Performance optimization constants
CACHE_TIMEOUT = 300  # 5 minutes
MENU_CACHE_KEY = 'menu_items_{college_id}'
COLLEGE_CACHE_KEY = 'college_{college_slug}'
USER_PROFILE_CACHE_KEY = 'user_profile_{user_id}'

# Security decorators and utilities
def rate_limit(max_requests=10, window=60):
    """Rate limiting decorator - optimized for performance"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            # Use cache for rate limiting instead of session for better performance
            now = timezone.now()
            
            # Get user identifier (user ID if authenticated, IP if not)
            user_id = request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR', 'anonymous')
            
            # Create unique key for this user and view
            rate_key = f"rate_limit_{user_id}_{view_func.__name__}"
            
            # Use cache for rate limiting
            request_count = cache.get(rate_key, 0)
            
            if request_count >= max_requests:
                return JsonResponse({
                    'error': 'Rate limit exceeded. Please try again later.',
                    'retry_after': window
                }, status=429)
            
            # Increment counter with cache expiration
            cache.set(rate_key, request_count + 1, window)
            
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

def validate_phone_number(phone):
    """Validate phone number format"""
    is_valid, result = SecurityValidator.validate_phone_number(phone)
    return is_valid

def validate_payment_data(data):
    """Validate payment data"""
    return SecurityValidator.validate_payment_data(data)

def sanitize_input(text):
    """Sanitize user input"""
    return SecurityValidator.sanitize_input(text)

def verify_payment_signature(data, signature, secret_key):
    """Verify payment signature for security"""
    expected_signature = hmac.new(
        secret_key.encode(),
        json.dumps(data, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

def canteen_staff_required(view_func):
    """Decorator to check if user is canteen staff for the college - optimized"""
    @wraps(view_func)
    def wrapped(request, college_slug, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('custom_login')
        
        # Cache college lookup for better performance
        cache_key = COLLEGE_CACHE_KEY.format(college_slug=college_slug)
        college = cache.get(cache_key)
        
        if not college:
            try:
                college = College.objects.get(slug=college_slug)
                cache.set(cache_key, college, CACHE_TIMEOUT)
            except College.DoesNotExist:
                messages.error(request, "College not found.")
                return redirect('home')
        
        # Superuser can access any college
        if request.user.is_superuser:
            return view_func(request, college_slug, *args, **kwargs)
        
        # Check if user is canteen staff for this college
        try:
            canteen_staff = CanteenStaff.objects.filter(
                user=request.user,
                college=college,
                is_active=True
            ).first()
            
            if not canteen_staff:
                messages.error(request, "Access denied. You don't have permission to access this college's dashboard.")
                return redirect('home')
            
            return view_func(request, college_slug, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error checking canteen staff permissions: {e}")
            messages.error(request, "Access denied. You don't have permission to access this college's dashboard.")
            return redirect('home')
    
    return wrapped

@login_required(login_url='/login/?next=/collect-phone/')
@csrf_protect
def collect_phone(request):
    """Collect phone number for order with profile update - optimized"""
    
    def get_cart_context():
        """Helper function to get cart context data - optimized"""
        cart = request.session.get('cart', {})
        menu_items = []
        total = 0
        
        # Batch fetch menu items for better performance
        if cart:
            item_ids = list(cart.keys())
            items = MenuItem.objects.filter(id__in=item_ids, is_available=True)
            items_dict = {str(item.id): item for item in items}
            
            for item_id, quantity in cart.items():
                item = items_dict.get(item_id)
                if item:
                    item_total = item.price * quantity
                    menu_items.append({
                        'id': item.id,
                        'name': item.name,
                        'price': item.price,
                        'quantity': quantity,
                        'total': item_total
                    })
                    total += item_total
        
        # Get college information
        selected_college = request.session.get('selected_college')
        college = None
        if selected_college and isinstance(selected_college, dict) and 'id' in selected_college:
            try:
                college = College.objects.get(id=selected_college['id'])
            except College.DoesNotExist:
                pass
        
        return {
            'menu_items': menu_items,
            'total': total,
            'college': college
        }
    
    # Validate cart
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('menu')
    
    # Check if cart has valid items - optimized
    if cart:
        item_ids = list(cart.keys())
        valid_items = MenuItem.objects.filter(id__in=item_ids, is_available=True)
        
        if not valid_items.exists():
            messages.error(request, "No valid items in your cart.")
            return redirect('menu')
    
    if request.method == 'POST':
        phone = SecurityValidator.sanitize_input(request.POST.get('phone'))
        payment_method = request.POST.get('payment_method', 'Online')
        
        # Validate phone number
        is_valid, phone_result = SecurityValidator.validate_phone_number(phone)
        if not is_valid:
            messages.error(request, f"Please enter a valid phone number: {phone_result}")
            return render(request, 'orders/collect_phone.html', get_cart_context())
        
        try:
            # Save phone number to user profile
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            user_profile.phone_number = phone
            user_profile.save()
            
            # Store in session for order
            request.session['user_phone'] = phone
            request.session['payment_method'] = payment_method
            request.session.modified = True
            
            # Get special instructions if any
            special_instructions = sanitize_input(request.POST.get('special_instructions', ''))
            if special_instructions:
                request.session['special_instructions'] = special_instructions
            
            # Redirect to place order
            return redirect('place_order')
            
        except Exception as e:
            logger.error(f"Error saving user profile: {e}")
            messages.error(request, "An error occurred while saving your information. Please try again.")
            return render(request, 'orders/collect_phone.html', get_cart_context())
    
    # GET request: render form with context
    return render(request, 'orders/collect_phone.html', get_cart_context())

def test_collect_phone(request):
    """Test view to debug collect phone issues"""
    return render(request, 'orders/collect_phone.html', {
        'menu_items': [
            {
                'id': 1,
                'name': 'Test Item',
                'price': 100.00,
                'quantity': 2,
                'total': 200.00
            }
        ],
        'total': 200.00,
        'college': None
    })

def test_auth(request):
    """Test authentication status and user type"""
    if request.user.is_authenticated:
        user_email = request.user.email
        
        # Check user type
        user_type = "Regular User"
        redirect_url = None
        
        if user_email == 'skipthequeue.app@gmail.com':
            user_type = "Super Admin"
            redirect_url = '/super-admin/'
        else:
            try:
                canteen_staff = CanteenStaff.objects.get(user=request.user, is_active=True)
                user_type = f"Canteen Staff ({canteen_staff.college.name})"
                redirect_url = f'/canteen/dashboard/{canteen_staff.college.slug}/'
            except CanteenStaff.DoesNotExist:
                user_type = "Regular User"
                redirect_url = '/'
        
        return JsonResponse({
            'authenticated': True,
            'username': request.user.username,
            'email': user_email,
            'is_superuser': request.user.is_superuser,
            'is_staff': request.user.is_staff,
            'user_type': user_type,
            'redirect_url': redirect_url,
        })
    else:
        return JsonResponse({
            'authenticated': False,
            'username': None,
            'email': None,
            'is_superuser': False,
            'is_staff': False,
            'user_type': 'Not Authenticated',
            'redirect_url': '/login/',
        })

@csrf_exempt
@require_POST
def update_cart_api(request, item_id):
    """Enhanced cart update API with better error handling"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get cart from session
        cart = request.session.get('cart', {})
        if not isinstance(cart, dict):
            logger.warning('Cart session corrupted: not a dict')
            cart = {}
        
        # Convert all keys to strings for consistency
        cart = {str(k): v for k, v in cart.items()}
        
        action = request.POST.get('action')
        logger.info(f'Cart action: {action} for item {item_id}')
        
        # Get the menu item
        try:
            item = MenuItem.objects.get(id=item_id)
        except MenuItem.DoesNotExist:
            logger.error(f'Item {item_id} not found')
            return JsonResponse({'error': 'Item not found'}, status=404)
        
        item_id_str = str(item_id)
        
        if action == 'increase':
            if not item.is_available:
                logger.warning(f'{item.name} unavailable')
                return JsonResponse({'error': f'{item.name} is currently unavailable.'}, status=400)
            
            if item.is_stock_managed:
                current_quantity = cart.get(item_id_str, 0)
                if current_quantity >= item.stock_quantity:
                    logger.warning(f'Stock exceeded for {item.name}')
                    return JsonResponse({'error': f'Only {item.stock_quantity} {item.name} available in stock.'}, status=400)
            
            cart[item_id_str] = cart.get(item_id_str, 0) + 1
            
        elif action == 'decrease':
            current_quantity = cart.get(item_id_str, 0)
            if current_quantity > 1:
                cart[item_id_str] = current_quantity - 1
            else:
                cart.pop(item_id_str, None)
                
        elif action == 'remove':
            cart.pop(item_id_str, None)
            
        else:
            logger.error('Invalid action')
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        # Update session
        request.session['cart'] = cart
        request.session.modified = True
        
        # Calculate cart totals
        cart_items = []
        cart_total = 0
        
        for cart_item_id, quantity in cart.items():
            try:
                cart_item = MenuItem.objects.get(id=cart_item_id)
                cart_items.append({
                    'id': cart_item.id,
                    'name': cart_item.name,
                    'price': float(cart_item.price),
                    'quantity': quantity,
                    'total': float(cart_item.price * quantity)
                })
                cart_total += cart_item.price * quantity
            except MenuItem.DoesNotExist:
                # Remove invalid item from cart
                cart.pop(cart_item_id, None)
                continue
        
        # Update session again in case invalid items were removed
        request.session['cart'] = cart
        request.session.modified = True
        
        logger.info(f'Cart updated successfully: {cart}')
        
        return JsonResponse({
            'success': True,
            'cart_items': cart_items,
            'cart_total': float(cart_total),
            'cart_count': len(cart_items),
            'message': 'Cart updated successfully'
        })
        
    except Exception as e:
        logger.error(f'Cart update error: {str(e)}')
        # Reset cart on error
        request.session['cart'] = {}
        request.session.modified = True
        return JsonResponse({
            'error': 'Cart session error. Your cart was reset. Please try again.',
            'cart_items': [],
            'cart_total': 0.0,
            'cart_count': 0
        }, status=500)

@login_required(login_url='/login/?next=/place-order/')
@csrf_protect
def place_order(request):
    """Place order with payment processing and security"""
    cart = request.session.get('cart', {})
    selected_college = request.session.get('selected_college')

    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('menu')

    user_phone = request.session.get('user_phone')
    payment_method = request.session.get('payment_method', 'Online')
    
    if not user_phone:
        return redirect('collect_phone')

    # Validate cart items
    total_amount = 0
    order_items = []
    
    for item_id, quantity in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            if not item.is_available:
                messages.error(request, f"{item.name} is no longer available.")
                return redirect('view_cart')
            
            if item.is_stock_managed and quantity > item.stock_quantity:
                messages.error(request, f"Only {item.stock_quantity} {item.name} available in stock.")
                return redirect('view_cart')
            
            total_amount += item.price * quantity
            order_items.append((item, quantity))
        except MenuItem.DoesNotExist:
            messages.error(request, "Some items in your cart are no longer available.")
            return redirect('view_cart')

    # Create order
    college = None
    if selected_college:
        college = College.objects.get(id=selected_college['id'])

    try:
        order = Order.objects.create(
            user=request.user,
            user_name=request.user.get_full_name() or request.user.username,
            user_phone=user_phone,
            college=college,
            special_instructions=request.session.get('special_instructions', ''),
            payment_method=payment_method,
            estimated_time=college.estimated_preparation_time if college else 15
        )

        # Create order items and update stock
        for item, quantity in order_items:
            OrderItem.objects.create(
                order=order, 
                item=item, 
                quantity=quantity,
                price_at_time=item.price
            )
            
            # Update stock if managed
            if item.is_stock_managed:
                item.stock_quantity -= quantity
                item.save()
                
    except Exception as e:
        messages.error(request, "Error placing order. Please try again.")
        return redirect('view_cart')

    # Handle payment
    if payment_method == 'Online':
        order.status = 'Payment_Pending'
        order.save()
        return redirect('process_payment', order_id=order.id)
    else:
        # Cash payment - mark as paid
        order.status = 'Paid'
        order.payment_status = 'Paid'
        order.save()
        
        # Clear sensitive session data
        SessionSecurity.clear_sensitive_session_data(request)

        messages.success(request, f"Order #{order.id} placed successfully!")
        return redirect('order_success', order_id=order.id)

@cache_page(600)  # Cache for 10 minutes
def home(request):
    """Home page with auto-redirect based on user email and enhanced security - optimized for performance"""
    try:
        # Auto-redirect logic for logged-in users
        if request.user.is_authenticated:
            user_email = request.user.email
            
            # Check if user is the main admin (skipthequeue.app@gmail.com)
            if user_email == 'skipthequeue.app@gmail.com':
                if not request.user.is_superuser:
                    # Update user to superuser if they have the admin email
                    request.user.is_superuser = True
                    request.user.is_staff = True
                    request.user.save()
                # Store user type in session for consistent behavior
                request.session['user_type'] = 'super_admin'
                request.session['user_email'] = user_email
                return redirect('super_admin_dashboard')
            
            # Check if user is canteen staff for any college - optimized with select_related
            try:
                canteen_staff = CanteenStaff.objects.select_related('college').get(user=request.user, is_active=True)
                # Verify the college still exists and is active
                if canteen_staff.college and canteen_staff.college.is_active:
                    # Store user type and college info in session for consistent behavior
                    request.session['user_type'] = 'canteen_staff'
                    request.session['college_slug'] = canteen_staff.college.slug
                    request.session['college_name'] = canteen_staff.college.name
                    request.session['user_email'] = user_email
                    return redirect('canteen_staff_dashboard', college_slug=canteen_staff.college.slug)
                else:
                    # College is inactive or doesn't exist, log out the user
                    logout(request)
                    messages.error(request, "Your assigned college is no longer active. Please contact administrator.")
                    return redirect('home')
            except CanteenStaff.DoesNotExist:
                # Check if user is college admin
                try:
                    college_admin = College.objects.get(admin_email=user_email, is_active=True)
                    # Store user type and college info in session for consistent behavior
                    request.session['user_type'] = 'college_admin'
                    request.session['college_slug'] = college_admin.slug
                    request.session['college_name'] = college_admin.name
                    request.session['user_email'] = user_email
                    return redirect('college_admin_dashboard', college_slug=college_admin.slug)
                except College.DoesNotExist:
                    # Regular user - continue to normal home page
                    request.session['user_type'] = 'regular_user'
                    request.session['user_email'] = user_email
        
        # Get active colleges with optimized caching
        colleges_cache_key = 'active_colleges_home'
        colleges = cache.get(colleges_cache_key)
        
        if colleges is None:
            # Use select_related to optimize database queries
            colleges = list(College.objects.filter(is_active=True).select_related().order_by('name'))
            cache.set(colleges_cache_key, colleges, 1800)  # Cache for 30 minutes
        
        # Get selected college from session
        selected_college = request.session.get('selected_college')
        
        # Validate selected college still exists and is active
        if selected_college:
            try:
                college = College.objects.get(id=selected_college['id'], is_active=True)
                # Update session with current college data
                request.session['selected_college'] = {
                    'id': college.id,
                    'name': college.name,
                    'slug': college.slug
                }
            except College.DoesNotExist:
                # College no longer exists or is inactive, clear session
                request.session.pop('selected_college', None)
                selected_college = None
                messages.warning(request, "Your previously selected college is no longer available.")
        
        context = {
            'colleges': colleges,
            'selected_college': selected_college,
        }
        return render(request, 'orders/home.html', context)
        
    except Exception as e:
        logger.error(f"Error in home view: {str(e)}")
        # Return a simple error page instead of 500
        return render(request, 'orders/home.html', {
            'colleges': [],
            'selected_college': None,
            'error_message': 'An error occurred while loading the page. Please try again.'
        })

@never_cache
@vary_on_cookie
@cache_page(300)  # Cache for 5 minutes
def menu(request):
    """Menu page - requires college selection but not login - optimized for performance"""
    # Check if college is selected
    selected_college = request.session.get('selected_college')
    if not selected_college:
        messages.warning(request, "Please select a college first.")
        return redirect('home')
    
    try:
        college = College.objects.get(id=selected_college['id'], is_active=True)
    except College.DoesNotExist:
        # Clear invalid college from session
        request.session.pop('selected_college', None)
        messages.error(request, "Selected college is no longer available. Please select another college.")
        return redirect('home')
    
    # Get search query
    search_query = request.GET.get('search', '').strip()
    
    # Use cache for menu items if no search query
    cache_key = f'menu_items_{college.id}_{hash(search_query)}'
    menu_items = cache.get(cache_key)
    
    if menu_items is None:
        # Get menu items for the college with optimized query
        menu_items = MenuItem.objects.filter(
            college=college,
            is_available=True
        ).select_related('college').prefetch_related('favorited_by').order_by('category', 'name')
        
        # Apply search filter
        if search_query:
            menu_items = menu_items.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__icontains=search_query)
            )
        
        # Cache the result for 5 minutes
        cache.set(cache_key, menu_items, 300)
    
    # Get cart items for display - optimized
    cart = request.session.get('cart', {})
    cart_items = []
    cart_total = 0
    
    if cart:
        # Fetch all cart items in one query with select_related
        cart_item_ids = list(cart.keys())
        try:
            cart_items_data = MenuItem.objects.filter(id__in=cart_item_ids).select_related('college')
            cart_items_dict = {str(item.id): item for item in cart_items_data}
            
            for item_id, quantity in cart.items():
                item = cart_items_dict.get(item_id)
                if item:
                    cart_items.append({
                        'item': item,
                        'quantity': quantity,
                        'total': item.price * quantity
                    })
                    cart_total += item.price * quantity
        except Exception:
            pass
    
    # Get favorite items if user is logged in - optimized with caching
    favorite_items = []
    if request.user.is_authenticated:
        favorite_cache_key = f'favorites_{request.user.id}_{college.id}'
        favorite_items = cache.get(favorite_cache_key)
        
        if favorite_items is None:
            try:
                user_profile = UserProfile.objects.select_related('user').get(user=request.user)
                favorite_items = user_profile.favorite_items.filter(college=college).select_related('college')
                cache.set(favorite_cache_key, favorite_items, 300)
            except UserProfile.DoesNotExist:
                favorite_items = []
    
    # Get categories efficiently with caching
    categories_cache_key = f'categories_{college.id}'
    categories = cache.get(categories_cache_key)
    
    if categories is None:
        categories = menu_items.values_list('category', flat=True).distinct()
        cache.set(categories_cache_key, categories, 600)  # Cache categories for 10 minutes
    
    context = {
        'college': college,
        'menu_items': menu_items,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': len(cart_items),
        'search_query': search_query,
        'favorite_items': favorite_items,
        'categories': categories,
    }
    
    return render(request, 'orders/menu.html', context)

@never_cache
def order_success(request, order_id):
    """Enhanced order success page"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        return render(request, 'orders/order_success.html', {'order': order})
    except:
        messages.error(request, "Order not found.")
        return redirect('home')

@login_required(login_url='/login/?next=/register-college/')
@csrf_protect
def register_college(request):
    """College registration form with security - Only for super admins"""
    # Check if user is super admin
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Only administrators can register colleges.")
        return redirect('home')
    
    if request.method == 'POST':
        # Sanitize all inputs using SecurityValidator
        name = SecurityValidator.sanitize_input(request.POST.get('name'))
        slug = SecurityValidator.sanitize_input(request.POST.get('slug'))
        address = SecurityValidator.sanitize_input(request.POST.get('address'))
        admin_name = SecurityValidator.sanitize_input(request.POST.get('admin_name'))
        admin_email = SecurityValidator.sanitize_input(request.POST.get('admin_email'))
        admin_phone = SecurityValidator.sanitize_input(request.POST.get('admin_phone'))
        
        # Validate inputs
        if not name or len(name) < 3:
            messages.error(request, "College name must be at least 3 characters long.")
            return render(request, 'orders/register_college.html')
        
        if not slug or not re.match(r'^[a-z0-9-]+$', slug):
            messages.error(request, "College code must contain only lowercase letters, numbers, and hyphens.")
            return render(request, 'orders/register_college.html')
        
        if admin_email:
            try:
                validate_email(admin_email)
            except ValidationError:
                messages.error(request, "Please enter a valid email address.")
                return render(request, 'orders/register_college.html')
        
        if admin_phone:
            is_valid, phone_result = SecurityValidator.validate_phone_number(admin_phone)
            if not is_valid:
                messages.error(request, f"Please enter a valid phone number: {phone_result}")
                return render(request, 'orders/register_college.html')
        
        # Check if slug already exists
        if College.objects.filter(slug=slug).exists():
            messages.error(request, "College code already exists. Please choose a different one.")
            return render(request, 'orders/register_college.html')
        
        try:
            college = College.objects.create(
                name=name,
                slug=slug,
                address=address,
                admin_name=admin_name,
                admin_email=admin_email,
                admin_phone=admin_phone
            )
            messages.success(request, f"College '{college.name}' registered successfully!")
            return redirect('college_admin_dashboard', college_slug=college.slug)
        except Exception as e:
            messages.error(request, f"Error registering college. Please try again.")
            return render(request, 'orders/register_college.html')
    
    return render(request, 'orders/register_college.html')

@csrf_protect
def select_college(request, college_slug):
    """Select college via QR code or manual selection with memory"""
    try:
        college = College.objects.get(slug=college_slug, is_active=True)
        
        # Update session
        request.session['selected_college'] = {
            'id': college.id,
            'name': college.name,
            'slug': college.slug
        }
        
        # Update user profile if logged in
        if request.user.is_authenticated:
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            user_profile.last_login_college = college
            user_profile.save()
        
        messages.success(request, f"Welcome to {college.name}!")
        return redirect('menu')
    except College.DoesNotExist:
        messages.error(request, "College not found.")
        return redirect('home')

@never_cache
@csrf_protect
def add_to_cart(request, item_id):
    """Add item to cart - optimized for both logged in and anonymous users"""
    # Check if college is selected
    selected_college = request.session.get('selected_college')
    if not selected_college:
        messages.warning(request, "Please select a college first.")
        return redirect('home')
    
    try:
        item = MenuItem.objects.select_related('college').get(id=item_id)
        
        # Verify item belongs to selected college
        if item.college.id != selected_college['id']:
            messages.error(request, "Item not available for selected college.")
            return redirect('menu')
        
        # Check if item is available
        if not item.is_available:
            messages.error(request, f"{item.name} is currently unavailable.")
            return redirect('menu')
        
        # Check stock
        if item.is_stock_managed and item.stock_quantity <= 0:
            messages.error(request, f"{item.name} is out of stock.")
            return redirect('menu')
        
    except MenuItem.DoesNotExist:
        messages.error(request, "Item not found.")
        return redirect('menu')
    
    # Add to cart
    cart = request.session.get('cart', {})
    item_id_str = str(item_id)
    
    if item_id_str in cart:
        cart[item_id_str] += 1
    else:
        cart[item_id_str] = 1
    
    # Update stock if managed
    if item.is_stock_managed:
        item.stock_quantity = max(0, item.stock_quantity - 1)
        item.save()
    
    request.session['cart'] = cart
    request.session.modified = True
    
    # Return JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_items = []
        cart_total = 0
        
        for cart_item_id, quantity in cart.items():
            try:
                cart_item = MenuItem.objects.get(id=cart_item_id)
                cart_items.append({
                    'id': cart_item.id,
                    'name': cart_item.name,
                    'price': float(cart_item.price),
                    'quantity': quantity,
                    'total': float(cart_item.price * quantity)
                })
                cart_total += cart_item.price * quantity
            except MenuItem.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'message': f"{item.name} added to cart!",
            'cart_count': len(cart_items),
            'cart_total': float(cart_total),
            'cart_items': cart_items
        })
    
    messages.success(request, f"{item.name} added to cart!")
    return redirect('menu')

@never_cache
@ensure_csrf_cookie
@csrf_protect
def view_cart(request):
    """Enhanced cart with payment options - optimized for performance"""
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    selected_college = request.session.get('selected_college')

    if not cart:
        return render(request, 'orders/cart.html', {
            'cart_items': [],
            'total': 0,
            'college': None,
            'user_authenticated': request.user.is_authenticated
        })

    # Optimize database queries by fetching all items at once
    item_ids = list(cart.keys())
    try:
        items = MenuItem.objects.filter(id__in=item_ids).select_related('college')
        items_dict = {str(item.id): item for item in items}
    except Exception:
        items_dict = {}

    # Clean up invalid items from cart
    items_to_remove = []
    for item_id, quantity in cart.items():
        item = items_dict.get(item_id)
        if not item:
            items_to_remove.append(item_id)
            continue
            
        # Check if item is still available
        if not item.is_available:
            items_to_remove.append(item_id)
            continue
            
        # Check stock
        if item.is_stock_managed and quantity > item.stock_quantity:
            # Adjust quantity to available stock
            quantity = item.stock_quantity
            cart[item_id] = quantity
            if quantity <= 0:
                items_to_remove.append(item_id)
                continue
                
        item_total = item.price * quantity
        total += item_total
        cart_items.append({
            'item': item,
            'quantity': quantity,
            'total': item_total,
        })

    # Remove invalid items from cart
    for item_id in items_to_remove:
        del cart[item_id]
        
    # Update session if items were removed
    if items_to_remove:
        request.session['cart'] = cart
        request.session.modified = True
        if len(items_to_remove) == 1:
            messages.warning(request, "One item was removed from your cart as it's no longer available.")
        elif len(items_to_remove) > 1:
            messages.warning(request, f"{len(items_to_remove)} items were removed from your cart as they're no longer available.")

    # Get college info efficiently
    college = None
    if selected_college and isinstance(selected_college, dict) and 'id' in selected_college:
        try:
            college = College.objects.get(id=selected_college['id'])
        except College.DoesNotExist:
            pass

    return render(request, 'orders/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'college': college,
        'user_authenticated': request.user.is_authenticated
    })

@require_POST
@csrf_protect
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart = request.session.get('cart', {})
    if str(item_id) in cart:
        del cart[str(item_id)]
        request.session['cart'] = cart
        messages.success(request, "Item removed from cart!")
    return redirect('view_cart')

@require_POST
@csrf_protect
def update_cart(request, item_id):
    """Form-friendly cart update that redirects back to cart page"""
    action = request.POST.get('action')
    cart = request.session.get('cart', {})
    item_id_str = str(item_id)

    try:
        item = MenuItem.objects.get(id=item_id)
    except MenuItem.DoesNotExist:
        messages.error(request, "Item not found.")
        return redirect('view_cart')

    current_quantity = int(cart.get(item_id_str, 0))

    if action == 'increase':
        if not item.is_available:
            messages.error(request, f"{item.name} is currently unavailable.")
            return redirect('view_cart')
        if item.is_stock_managed and current_quantity >= item.stock_quantity:
            messages.warning(request, f"Only {item.stock_quantity} {item.name} available in stock.")
            return redirect('view_cart')
        cart[item_id_str] = current_quantity + 1
        messages.success(request, f"Added one more {item.name}.")
    elif action == 'decrease':
        if current_quantity > 1:
            cart[item_id_str] = current_quantity - 1
            messages.info(request, f"Decreased quantity for {item.name}.")
        else:
            cart.pop(item_id_str, None)
            messages.info(request, f"Removed {item.name} from cart.")
    elif action == 'remove':
        cart.pop(item_id_str, None)
        messages.info(request, f"Removed {item.name} from cart.")
    else:
        messages.error(request, "Invalid action.")
        return redirect('view_cart')

    request.session['cart'] = cart
    request.session.modified = True
    return redirect('view_cart')

@login_required(login_url='/admin/login/')
@never_cache
@canteen_staff_required
def canteen_dashboard(request, college_slug):
    """Canteen dashboard for staff with proper access control"""
    try:
        college = get_object_or_404(College, slug=college_slug)
        orders = Order.objects.filter(
            college=college,
            status__in=['Paid', 'In Progress', 'Ready']
        ).order_by('-created_at')
        
        return render(request, 'orders/canteen_dashboard.html', {
            'college': college,
            'orders': orders
        })
    except Exception as e:
        messages.error(request, "Error loading dashboard.")
        return redirect('home')

@login_required(login_url='/admin/login/')
@require_POST
@csrf_protect
@canteen_staff_required
def accept_order(request, college_slug, order_id):
    """Accept order with proper access control"""
    try:
        order = get_object_or_404(Order, id=order_id, college__slug=college_slug)
        order.status = "In Progress"
        order.save()
        messages.success(request, f"Order #{order.id} accepted!")
        return redirect('canteen_dashboard', college_slug=college_slug)
    except Exception as e:
        messages.error(request, "Error accepting order.")
        return redirect('canteen_dashboard', college_slug=college_slug)

@login_required(login_url='/admin/login/')
@require_POST
@csrf_protect
@canteen_staff_required
def decline_order(request, college_slug, order_id):
    """Decline order with proper access control"""
    try:
        order = get_object_or_404(Order, id=order_id, college__slug=college_slug)
        order.status = "Declined"
        order.save()
        messages.success(request, f"Order #{order.id} declined!")
        return redirect('canteen_dashboard', college_slug=college_slug)
    except Exception as e:
        messages.error(request, "Error declining order.")
        return redirect('canteen_dashboard', college_slug=college_slug)

def custom_login(request):
    """Custom login view that handles redirects after OAuth or email login"""
    next_url = request.GET.get('next', '/')
    
    # Store the next URL in session for after login
    request.session['next_url'] = next_url
    
    # Check if OAuth is configured
    from django.conf import settings
    if hasattr(settings, 'SOCIAL_AUTH_GOOGLE_OAUTH2_KEY') and settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
        # Redirect to Google OAuth
        return redirect('social:begin', backend='google-oauth2')
    else:
        # Fallback to email login form
        if request.method == 'POST':
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            if email and password:
                # Use the custom authentication backend
                from django.contrib.auth import authenticate, login
                user = authenticate(request, username=email, password=password)
                
                if user is not None:
                    login(request, user)
                    # Redirect to oauth_complete to handle user type routing
                    return redirect('oauth_complete')
                else:
                    messages.error(request, 'Invalid email or password.')
            else:
                messages.error(request, 'Please provide both email and password.')
        
        return render(request, 'orders/login.html', {'next': next_url})

def oauth_complete(request):
    """Handle redirect after successful OAuth login with proper user type routing"""
    if request.user.is_authenticated:
        user_email = request.user.email
        
        # Check if user is the main admin (skipthequeue.app@gmail.com)
        if user_email == 'skipthequeue.app@gmail.com':
            if not request.user.is_superuser:
                # Update user to superuser if they have the admin email
                request.user.is_superuser = True
                request.user.is_staff = True
                request.user.save()
            # Store user type in session for consistent behavior
            request.session['user_type'] = 'super_admin'
            request.session['user_email'] = user_email
            return redirect('super_admin_dashboard')
        
        # Check if user is canteen staff for any college
        try:
            canteen_staff = CanteenStaff.objects.get(user=request.user, is_active=True)
            # Store user type and college info in session
            request.session['user_type'] = 'canteen_staff'
            request.session['college_slug'] = canteen_staff.college.slug
            request.session['college_name'] = canteen_staff.college.name
            request.session['user_email'] = user_email
            # Redirect to canteen staff dashboard
            return redirect('canteen_staff_dashboard', college_slug=canteen_staff.college.slug)
        except CanteenStaff.DoesNotExist:
            # Check if user is a college admin
            try:
                college = College.objects.get(admin_email=user_email, is_active=True)
                # Store user type and college info in session
                request.session['user_type'] = 'college_admin'
                request.session['college_slug'] = college.slug
                request.session['college_name'] = college.name
                request.session['user_email'] = user_email
                # Redirect to college admin dashboard
                return redirect('college_admin_dashboard', college_slug=college.slug)
            except College.DoesNotExist:
                # Regular user - check if they need to collect phone
                next_url = request.session.get('next_url', '/')
                request.session.pop('next_url', None)
                
                # Store user type in session
                request.session['user_type'] = 'regular_user'
                request.session['user_email'] = user_email
                
                # Check if user has phone number in profile
                try:
                    user_profile = UserProfile.objects.get(user=request.user)
                    if user_profile.phone_number:
                        request.session['user_phone'] = user_profile.phone_number
                        # User has phone, go to intended page or home
                        if next_url and next_url != '/':
                            return redirect(next_url)
                        return redirect('home')
                    else:
                        # User doesn't have phone number, redirect to collect_phone
                        return redirect('collect_phone')
                except UserProfile.DoesNotExist:
                    # User profile doesn't exist, redirect to collect_phone
                    return redirect('collect_phone')
    
    # If not authenticated, redirect to home
    return redirect('home')

def custom_logout(request):
    """Custom logout with session cleanup"""
    request.session.pop('selected_college', None)
    logout(request)
    return redirect('home')

# API Views for real-time updates with security
@login_required(login_url='/admin/login/')
@require_GET
def get_orders_json(request, college_slug):
    """API endpoint for real-time order updates with security"""
    # Check if user is superuser
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied. Super admin privileges required.'}, status=403)
    
    try:
        college = get_object_or_404(College, slug=college_slug)
        orders = Order.objects.filter(college=college).order_by('-created_at')[:20]
        
        orders_data = []
        for order in orders:
            orders_data.append({
                'id': order.id,
                'user_name': order.user_name,
                'user_phone': order.user_phone,
                'status': order.status,
                'status_color': order.get_status_color(),
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
                'total_price': float(order.total_price()),
                'payment_method': order.payment_method,
                'items': [
                    {
                        'name': item.item.name,
                        'quantity': item.quantity,
                        'price': float(item.price_at_time)
                    } for item in order.order_items.all()
                ]
            })
        
        return JsonResponse({'orders': orders_data})
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)

# College Admin Views with security
@login_required(login_url='/admin/login/')
@csrf_protect
def college_admin_dashboard(request, college_slug):
    """College admin dashboard for managing menu and orders"""
    # Check if user is superuser or college admin
    if not request.user.is_superuser:
        # Check if user is the college admin for this college
        try:
            college = College.objects.get(slug=college_slug, admin_email=request.user.email, is_active=True)
            # Store user type and college info in session for consistent behavior
            request.session['user_type'] = 'college_admin'
            request.session['college_slug'] = college.slug
            request.session['college_name'] = college.name
            request.session['user_email'] = request.user.email
        except College.DoesNotExist:
            messages.error(request, "Access denied. You don't have permission to access this college's dashboard.")
            return redirect('home')
    else:
        # Superuser - store user type in session
        request.session['user_type'] = 'super_admin'
        request.session['user_email'] = request.user.email
    
    try:
        college = get_object_or_404(College, slug=college_slug)
        orders = Order.objects.filter(college=college).order_by('-created_at')
        
        # Get status counts for analytics
        status_counts = orders.values('status').annotate(count=Count('status'))
        
        # Get recent orders (last 24 hours)
        recent_orders = orders.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        )
        
        # Get pending orders
        pending_orders = orders.filter(status__in=['Pending', 'Payment_Pending', 'Paid'])
        
        context = {
            'college': college,
            'orders': orders[:50],  # Limit to 50 most recent
            'status_counts': status_counts,
            'recent_orders': recent_orders.count(),
            'pending_orders': pending_orders.count(),
            'total_orders': orders.count()
        }
        
        return render(request, 'orders/college_admin_dashboard.html', context)
    except Exception as e:
        messages.error(request, "Error loading dashboard.")
        return redirect('home')

@login_required(login_url='/admin/login/')
@csrf_protect
def manage_menu(request, college_slug):
    """Manage college menu items with security"""
    # Check if user is superuser or college admin
    if not request.user.is_superuser:
        # Check if user is the college admin for this college
        try:
            college = College.objects.get(slug=college_slug, admin_email=request.user.email, is_active=True)
            # Store user type and college info in session for consistent behavior
            request.session['user_type'] = 'college_admin'
            request.session['college_slug'] = college.slug
            request.session['college_name'] = college.name
            request.session['user_email'] = request.user.email
        except College.DoesNotExist:
            messages.error(request, "Access denied. You don't have permission to manage this college's menu.")
            return redirect('home')
    else:
        # Superuser - store user type in session
        request.session['user_type'] = 'super_admin'
        request.session['user_email'] = request.user.email
    
    try:
        college = get_object_or_404(College, slug=college_slug)
        
        if request.method == 'POST':
            action = sanitize_input(request.POST.get('action'))
            item_id = request.POST.get('item_id')
            
            if action == 'toggle_availability' and item_id:
                item = get_object_or_404(MenuItem, id=item_id, college=college)
                item.is_available = not item.is_available
                item.save()
                messages.success(request, f"{item.name} availability updated!")
                
            elif action == 'delete_item' and item_id:
                item = get_object_or_404(MenuItem, id=item_id, college=college)
                item.delete()
                messages.success(request, f"{item.name} deleted from menu!")
                
            elif action == 'add_item':
                name = sanitize_input(request.POST.get('name'))
                description = sanitize_input(request.POST.get('description', ''))
                price = request.POST.get('price')
                category = sanitize_input(request.POST.get('category', 'General'))
                
                if name and price:
                    try:
                        price_float = float(price)
                        if price_float <= 0:
                            raise ValueError("Price must be positive")
                    except ValueError:
                        messages.error(request, "Please enter a valid price.")
                        return redirect('manage_menu', college_slug=college_slug)
                    
                    MenuItem.objects.create(
                        name=name,
                        description=description,
                        price=price_float,
                        category=category,
                        college=college
                    )
                    messages.success(request, f"{name} added to menu!")
                else:
                    messages.error(request, "Please fill all required fields.")
        
        menu_items = MenuItem.objects.filter(college=college).order_by('category', 'name')
        categories = {}
        for item in menu_items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)
        
        return render(request, 'orders/manage_menu.html', {
            'college': college,
            'categories': categories
        })
    except Exception as e:
        messages.error(request, "Error managing menu.")
        return redirect('home')

@login_required(login_url='/login/?next=/process-payment/')
@csrf_protect
def process_payment(request, order_id):
    """Process online payment with enhanced security"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Security checks
        if order.status != 'Payment_Pending':
            messages.error(request, "Invalid payment status.")
            return redirect('view_cart')
        
        # Check payment timeout
        payment_timeout = getattr(settings, 'PAYMENT_TIMEOUT', 900)  # 15 minutes
        if (timezone.now() - order.created_at).seconds > payment_timeout:
            order.status = 'Cancelled'
            order.save()
            messages.error(request, "Payment session expired.")
            return redirect('view_cart')
        
        # Validate order amount
        max_amount = getattr(settings, 'MAX_ORDER_AMOUNT', 10000)
        if order.total_price() > max_amount:
            messages.error(request, f"Order amount exceeds maximum limit of ₹{max_amount:,}.")
            return redirect('view_cart')
        
        if request.method == 'POST':
            # Sanitize and validate payment data
            payment_data = {
                'amount': request.POST.get('amount'),
                'payment_method': request.POST.get('payment_method', 'Online'),
                'payment_gateway': request.POST.get('payment_gateway', 'razorpay'),
            }
            
            # Validate payment data
            is_valid, message = validate_payment_data(payment_data)
            if not is_valid:
                messages.error(request, message)
                return render(request, 'orders/process_payment.html', {'order': order})
            
            # Verify amount matches order
            if float(payment_data['amount']) != float(order.total_price()):
                logger.warning(f'Payment amount mismatch: expected {order.total_price()}, got {payment_data["amount"]}')
                messages.error(request, "Payment amount mismatch.")
                return render(request, 'orders/process_payment.html', {'order': order})
            
            # Validate payment gateway
            valid_gateways = ['razorpay', 'paytm', 'stripe', 'paypal']
            if payment_data['payment_gateway'] not in valid_gateways:
                messages.error(request, "Invalid payment gateway.")
                return render(request, 'orders/process_payment.html', {'order': order})
            
            # Simulate secure payment processing
            try:
                # Generate secure payment ID
                payment_id = str(uuid.uuid4())
                
                # Create payment signature for verification
                payment_secret = getattr(settings, 'PAYMENT_SECRET_KEY', 'default-secret-key')
                payment_signature = hmac.new(
                    payment_secret.encode(),
                    f"{order.id}:{payment_data['amount']}:{payment_id}".encode(),
                    hashlib.sha256
                ).hexdigest()
                
                # Update order with payment details
                order.payment_status = 'Paid'
                order.payment_id = payment_id
                order.payment_signature = payment_signature
                order.status = 'Paid'
                order.amount_paid = order.total_price()
                order.payment_method = payment_data['payment_method']
                order.payment_gateway = payment_data['payment_gateway']
                order.payment_completed_at = timezone.now()
                order.save()
                
                # Create payment record
                Payment.objects.create(
                    order=order,
                    amount=order.total_price(),
                    payment_method=payment_data['payment_method'],
                    payment_gateway=payment_data['payment_gateway'],
                    transaction_id=payment_id,
                    signature=payment_signature,
                    status='Completed',
                    completed_at=timezone.now()
                )
                
                # Log successful payment
                logger.info(f'Payment successful: Order #{order.id}, Amount: ₹{order.total_price()}, Gateway: {payment_data["payment_gateway"]}')
                
                # Clear sensitive session data
                SessionSecurity.clear_sensitive_session_data(request)

                messages.success(request, f"✅ Payment successful! Order #{order.id} confirmed.")
                return redirect('order_success', order_id=order.id)
                
            except Exception as e:
                logger.error(f'Payment processing error: {str(e)}')
                messages.error(request, "Payment processing failed. Please try again.")
                return render(request, 'orders/process_payment.html', {'order': order})
        
        return render(request, 'orders/process_payment.html', {'order': order})
        
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('view_cart')
    except Exception as e:
        logger.error(f'Payment view error: {str(e)}')
        messages.error(request, "Error processing payment. Please try again.")
        return redirect('view_cart')

@login_required(login_url='/login/?next=/order-history/')
@never_cache
def order_history(request):
    """Enhanced order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate total spent
    total_spent = sum(order.total_price() for order in orders if order.status == 'Completed')
    
    return render(request, 'orders/order_history.html', {
        'orders': orders,
        'total_spent': total_spent
    })

@never_cache
def track_order(request):
    """Enhanced order tracking with validation"""
    phone = SecurityValidator.sanitize_input(request.GET.get('phone'))
    order_id = request.GET.get('order_id')
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            return render(request, 'orders/track_order.html', {'order': order})
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
    
    elif phone:
        is_valid, phone_result = SecurityValidator.validate_phone_number(phone)
        if not is_valid:
            messages.error(request, f"Please enter a valid phone number: {phone_result}")
            return render(request, 'orders/track_order.html')
        
        orders = Order.objects.filter(user_phone=phone).order_by('-created_at')
        return render(request, 'orders/track_order.html', {'orders': orders})
    
    return render(request, 'orders/track_order.html')

# PWA Manifest view
def pwa_manifest(request):
    """Serve PWA manifest file"""
    from django.conf import settings
    import os
    
    # Try to read the static manifest file
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/manifest+json')
    else:
        # Fallback manifest if file doesn't exist
        manifest = {
            "name": "SkipTheQueue - Smart Canteen Ordering",
            "short_name": "SkipTheQueue",
            "description": "Order food from your college canteen and skip the queues",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#3B82F6",
            "orientation": "portrait-primary",
            "icons": [
                {
                    "src": "/static/images/icon-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "/static/images/icon-512x512.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ]
        }
        return JsonResponse(manifest, content_type='application/manifest+json')

def pwa_service_worker(request):
    """Serve PWA service worker"""
    from django.conf import settings
    import os
    
    # Try to read the service worker file
    sw_path = os.path.join(settings.STATIC_ROOT, 'sw.js')
    if not os.path.exists(sw_path):
        sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    
    if os.path.exists(sw_path):
        with open(sw_path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/javascript')
    else:
        # Return a basic service worker if file doesn't exist
        basic_sw = """
        self.addEventListener('install', function(event) {
            console.log('Service Worker installed');
        });

        self.addEventListener('fetch', function(event) {
            event.respondWith(fetch(event.request));
        });
        """
        return HttpResponse(basic_sw, content_type='application/javascript')

@login_required(login_url='/admin/login/')
@require_POST
@csrf_protect
def update_order_status(request, college_slug, order_id):
    """Update order status with enhanced security and notifications"""
    try:
        college = get_object_or_404(College, slug=college_slug)
        order = get_object_or_404(Order, id=order_id, college=college)
        new_status = request.POST.get('status')
        
        # Check permissions
        try:
            canteen_staff = CanteenStaff.objects.get(
                user=request.user, 
                college=college, 
                is_active=True,
                can_update_status=True
            )
        except CanteenStaff.DoesNotExist:
            if not request.user.is_superuser:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if new_status in ['In Progress', 'Ready', 'Completed']:
            old_status = order.status
            order.status = new_status
            order.save()
            
            # Prepare comprehensive notification data for user
            notification_data = {
                'success': True, 
                'message': f'Order #{order.id} status updated to {new_status}!',
                'order_id': order.id,
                'new_status': new_status,
                'old_status': old_status,
                'user_name': order.user_name,
                'college_name': college.name,
                'timestamp': timezone.now().isoformat(),
                'requires_user_action': False,
                'requires_notification': True
            }
            
            # Add specific notification for ready status - requires user action
            if new_status == 'Ready':
                notification_data['user_notification'] = {
                    'title': '🎉 Order Ready for Pickup!',
                    'message': f'Your order #{order.id} is ready for pickup at {college.name}. Please collect it from the canteen.',
                    'type': 'success',
                    'persistent': True,  # This notification won't auto-dismiss
                    'action_required': True,
                    'order_id': order.id,
                    'college_name': college.name
                }
                notification_data['requires_user_action'] = True
                notification_data['status_color'] = 'status-ready'
            elif new_status == 'In Progress':
                notification_data['user_notification'] = {
                    'title': '👨‍🍳 Order Being Prepared',
                    'message': f'Your order #{order.id} is being prepared at {college.name}. We\'ll notify you when it\'s ready!',
                    'type': 'info',
                    'persistent': False,
                    'action_required': False,
                    'order_id': order.id,
                    'college_name': college.name
                }
                notification_data['status_color'] = 'status-preparing'
            elif new_status == 'Completed':
                notification_data['user_notification'] = {
                    'title': '✅ Order Completed',
                    'message': f'Your order #{order.id} has been completed. Thank you for using SkipTheQueue!',
                    'type': 'success',
                    'persistent': False,
                    'action_required': False,
                    'order_id': order.id,
                    'college_name': college.name
                }
                notification_data['status_color'] = 'status-completed'
            
            # Store notification in session for the user to see
            if order.user_phone:
                # Create a session key for this user's notifications
                notification_key = f'order_notification_{order.user_phone}_{order.id}'
                request.session[notification_key] = notification_data
                
                # Also store in a general user notification key for easier retrieval
                user_notification_key = f'user_notification_{order.user_phone}_{order.id}'
                request.session[user_notification_key] = notification_data.get('user_notification', {})
                
                # Store the order in user's active orders for real-time tracking
                active_orders_key = f'active_orders_{order.user_phone}'
                active_orders = request.session.get(active_orders_key, [])
                if order.id not in active_orders:
                    active_orders.append(order.id)
                    request.session[active_orders_key] = active_orders
                
                # Store notification in a global notifications list for real-time access
                global_notifications_key = 'global_notifications'
                global_notifications = request.session.get(global_notifications_key, [])
                global_notifications.append({
                    'user_phone': order.user_phone,
                    'order_id': order.id,
                    'notification': notification_data,
                    'timestamp': timezone.now().isoformat()
                })
                request.session[global_notifications_key] = global_notifications
                
                # Store persistent notification for ready orders that won't auto-dismiss
                if new_status == 'Ready':
                    persistent_key = f'persistent_notification_{order.user_phone}_{order.id}'
                    request.session[persistent_key] = {
                        'type': 'order_ready',
                        'title': '🎉 Order Ready for Pickup!',
                        'message': f'Your order #{order.id} is ready for pickup at {college.name}. Please collect it from the canteen.',
                        'order_id': order.id,
                        'college_name': college.name,
                        'timestamp': timezone.now().isoformat(),
                        'persistent': True,
                        'requires_action': True
                    }
                    
                    # Also store in a user-specific persistent notifications list
                    user_persistent_key = f'user_persistent_notifications_{order.user_phone}'
                    user_persistent = request.session.get(user_persistent_key, [])
                    user_persistent.append({
                        'order_id': order.id,
                        'type': 'order_ready',
                        'title': '🎉 Order Ready for Pickup!',
                        'message': f'Your order #{order.id} is ready for pickup at {college.name}. Please collect it from the canteen.',
                        'college_name': college.name,
                        'timestamp': timezone.now().isoformat(),
                        'persistent': True,
                        'requires_action': True
                    })
                    request.session[user_persistent_key] = user_persistent
            
            return JsonResponse(notification_data)
        else:
            return JsonResponse({'error': 'Invalid status'}, status=400)
            
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}")
        return JsonResponse({'error': 'Error updating order status'}, status=500)

def help_center(request):
    """Help center page"""
    return render(request, 'orders/help_center.html')

def privacy_policy(request):
    """Privacy policy page"""
    return render(request, 'orders/privacy_policy.html')

def terms_of_service(request):
    """Terms of service page"""
    return render(request, 'orders/terms_of_service.html')

def is_superuser(user):
    return user.is_superuser

def is_canteen_staff(user, college):
    from orders.models import CanteenStaff
    return CanteenStaff.objects.filter(user=user, college=college, is_active=True).exists()

@user_passes_test(is_superuser, login_url='canteen_staff_login')
def super_admin_dashboard(request):
    """Super admin dashboard for managing all colleges and orders with comprehensive monitoring"""
    # Check if user is superuser
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super admin privileges required.")
        return redirect('home')
    
    # Store user type in session for consistent behavior
    request.session['user_type'] = 'super_admin'
    request.session['user_email'] = request.user.email
    
    from datetime import datetime, timedelta
    import json
    
    # Get date filters
    today = timezone.now().date()
    selected_date = request.GET.get('date', today.strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except:
        selected_date = today
    
    # Get all colleges
    colleges = College.objects.all().order_by('name')
    
    # Get comprehensive statistics
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='Pending').count()
    completed_orders = Order.objects.filter(status='Completed').count()
    total_revenue = sum(order.total_price() for order in Order.objects.filter(status='Completed'))
    
    # Today's statistics
    today_orders = Order.objects.filter(created_at__date=today).count()
    today_revenue = sum(order.total_price() for order in Order.objects.filter(created_at__date=today, status='Completed'))
    
    # Selected date statistics
    date_orders = Order.objects.filter(created_at__date=selected_date).count()
    date_revenue = sum(order.total_price() for order in Order.objects.filter(created_at__date=selected_date, status='Completed'))
    
    # User statistics
    total_users = User.objects.count()
    active_users_today = User.objects.filter(last_login__date=today).count()
    active_users_date = User.objects.filter(last_login__date=selected_date).count()
    
    # College statistics
    active_colleges = College.objects.filter(is_active=True).count()
    total_menu_items = MenuItem.objects.count()
    
    # Real-time orders (last 24 hours)
    recent_orders = Order.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-created_at')
    
    # Orders by college for selected date
    college_orders = {}
    for college in colleges:
        college_orders[college.name] = {
            'total': Order.objects.filter(college=college).count(),
            'today': Order.objects.filter(college=college, created_at__date=today).count(),
            'selected_date': Order.objects.filter(college=college, created_at__date=selected_date).count(),
            'revenue': sum(order.total_price() for order in Order.objects.filter(college=college, status='Completed')),
            'pending': Order.objects.filter(college=college, status='Pending').count(),
        }
    
    # Monthly statistics for charts
    monthly_data = []
    for i in range(12):
        month_date = today - timedelta(days=30*i)
        month_orders = Order.objects.filter(created_at__month=month_date.month, created_at__year=month_date.year).count()
        month_revenue = sum(order.total_price() for order in Order.objects.filter(
            created_at__month=month_date.month, 
            created_at__year=month_date.year, 
            status='Completed'
        ))
        monthly_data.append({
            'month': month_date.strftime('%B %Y'),
            'orders': month_orders,
            'revenue': float(month_revenue)
        })
    
    # User phone numbers (for admin access)
    users_with_phones = UserProfile.objects.select_related('user').filter(phone_number__isnull=False).order_by('-updated_at')
    
    context = {
        'colleges': colleges,
        'recent_orders': recent_orders[:10],  # Last 10 orders
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'active_colleges': active_colleges,
        'total_menu_items': total_menu_items,
        'total_users': total_users,
        'active_users_today': active_users_today,
        'active_users_date': active_users_date,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'date_orders': date_orders,
        'date_revenue': date_revenue,
        'selected_date': selected_date,
        'college_orders': college_orders,
        'monthly_data': json.dumps(monthly_data),
        'users_with_phones': users_with_phones[:20],  # Last 20 users with phones
    }
    
    return render(request, 'orders/super_admin_dashboard.html', context)

@login_required(login_url='/admin/login/')
def manage_college(request, college_id):
    """Manage individual college settings"""
    # Check if user is superuser or college admin
    if not request.user.is_superuser:
        # Check if user is the college admin for this college
        try:
            college = College.objects.get(id=college_id, admin_email=request.user.email, is_active=True)
            # Store user type and college info in session for consistent behavior
            request.session['user_type'] = 'college_admin'
            request.session['college_slug'] = college.slug
            request.session['college_name'] = college.name
            request.session['user_email'] = request.user.email
        except College.DoesNotExist:
            messages.error(request, "Access denied. You don't have permission to manage this college.")
            return redirect('home')
    else:
        # Superuser - store user type in session
        request.session['user_type'] = 'super_admin'
        request.session['user_email'] = request.user.email
        college = get_object_or_404(College, id=college_id)
    
    if request.method == 'POST':
        # Update college settings using SecurityValidator
        college.name = SecurityValidator.sanitize_input(request.POST.get('name', college.name))
        college.address = SecurityValidator.sanitize_input(request.POST.get('address', college.address))
        college.admin_name = SecurityValidator.sanitize_input(request.POST.get('admin_name', college.admin_name))
        college.admin_email = SecurityValidator.sanitize_input(request.POST.get('admin_email', college.admin_email))
        college.admin_phone = SecurityValidator.sanitize_input(request.POST.get('admin_phone', college.admin_phone))
        college.is_active = request.POST.get('is_active') == 'on'
        college.payment_gateway_enabled = request.POST.get('payment_gateway_enabled') == 'on'
        college.allow_pay_later = request.POST.get('allow_pay_later') == 'on'
        
        try:
            college.save()
            messages.success(request, f"College '{college.name}' updated successfully!")
        except Exception as e:
            messages.error(request, f"Error updating college: {str(e)}")
    
    # Get college orders
    orders = Order.objects.filter(college=college).order_by('-created_at')
    
    context = {
        'college': college,
        'orders': orders[:20],  # Last 20 orders
    }
    
    return render(request, 'orders/manage_college.html', context)

@login_required(login_url='/admin/login/')
def manage_menu_items(request):
    """Manage all menu items across colleges"""
    # Check if user is superuser or college admin
    if not request.user.is_superuser:
        # Check if user is a college admin
        try:
            college = College.objects.get(admin_email=request.user.email, is_active=True)
            # Store user type and college info in session for consistent behavior
            request.session['user_type'] = 'college_admin'
            request.session['college_slug'] = college.slug
            request.session['college_name'] = college.name
            request.session['user_email'] = request.user.email
        except College.DoesNotExist:
            messages.error(request, "Access denied. You don't have permission to manage menu items.")
            return redirect('home')
    else:
        # Superuser - store user type in session
        request.session['user_type'] = 'super_admin'
        request.session['user_email'] = request.user.email
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            # Add new menu item using SecurityValidator
            name = SecurityValidator.sanitize_input(request.POST.get('name'))
            description = SecurityValidator.sanitize_input(request.POST.get('description'))
            price = request.POST.get('price')
            category = SecurityValidator.sanitize_input(request.POST.get('category'))
            college_id = request.POST.get('college')
            
            try:
                college = College.objects.get(id=college_id) if college_id else None
                MenuItem.objects.create(
                    name=name,
                    description=description,
                    price=price,
                    category=category,
                    college=college
                )
                messages.success(request, f"Menu item '{name}' added successfully!")
            except Exception as e:
                messages.error(request, f"Error adding menu item: {str(e)}")
        
        elif action == 'delete':
            # Delete menu item
            item_id = request.POST.get('item_id')
            try:
                item = MenuItem.objects.get(id=item_id)
                item_name = item.name
                item.delete()
                messages.success(request, f"Menu item '{item_name}' deleted successfully!")
            except MenuItem.DoesNotExist:
                messages.error(request, "Menu item not found.")
            except Exception as e:
                messages.error(request, f"Error deleting menu item: {str(e)}")
        
        elif action == 'update':
            # Update menu item
            item_id = request.POST.get('item_id')
            try:
                item = MenuItem.objects.get(id=item_id)
                item.name = SecurityValidator.sanitize_input(request.POST.get('name', item.name))
                item.description = SecurityValidator.sanitize_input(request.POST.get('description', item.description))
                item.price = request.POST.get('price', item.price)
                item.category = SecurityValidator.sanitize_input(request.POST.get('category', item.category))
                item.is_available = request.POST.get('is_available') == 'on'
                item.save()
                messages.success(request, f"Menu item '{item.name}' updated successfully!")
            except MenuItem.DoesNotExist:
                messages.error(request, "Menu item not found.")
            except Exception as e:
                messages.error(request, f"Error updating menu item: {str(e)}")
    
    # Get all menu items with college info
    menu_items = MenuItem.objects.select_related('college').order_by('college__name', 'category', 'name')
    colleges = College.objects.filter(is_active=True).order_by('name')
    
    context = {
        'menu_items': menu_items,
        'colleges': colleges,
    }
    
    return render(request, 'orders/manage_menu_items.html', context)

@login_required(login_url='/admin/login/')
def delete_college(request, college_id):
    """Delete a college (emergency function)"""
    # Check if user is superuser or college admin
    if not request.user.is_superuser:
        # Check if user is the college admin for this college
        try:
            college = College.objects.get(id=college_id, admin_email=request.user.email, is_active=True)
            # Store user type and college info in session for consistent behavior
            request.session['user_type'] = 'college_admin'
            request.session['college_slug'] = college.slug
            request.session['college_name'] = college.name
            request.session['user_email'] = request.user.email
        except College.DoesNotExist:
            messages.error(request, "Access denied. You don't have permission to delete this college.")
            return redirect('home')
    else:
        # Superuser - store user type in session
        request.session['user_type'] = 'super_admin'
        request.session['user_email'] = request.user.email
    
    if request.method == 'POST':
        try:
            college = College.objects.get(id=college_id)
            college_name = college.name
            
            # Check if college has active orders
            active_orders = Order.objects.filter(college=college, status__in=['Pending', 'Paid', 'In Progress'])
            if active_orders.exists():
                messages.error(request, f"Cannot delete college '{college_name}' - it has active orders.")
                return redirect('super_admin_dashboard')
            
            # Delete college and related data
            college.delete()
            messages.success(request, f"College '{college_name}' deleted successfully!")
            
        except College.DoesNotExist:
            messages.error(request, "College not found.")
        except Exception as e:
            messages.error(request, f"Error deleting college: {str(e)}")
    
    return redirect('super_admin_dashboard')

@login_required(login_url='/admin/login/')
def view_order_history(request):
    """View comprehensive order history with date filtering"""
    # Check if user is superuser or college admin
    if not request.user.is_superuser:
        # Check if user is a college admin
        try:
            college = College.objects.get(admin_email=request.user.email, is_active=True)
            # Store user type and college info in session for consistent behavior
            request.session['user_type'] = 'college_admin'
            request.session['college_slug'] = college.slug
            request.session['college_name'] = college.name
            request.session['user_email'] = request.user.email
        except College.DoesNotExist:
            messages.error(request, "Access denied. You don't have permission to view order history.")
            return redirect('home')
    else:
        # Superuser - store user type in session
        request.session['user_type'] = 'super_admin'
        request.session['user_email'] = request.user.email
    
    from datetime import datetime
    
    # Get date filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    college_id = request.GET.get('college')
    
    orders = Order.objects.select_related('college', 'user').order_by('-created_at')
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__gte=start_date)
        except:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__lte=end_date)
        except:
            pass
    
    if college_id:
        orders = orders.filter(college_id=college_id)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 50)  # 50 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    colleges = College.objects.all().order_by('name')
    
    context = {
        'page_obj': page_obj,
        'colleges': colleges,
        'start_date': start_date,
        'end_date': end_date,
        'selected_college': college_id,
    }
    
    return render(request, 'orders/order_history_admin.html', context)

@require_POST
@csrf_protect
@login_required
def toggle_favorite(request, item_id):
    """Toggle favorite status of an item"""
    try:
        item = MenuItem.objects.get(id=item_id)
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        if item in user_profile.favorite_items.all():
            user_profile.favorite_items.remove(item)
            is_favorite = False
            message = f"{item.name} removed from favorites"
        else:
            user_profile.favorite_items.add(item)
            is_favorite = True
            message = f"{item.name} added to favorites"
        
        return JsonResponse({
            'success': True,
            'is_favorite': is_favorite,
            'message': message
        })
        
    except MenuItem.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Error updating favorites'}, status=500)

@login_required
def favorites(request):
    """View favorite items"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        selected_college = request.session.get('selected_college')
        
        if selected_college:
            college = College.objects.get(id=selected_college['id'])
            favorite_items = user_profile.favorite_items.filter(college=college)
        else:
            favorite_items = user_profile.favorite_items.all()
            college = None
        
        context = {
            'favorite_items': favorite_items,
            'college': college,
        }
        return render(request, 'orders/favorites.html', context)
        
    except UserProfile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('home')

# Canteen Staff Authentication and Management Views
def canteen_staff_login(request):
    """Canteen staff login view with simplified and secure authentication logic"""
    
    # If user is already authenticated, check if they are valid canteen staff
    if request.user.is_authenticated:
        user_email = request.user.email
        
        # Check if user is the main admin (skipthequeue.app@gmail.com)
        if user_email == 'skipthequeue.app@gmail.com':
            if not request.user.is_superuser:
                # Update user to superuser if they have the admin email
                request.user.is_superuser = True
                request.user.is_staff = True
                request.user.save()
            # Store user type in session for consistent behavior
            request.session['user_type'] = 'super_admin'
            request.session['user_email'] = user_email
            return redirect('super_admin_dashboard')
        
        try:
            canteen_staff = CanteenStaff.objects.get(user=request.user, is_active=True)
            # Store user type and college info in session
            request.session['user_type'] = 'canteen_staff'
            request.session['college_slug'] = canteen_staff.college.slug
            request.session['college_name'] = canteen_staff.college.name
            request.session['user_email'] = user_email
            # Redirect to the assigned college dashboard
            return redirect('canteen_staff_dashboard', college_slug=canteen_staff.college.slug)
        except CanteenStaff.DoesNotExist:
            # User is not authorized as canteen staff, log them out
            logout(request)
            messages.error(request, "Access denied. You are not authorized as canteen staff.")
            return redirect('canteen_staff_login')

    if request.method == 'POST':
        identifier = request.POST.get('email')  # This could be email or username
        password = request.POST.get('password')

        if identifier and password:
            # Try to find user by email first, then username
            user = User.objects.filter(email=identifier).first()
            if not user:
                user = User.objects.filter(username=identifier).first()
            
            if user and user.check_password(password):
                # Check if user is the main admin
                if user.email == 'skipthequeue.app@gmail.com':
                    if not user.is_superuser:
                        user.is_superuser = True
                        user.is_staff = True
                        user.save()
                    login(request, user)
                    request.session.save()
                    # Store user type in session for consistent behavior
                    request.session['user_type'] = 'super_admin'
                    request.session['user_email'] = user.email
                    messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                    return redirect('super_admin_dashboard')
                
                try:
                    # Check if user is authorized as canteen staff
                    canteen_staff = CanteenStaff.objects.get(user=user, is_active=True)
                    login(request, user)
                    request.session.save()  # Force session save
                    # Store user type and college info in session
                    request.session['user_type'] = 'canteen_staff'
                    request.session['college_slug'] = canteen_staff.college.slug
                    request.session['college_name'] = canteen_staff.college.name
                    request.session['user_email'] = user.email
                    messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                    # Always redirect to the assigned college dashboard
                    return redirect('canteen_staff_dashboard', college_slug=canteen_staff.college.slug)
                except CanteenStaff.DoesNotExist:
                    logger.warning(f"Login attempt for unauthorized user: {identifier}")
                    messages.error(request, "Access denied. You are not authorized as canteen staff.")
            else:
                logger.warning(f"Invalid login attempt for: {identifier}")
                messages.error(request, "Invalid credentials.")
        else:
            messages.error(request, "Please provide both email/username and password.")

    return render(request, 'orders/canteen_staff_login.html')

@login_required(login_url='/canteen/login/')
def canteen_staff_dashboard(request, college_slug):
    """Enhanced canteen dashboard with simplified security logic"""
    
    # Check if user is the main admin (skipthequeue.app@gmail.com)
    if request.user.email == 'skipthequeue.app@gmail.com':
        if not request.user.is_superuser:
            # Update user to superuser if they have the admin email
            request.user.is_superuser = True
            request.user.is_staff = True
            request.user.save()
        # Store user type in session for consistent behavior
        request.session['user_type'] = 'super_admin'
        request.session['user_email'] = request.user.email
        return redirect('super_admin_dashboard')
    
    try:
        # Get the user's assigned canteen staff record
        try:
            canteen_staff = CanteenStaff.objects.get(user=request.user, is_active=True)
        except CanteenStaff.DoesNotExist:
            logout(request)
            messages.error(request, "Access denied. You are not authorized as canteen staff.")
            return redirect('canteen_staff_login')
        
        # Get the assigned college and verify it exists and is active
        assigned_college = canteen_staff.college
        if not assigned_college or not assigned_college.is_active:
            logout(request)
            messages.error(request, "Your assigned college is no longer active. Please contact administrator.")
            return redirect('canteen_staff_login')
        
        # If URL slug doesn't match assigned college, redirect to correct dashboard
        if college_slug != assigned_college.slug:
            return redirect('canteen_staff_dashboard', college_slug=assigned_college.slug)
        
        college = assigned_college
        
        # Store user type and college info in session for consistent behavior
        request.session['user_type'] = 'canteen_staff'
        request.session['college_slug'] = college.slug
        request.session['college_name'] = college.name
        request.session['user_email'] = request.user.email
        
        # Check if user has permission (superuser can access any college)
        if not (request.user.is_superuser or is_canteen_staff(request.user, college)):
            logout(request)
            messages.error(request, "Access denied. You don't have permission to access this college's dashboard.")
            return redirect('canteen_staff_login')
        
        print(f"DEBUG: User {request.user.username} is authorized for college {college.name}")
        
        # Get orders with different statuses using efficient queries with prefetch_related
        # Use only() to fetch only needed fields for better performance
        order_fields = ['id', 'user_name', 'user_phone', 'total_price', 'created_at', 'status']
        item_fields = ['quantity', 'total_price']
        menu_fields = ['name']
        
        # Optimize pending orders query
        pending_orders = Order.objects.filter(
            college=college,
            status='Paid'
        ).only(*order_fields).prefetch_related(
            Prefetch('order_items', 
                    queryset=OrderItem.objects.only(*item_fields).select_related('menu_item').only('menu_item__name'))
        ).order_by('-created_at')[:20]  # Limit to 20 orders for performance
        
        # Optimize in-progress orders query
        in_progress_orders = Order.objects.filter(
            college=college,
            status='In Progress'
        ).only(*order_fields).prefetch_related(
            Prefetch('order_items', 
                    queryset=OrderItem.objects.only(*item_fields).select_related('menu_item').only('menu_item__name'))
        ).order_by('-created_at')[:20]
        
        # Optimize ready orders query
        ready_orders = Order.objects.filter(
            college=college,
            status='Ready'
        ).only(*order_fields).prefetch_related(
            Prefetch('order_items', 
                    queryset=OrderItem.objects.only(*item_fields).select_related('menu_item').only('menu_item__name'))
        ).order_by('-created_at')[:20]
        
        # Get today's orders with caching for better performance
        today = timezone.now().date()
        today_cache_key = f'today_orders_{college.id}_{today}'
        today_orders_data = cache.get(today_cache_key)
        
        if today_orders_data is None:
            # Fetch today's orders data
            today_orders = Order.objects.filter(
                college=college,
                created_at__date=today
            ).only('status', 'total_price')
            
            total_today = today_orders.count()
            completed_today = today_orders.filter(status='Completed').count()
            total_revenue_today = sum(order.total_price for order in today_orders.filter(status='Completed'))
            
            # Cache for 5 minutes
            today_orders_data = {
                'total': total_today,
                'completed': completed_today,
                'revenue': total_revenue_today
            }
            cache.set(today_cache_key, today_orders_data, 300)
        else:
            total_today = today_orders_data['total']
            completed_today = today_orders_data['completed']
            total_revenue_today = today_orders_data['revenue']
        
        context = {
            'college': college,
            'active_orders': active_orders,
            'pending_orders': pending_orders,
            'in_progress_orders': in_progress_orders,
            'ready_orders': ready_orders,
            'total_today': total_today,
            'completed_today': completed_today,
            'total_revenue_today': total_revenue_today,
        }
        
        return render(request, 'orders/canteen_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in canteen_staff_dashboard for user {request.user.username}: {str(e)}")
        messages.error(request, "Error loading dashboard. Please try again.")
        return redirect('canteen_staff_login')

@login_required(login_url='/canteen/login/')
@require_POST
@csrf_protect
def canteen_accept_order(request, college_slug, order_id):
    """Accept order with enhanced security"""
    try:
        college = get_object_or_404(College, slug=college_slug)
        order = get_object_or_404(Order, id=order_id, college=college)
        
        # Check permissions
        try:
            canteen_staff = CanteenStaff.objects.get(
                user=request.user, 
                college=college, 
                is_active=True,
                can_accept_orders=True
            )
        except CanteenStaff.DoesNotExist:
            if not request.user.is_superuser:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if order.status == 'Paid':
            order.status = 'In Progress'
            order.save()
            return JsonResponse({'success': True, 'message': f'Order #{order.id} accepted!'})
        else:
            return JsonResponse({'error': 'Order cannot be accepted in current status'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': 'Error accepting order'}, status=500)

@login_required(login_url='/canteen/login/')
@require_POST
@csrf_protect
def canteen_decline_order(request, college_slug, order_id):
    """Decline order with enhanced security"""
    try:
        college = get_object_or_404(College, slug=college_slug)
        order = get_object_or_404(Order, id=order_id, college=college)
        
        # Check permissions
        try:
            canteen_staff = CanteenStaff.objects.get(
                user=request.user, 
                college=college, 
                is_active=True,
                can_accept_orders=True
            )
        except CanteenStaff.DoesNotExist:
            if not request.user.is_superuser:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        order.status = 'Declined'
        order.save()
        return JsonResponse({'success': True, 'message': f'Order #{order.id} declined!'})
        
    except Exception as e:
        return JsonResponse({'error': 'Error declining order'}, status=500)

def check_active_orders(request):
    """Check for active orders and return notification data - optimized"""
    if not request.user.is_authenticated:
        return JsonResponse({'active_orders': []})
    
    # Get user's active orders from cache
    user_profile = UserProfile.get_cached_profile(request.user.id)
    if not user_profile or not user_profile.phone_number:
        return JsonResponse({'active_orders': []})
    
    active_orders_key = f'active_orders_{user_profile.phone_number}'
    active_order_ids = cache.get(active_orders_key, [])
    
    if not active_order_ids:
        return JsonResponse({'active_orders': []})
    
    # Get active orders with optimized queries
    active_orders = Order.objects.filter(
        id__in=active_order_ids,
        status__in=['Pending', 'In Progress', 'Ready']
    ).select_related('college').prefetch_related('order_items__menu_item')
    
    orders_data = []
    for order in active_orders:
        orders_data.append({
            'id': order.id,
            'status': order.status,
            'college_name': order.college.name if order.college else 'Unknown',
            'total_price': float(order.total_price()),
            'created_at': order.created_at.isoformat(),
            'estimated_time': order.estimated_time,
            'status_color': order.get_status_color(),
        })
    
    return JsonResponse({'active_orders': orders_data})

@login_required(login_url='/canteen/login/')
@require_POST
@csrf_protect
def canteen_update_order_status(request, college_slug, order_id):
    """Update order status with enhanced security and notifications - optimized"""
    try:
        college = get_object_or_404(College, slug=college_slug)
        order = get_object_or_404(Order, id=order_id, college=college)
        new_status = request.POST.get('status')
        
        # Check permissions
        try:
            canteen_staff = CanteenStaff.objects.get(
                user=request.user, 
                college=college, 
                is_active=True,
                can_update_status=True
            )
        except CanteenStaff.DoesNotExist:
            if not request.user.is_superuser:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if new_status in ['In Progress', 'Ready', 'Completed']:
            old_status = order.status
            order.status = new_status
            order.save()
            
            # Prepare comprehensive notification data for user
            notification_data = {
                'success': True, 
                'message': f'Order #{order.id} status updated to {new_status}!',
                'order_id': order.id,
                'new_status': new_status,
                'old_status': old_status,
                'user_name': order.user_name,
                'college_name': college.name,
                'timestamp': timezone.now().isoformat(),
                'requires_user_action': False,
                'requires_notification': True
            }
            
            # Add specific notification for ready status - requires user action
            if new_status == 'Ready':
                notification_data['user_notification'] = {
                    'title': '🎉 Order Ready for Pickup!',
                    'message': f'Your order #{order.id} is ready for pickup at {college.name}. Please collect it from the canteen.',
                    'type': 'success',
                    'persistent': True,  # This notification won't auto-dismiss
                    'action_required': True,
                    'order_id': order.id,
                    'college_name': college.name
                }
                notification_data['requires_user_action'] = True
                notification_data['status_color'] = 'status-ready'
            elif new_status == 'In Progress':
                notification_data['user_notification'] = {
                    'title': '👨‍🍳 Order Being Prepared',
                    'message': f'Your order #{order.id} is being prepared at {college.name}. We\'ll notify you when it\'s ready!',
                    'type': 'info',
                    'persistent': False,
                    'action_required': False,
                    'order_id': order.id,
                    'college_name': college.name
                }
                notification_data['status_color'] = 'status-preparing'
            elif new_status == 'Completed':
                notification_data['user_notification'] = {
                    'title': '✅ Order Completed',
                    'message': f'Your order #{order.id} has been completed. Thank you for using SkipTheQueue!',
                    'type': 'success',
                    'persistent': False,
                    'action_required': False,
                    'order_id': order.id,
                    'college_name': college.name
                }
                notification_data['status_color'] = 'status-completed'
            
            # Store notification in session for the user to see - optimized
            if order.user_phone:
                # Use cache for notifications instead of multiple session writes
                notification_key = f'order_notification_{order.user_phone}_{order.id}'
                cache.set(notification_key, notification_data, CACHE_TIMEOUT)
                
                # Store in user's active orders for real-time tracking
                active_orders_key = f'active_orders_{order.user_phone}'
                active_orders = cache.get(active_orders_key, [])
                if order.id not in active_orders:
                    active_orders.append(order.id)
                    cache.set(active_orders_key, active_orders, CACHE_TIMEOUT)
                
                # Store persistent notification for ready orders
                if new_status == 'Ready':
                    persistent_key = f'persistent_notification_{order.user_phone}_{order.id}'
                    cache.set(persistent_key, {
                        'type': 'order_ready',
                        'title': '🎉 Order Ready for Pickup!',
                        'message': f'Your order #{order.id} is ready for pickup at {college.name}. Please collect it from the canteen.',
                        'order_id': order.id,
                        'college_name': college.name,
                        'timestamp': timezone.now().isoformat(),
                        'persistent': True,
                        'requires_action': True
                    }, CACHE_TIMEOUT)
            
            return JsonResponse(notification_data)
        else:
            return JsonResponse({'error': 'Invalid status'}, status=400)
            
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required(login_url='/canteen/login/')
def canteen_manage_menu(request, college_slug):
    """Canteen staff menu management with security"""
    try:
        college = get_object_or_404(College, slug=college_slug)
        
        # Check permissions
        try:
            canteen_staff = CanteenStaff.objects.get(
                user=request.user, 
                college=college, 
                is_active=True
            )
        except CanteenStaff.DoesNotExist:
            if not request.user.is_superuser:
                messages.error(request, "Access denied.")
                return redirect('canteen_staff_login')
        
        menu_items = MenuItem.objects.filter(college=college).order_by('category', 'name')
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'toggle_availability':
                item_id = request.POST.get('item_id')
                try:
                    item = MenuItem.objects.get(id=item_id, college=college)
                    item.is_available = not item.is_available
                    item.save()
                    messages.success(request, f"{item.name} availability updated!")
                except MenuItem.DoesNotExist:
                    messages.error(request, "Menu item not found.")
                    
            elif action == 'update_price':
                item_id = request.POST.get('item_id')
                new_price = request.POST.get('price')
                try:
                    item = MenuItem.objects.get(id=item_id, college=college)
                    item.price = new_price
                    item.save()
                    messages.success(request, f"{item.name} price updated!")
                except (MenuItem.DoesNotExist, ValueError):
                    messages.error(request, "Invalid price or item not found.")
                    
            elif action == 'update_stock':
                item_id = request.POST.get('item_id')
                new_stock = request.POST.get('stock')
                try:
                    item = MenuItem.objects.get(id=item_id, college=college)
                    item.stock_quantity = int(new_stock)
                    item.save()
                    messages.success(request, f"{item.name} stock updated!")
                except (MenuItem.DoesNotExist, ValueError):
                    messages.error(request, "Invalid stock quantity or item not found.")
        
        # Calculate stats for the dashboard
        available_count = menu_items.filter(is_available=True).count()
        stock_managed_count = menu_items.filter(is_stock_managed=True).count()
        categories_count = menu_items.values('category').distinct().count()
        
        context = {
            'college': college,
            'menu_items': menu_items,
            'canteen_staff': canteen_staff if 'canteen_staff' in locals() else None,
            'available_count': available_count,
            'stock_managed_count': stock_managed_count,
            'categories_count': categories_count
        }
        
        return render(request, 'orders/canteen_manage_menu.html', context)
        
    except Exception as e:
        messages.error(request, "Error loading menu management.")
        return redirect('canteen_staff_login')

@login_required(login_url='/canteen/login/')
def canteen_order_history(request, college_slug):
    """Canteen staff order history with security"""
    try:
        college = get_object_or_404(College, slug=college_slug)
        
        # Check permissions
        try:
            canteen_staff = CanteenStaff.objects.get(
                user=request.user, 
                college=college, 
                is_active=True,
                can_view_orders=True
            )
        except CanteenStaff.DoesNotExist:
            if not request.user.is_superuser:
                messages.error(request, "Access denied.")
                return redirect('canteen_staff_login')
        
        # Get date range from request
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        status_filter = request.GET.get('status', '')
        
        orders = Order.objects.filter(college=college)
        
        if date_from:
            orders = orders.filter(created_at__date__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__date__lte=date_to)
        if status_filter:
            orders = orders.filter(status=status_filter)
        
        orders = orders.order_by('-created_at')
        
        # Get statistics
        total_orders = orders.count()
        total_revenue = sum(order.total_price() for order in orders.filter(status='Completed'))
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        context = {
            'college': college,
            'orders': orders,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'avg_order_value': avg_order_value,
            'canteen_staff': canteen_staff if 'canteen_staff' in locals() else None
        }
        
        return render(request, 'orders/canteen_order_history.html', context)
        
    except Exception as e:
        messages.error(request, "Error loading order history.")
        return redirect('canteen_staff_login')

def canteen_staff_logout(request):
    """Canteen staff logout"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('canteen_staff_login')

def create_temp_superuser(request):
    """Create a temporary superuser for admin access"""
    if not User.objects.filter(email='skipthequeue.app@gmail.com').exists():
        User.objects.create_superuser(
            username='skipthequeue',
            email='skipthequeue.app@gmail.com',
            password='Paras@999'
        )
        return HttpResponse("✅ Superuser created! Email: skipthequeue.app@gmail.com, Password: Paras@999")
    return HttpResponse("❌ Superuser already exists with email: skipthequeue.app@gmail.com")

def debug_canteen_staff(request):
    """Temporary debug view to check canteen staff assignments"""
    if not request.user.is_superuser:
        return HttpResponse("Access denied. Superuser only.")
    
    debug_info = []
    
    # Check all canteen staff
    canteen_staff_list = CanteenStaff.objects.filter(is_active=True).select_related('user', 'college')
    debug_info.append(f"Total active canteen staff: {canteen_staff_list.count()}")
    
    for staff in canteen_staff_list:
        debug_info.append(f"User: {staff.user.username} ({staff.user.email}) - College: {staff.college.name} (slug: {staff.college.slug}) - Active: {staff.is_active}")
    
    # Check specific user 'paras'
    try:
        paras_user = User.objects.get(username='paras')
        debug_info.append(f"\nUser 'paras' found: {paras_user.username} ({paras_user.email})")
        
        paras_staff = CanteenStaff.objects.filter(user=paras_user, is_active=True).first()
        if paras_staff:
            debug_info.append(f"Paras is assigned to: {paras_staff.college.name} (slug: {paras_staff.college.slug})")
        else:
            debug_info.append("Paras is NOT assigned as active canteen staff")
    except User.DoesNotExist:
        debug_info.append("User 'paras' not found")
    
    # Check all colleges
    colleges = College.objects.filter(is_active=True)
    debug_info.append(f"\nActive colleges: {colleges.count()}")
    for college in colleges:
        debug_info.append(f"College: {college.name} (slug: {college.slug})")
    
    return HttpResponse("<br>".join(debug_info))

def security_test(request):
    """Comprehensive security test endpoint"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    test_results = {
        'authentication': {},
        'session_security': {},
        'input_validation': {},
        'csrf_protection': {},
        'rate_limiting': {},
        'headers': {},
        'overall_status': 'PASS'
    }
    
    # Test Authentication
    test_results['authentication']['user_authenticated'] = request.user.is_authenticated
    test_results['authentication']['user_is_superuser'] = request.user.is_superuser
    test_results['authentication']['user_is_staff'] = request.user.is_staff
    test_results['authentication']['user_is_active'] = request.user.is_active
    
    # Test Session Security
    test_results['session_security']['session_exists'] = bool(request.session.session_key)
    test_results['session_security']['session_age'] = request.session.get('_session_age', 0)
    test_results['session_security']['security_hash_exists'] = bool(request.session.get('_security_hash'))
    
    # Test Input Validation
    test_input = '<script>alert("xss")</script>'
    sanitized = SecurityValidator.sanitize_input(test_input)
    test_results['input_validation']['xss_prevention'] = '<script>' not in sanitized
    
    # Test CSRF Protection
    test_results['csrf_protection']['csrf_token_exists'] = bool(request.META.get('CSRF_COOKIE'))
    test_results['csrf_protection']['csrf_header_exists'] = bool(request.META.get('HTTP_X_CSRFTOKEN'))
    
    # Test Rate Limiting
    rate_limit_key = f"rate_limit:test:{request.META.get('REMOTE_ADDR', 'unknown')}"
    current_count = request.session.get(rate_limit_key, 0)
    test_results['rate_limiting']['current_count'] = current_count
    test_results['rate_limiting']['limit_not_exceeded'] = current_count < 100
    
    # Test Security Headers
    response = JsonResponse(test_results)
    test_results['headers']['x_content_type_options'] = response.get('X-Content-Type-Options') == 'nosniff'
    test_results['headers']['x_frame_options'] = response.get('X-Frame-Options') == 'DENY'
    test_results['headers']['x_xss_protection'] = response.get('X-XSS-Protection') == '1; mode=block'
    
    # Overall Status
    all_tests = []
    for category, tests in test_results.items():
        if category != 'overall_status':
            for test_name, result in tests.items():
                if isinstance(result, bool):
                    all_tests.append(result)
    
    test_results['overall_status'] = 'PASS' if all(all_tests) else 'FAIL'
    test_results['total_tests'] = len(all_tests)
    test_results['passed_tests'] = sum(all_tests)
    test_results['failed_tests'] = len(all_tests) - sum(all_tests)
    
    return JsonResponse(test_results)

def debug_home(request):
    """Debug view to check what's happening with the home page"""
    colleges = College.objects.filter(is_active=True).order_by('name')
    selected_college = request.session.get('selected_college')
    
    debug_info = {
        'user_authenticated': request.user.is_authenticated,
        'user_email': request.user.email if request.user.is_authenticated else None,
        'user_is_superuser': request.user.is_superuser if request.user.is_authenticated else False,
        'colleges_count': colleges.count(),
        'colleges_list': list(colleges.values('id', 'name', 'slug', 'is_active')),
        'selected_college': selected_college,
        'session_keys': list(request.session.keys()),
        'debug_mode': settings.DEBUG,
    }
    
    return JsonResponse(debug_info)

@safe_view
def health_check(request):
    """Comprehensive health check to verify the application is working"""
    # Use the comprehensive health check from error handling
    health_status = comprehensive_health_check()
    
    # Add application-specific checks
    try:
        colleges_count = College.objects.filter(is_active=True).count()
        superuser_exists = User.objects.filter(
            email='skipthequeue.app@gmail.com',
            is_superuser=True
        ).exists()
        
        health_status.update({
            'debug_mode': settings.DEBUG,
            'colleges_count': colleges_count,
            'superuser_exists': superuser_exists,
            'database_connected': True,
        })
        
    except Exception as e:
        health_status['checks']['application'] = {
            'status': 'unhealthy',
            'message': f'Application error: {str(e)}'
        }
        health_status['overall_status'] = 'unhealthy'
    
    return JsonResponse(health_status, status=200 if health_status['overall_status'] == 'healthy' else 500)

@safe_view
def site_diagnostic(request):
    """Comprehensive diagnostic to identify site issues"""
    diagnostic_results = {
        'timestamp': timezone.now().isoformat(),
        'debug_mode': settings.DEBUG,
        'issues': [],
        'warnings': [],
        'success': [],
        'database': {},
        'authentication': {},
        'static_files': {},
        'templates': {},
    }
    
    try:
        # Database checks
        colleges = College.objects.filter(is_active=True)
        diagnostic_results['database']['colleges_count'] = colleges.count()
        diagnostic_results['database']['colleges_list'] = list(colleges.values('id', 'name', 'slug', 'is_active', 'estimated_preparation_time'))
        
        if colleges.count() == 0:
            diagnostic_results['issues'].append('No active colleges found in database')
        else:
            diagnostic_results['success'].append(f'Found {colleges.count()} active colleges')
        
        # Check for superuser
        superuser = User.objects.filter(email='skipthequeue.app@gmail.com', is_superuser=True).first()
        if superuser:
            diagnostic_results['authentication']['superuser_exists'] = True
            diagnostic_results['authentication']['superuser_username'] = superuser.username
            diagnostic_results['success'].append('Superuser exists and is properly configured')
        else:
            diagnostic_results['issues'].append('Superuser (skipthequeue.app@gmail.com) not found or not configured as superuser')
        
        # Check canteen staff
        canteen_staff = CanteenStaff.objects.filter(is_active=True)
        diagnostic_results['database']['canteen_staff_count'] = canteen_staff.count()
        
        # Check menu items
        menu_items = MenuItem.objects.filter(is_available=True)
        diagnostic_results['database']['menu_items_count'] = menu_items.count()
        
        # Check static files
        try:
            from django.contrib.staticfiles.finders import find
            # Check if key static files exist
            static_files_to_check = [
                'images/colleges/ramdeo-baba-logo.png',
                'images/colleges/gh-raisoni-logo.png', 
                'images/colleges/ycce-logo.png',
                'images/zap-icon.svg'
            ]
            
            for static_file in static_files_to_check:
                if find(static_file):
                    diagnostic_results['static_files'][static_file] = 'Found'
                else:
                    diagnostic_results['warnings'].append(f'Static file not found: {static_file}')
                    
        except Exception as e:
            diagnostic_results['warnings'].append(f'Static files check failed: {str(e)}')
        
        # Check session
        diagnostic_results['session'] = {
            'session_id': request.session.session_key,
            'session_keys': list(request.session.keys()),
            'selected_college': request.session.get('selected_college'),
        }
        
        # Check user authentication
        if request.user.is_authenticated:
            diagnostic_results['authentication']['user_authenticated'] = True
            diagnostic_results['authentication']['user_email'] = request.user.email
            diagnostic_results['authentication']['user_is_superuser'] = request.user.is_superuser
            diagnostic_results['authentication']['user_is_staff'] = request.user.is_staff
        else:
            diagnostic_results['authentication']['user_authenticated'] = False
        
        # Check for common issues
        if settings.DEBUG:
            diagnostic_results['warnings'].append('DEBUG mode is enabled - this should be False in production')
        
        # Check if any colleges have missing required fields
        for college in colleges:
            if not college.estimated_preparation_time:
                diagnostic_results['warnings'].append(f'College "{college.name}" has no estimated preparation time')
        
        # Check for empty menu items
        colleges_without_menu = colleges.exclude(menu_items__is_available=True).distinct()
        if colleges_without_menu.exists():
            diagnostic_results['warnings'].append(f'Colleges without menu items: {list(colleges_without_menu.values_list("name", flat=True))}')
        
    except Exception as e:
        diagnostic_results['issues'].append(f'Database connection error: {str(e)}')
    
    # Determine overall status
    if diagnostic_results['issues']:
        diagnostic_results['status'] = 'ERROR'
    elif diagnostic_results['warnings']:
        diagnostic_results['status'] = 'WARNING'
    else:
        diagnostic_results['status'] = 'HEALTHY'
    
    return JsonResponse(diagnostic_results, status=200 if diagnostic_results['status'] != 'ERROR' else 500)

@safe_view
def error_monitoring_dashboard(request):
    """Error monitoring dashboard for administrators"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get error statistics
    error_stats = ErrorTracker.get_error_stats()
    
    # Get recent errors from cache
    recent_errors = []
    for i in range(10):  # Get last 10 errors
        error_key = f"error_{int(time.time()) - (i * 60)}"  # Last 10 minutes
        error_data = cache.get(error_key)
        if error_data:
            recent_errors.append(error_data)
    
    dashboard_data = {
        'timestamp': timezone.now().isoformat(),
        'error_statistics': error_stats,
        'recent_errors': recent_errors,
        'health_status': comprehensive_health_check(),
        'system_info': {
            'debug_mode': settings.DEBUG,
            'database_engine': settings.DATABASES['default']['ENGINE'],
            'cache_backend': settings.CACHES['default']['BACKEND'],
        }
    }
    
    return JsonResponse(dashboard_data)

@require_GET
def check_order_status(request, order_id):
    """Check order status and return notifications for real-time updates"""
    try:
        # Get user phone from session or request
        user_phone = None
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                user_phone = user_profile.phone_number
            except UserProfile.DoesNotExist:
                pass
        
        # If no user phone, try to get from session
        if not user_phone:
            user_phone = request.session.get('user_phone')
        
        if not user_phone:
            return JsonResponse({
                'has_active_order': False,
                'message': 'No user phone found'
            })
        
        # Check for active orders for this user
        active_orders = Order.objects.filter(
            user_phone=user_phone,
            status__in=['Paid', 'In Progress', 'Ready']
        ).order_by('-created_at')
        
        if active_orders.exists():
            current_order = active_orders.first()
            
            # Check for persistent notifications for this order
            persistent_key = f'persistent_notification_{user_phone}_{current_order.id}'
            persistent_notification = request.session.get(persistent_key)
            
            # Check for user-specific persistent notifications
            user_persistent_key = f'user_persistent_notifications_{user_phone}'
            user_persistent_notifications = request.session.get(user_persistent_key, [])
            
            # Find notification for current order
            current_order_notification = None
            for notification in user_persistent_notifications:
                if notification.get('order_id') == current_order.id:
                    current_order_notification = notification
                    break
            
            response_data = {
                'has_active_order': True,
                'order': {
                    'id': current_order.id,
                    'status': current_order.status,
                    'status_display': current_order.get_status_display(),
                    'college_name': current_order.college.name,
                    'created_at': current_order.created_at.isoformat(),
                    'total_price': float(current_order.total_price()),
                    'items': [
                        {
                            'name': item.item.name,
                            'quantity': item.quantity,
                            'price': float(item.item.price)
                        } for item in current_order.order_items.all()
                    ]
                }
            }
            
            # Add notification data if available
            if persistent_notification:
                response_data['persistent_notification'] = persistent_notification
                response_data['requires_user_action'] = persistent_notification.get('requires_action', False)
            
            if current_order_notification:
                response_data['user_notification'] = current_order_notification
                response_data['requires_user_action'] = current_order_notification.get('requires_action', False)
            
            # Add status-specific information
            if current_order.status == 'Ready':
                response_data['order']['status_message'] = f'Your order #{current_order.id} is ready for pickup at {current_order.college.name}!'
                response_data['order']['status_icon'] = '🎉'
                response_data['order']['status_color'] = 'status-ready'
            elif current_order.status == 'In Progress':
                response_data['order']['status_message'] = f'Your order #{current_order.id} is being prepared at {current_order.college.name}.'
                response_data['order']['status_icon'] = '👨‍🍳'
                response_data['order']['status_color'] = 'status-preparing'
            elif current_order.status == 'Paid':
                response_data['order']['status_message'] = f'Your order #{current_order.id} has been confirmed and is being prepared.'
                response_data['order']['status_icon'] = '✅'
                response_data['order']['status_color'] = 'status-confirmed'
            
            return JsonResponse(response_data)
        else:
            # Check if there are any persistent notifications that should be shown
            user_persistent_key = f'user_persistent_notifications_{user_phone}'
            user_persistent_notifications = request.session.get(user_persistent_key, [])
            
            if user_persistent_notifications:
                # Return the most recent persistent notification
                latest_notification = user_persistent_notifications[-1]
                return JsonResponse({
                    'has_active_order': False,
                    'has_persistent_notification': True,
                    'persistent_notification': latest_notification,
                    'requires_user_action': latest_notification.get('requires_action', False)
                })
            
            return JsonResponse({
                'has_active_order': False,
                'message': 'No active orders found'
            })
            
    except Exception as e:
        logger.error(f"Error checking order status: {str(e)}")
        return JsonResponse({
            'error': 'Error checking order status',
            'message': str(e)
        }, status=500)

@require_GET
def check_notifications(request):
    """Check for new notifications for the current user"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'notifications': [],
                'has_notifications': False
            })
        
        # Get user phone from session or user profile
        user_phone = request.session.get('user_phone')
        if not user_phone:
            return JsonResponse({
                'notifications': [],
                'has_notifications': False
            })
        
        # Get active orders for this user
        active_orders = Order.objects.filter(
            user_phone=user_phone,
            status__in=['Pending', 'Payment Pending', 'Paid', 'In Progress', 'Ready']
        ).order_by('-created_at')
        
        notifications = []
        
        for order in active_orders:
            # Check if order status has changed recently
            if order.updated_at and (timezone.now() - order.updated_at).seconds < 300:  # 5 minutes
                notification = {
                    'id': f'order_{order.id}',
                    'type': 'info',
                    'title': 'Order Update',
                    'message': f'Order #{order.id} status: {order.status}',
                    'order_id': order.id,
                    'status': order.status,
                    'timestamp': order.updated_at.isoformat(),
                    'persistent': order.status == 'Ready'
                }
                notifications.append(notification)
        
        return JsonResponse({
            'notifications': notifications,
            'has_notifications': len(notifications) > 0
        })
        
    except Exception as e:
        logger.error(f"Error checking notifications: {str(e)}")
        return JsonResponse({
            'error': 'Failed to check notifications',
            'notifications': [],
            'has_notifications': False
        }, status=500)

@require_POST
def dismiss_notification(request, order_id):
    """Dismiss a notification for a specific order"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Get user phone from session
        user_phone = request.session.get('user_phone')
        if not user_phone:
            return JsonResponse({'error': 'User phone not found'}, status=400)
        
        # Verify the order belongs to this user
        try:
            order = Order.objects.get(
                id=order_id,
                user_phone=user_phone
            )
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
        
        # Mark notification as dismissed in session
        dismissed_notifications = request.session.get('dismissed_notifications', [])
        if order_id not in dismissed_notifications:
            dismissed_notifications.append(order_id)
            request.session['dismissed_notifications'] = dismissed_notifications
            request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': 'Notification dismissed'
        })
        
    except Exception as e:
        logger.error(f"Error dismissing notification: {str(e)}")
        return JsonResponse({
            'error': 'Failed to dismiss notification'
        }, status=500)

@require_POST
def update_order_status(request, order_id):
    """Update order status (for canteen staff)"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Check if user is canteen staff
        if not hasattr(request.user, 'canteenstaff'):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get the order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
        
        # Verify the order belongs to this canteen staff's college
        if order.college != request.user.canteenstaff.college:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get new status from request
        new_status = request.POST.get('status')
        if not new_status:
            return JsonResponse({'error': 'Status is required'}, status=400)
        
        # Validate status
        valid_statuses = ['Pending', 'Payment Pending', 'Paid', 'In Progress', 'Ready', 'Completed', 'Cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        # Update order status
        old_status = order.status
        order.status = new_status
        order.updated_at = timezone.now()
        order.save()
        
        # Log the status change
        logger.info(f"Order {order_id} status changed from {old_status} to {new_status} by {request.user.email}")
        
        # Send notification to user if status is 'Ready'
        if new_status == 'Ready':
            # Store notification in session for the user
            notification_data = {
                'order_id': order.id,
                'status': new_status,
                'college_name': order.college.name,
                'timestamp': order.updated_at.isoformat(),
                'message': f'Order #{order.id} is ready for pickup!'
            }
            
            # This will be picked up by the notification system when user checks
            # Store in a way that can be accessed by the user's session
            try:
                # Try to store in a shared cache or database field
                order.notification_data = notification_data
                order.save(update_fields=['notification_data'])
            except:
                # Fallback: store in a simple way
                pass
        
        return JsonResponse({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'order': {
                'id': order.id,
                'status': order.status,
                'updated_at': order.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}")
        return JsonResponse({
            'error': 'Failed to update order status'
        }, status=500)

@login_required
def check_order_status_main(request):
    """Check order status for the current user's active orders"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Get user's phone number from profile or session
        user_phone = None
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            user_phone = user_profile.phone_number
        except UserProfile.DoesNotExist:
            user_phone = request.session.get('user_phone')
        
        if not user_phone:
            return JsonResponse({'error': 'Phone number not found'}, status=400)
        
        # Check for active orders
        active_orders = Order.objects.filter(
            user_phone=user_phone,
            status__in=['Pending', 'Payment_Pending', 'Paid', 'In Progress', 'Ready']
        ).order_by('-created_at')
        
        if active_orders.exists():
            # Get the most recent active order
            current_order = active_orders.first()
            
            # Check for pending notifications
            notification_key = f'order_notification_{user_phone}_{current_order.id}'
            pending_notification = request.session.get(notification_key, None)
            
            response_data = {
                'has_active_order': True,
                'order': {
                    'id': current_order.id,
                    'status': current_order.status,
                    'status_color': current_order.get_status_color(),
                    'created_at': current_order.created_at.isoformat(),
                    'college_name': current_order.college.name,
                    'total_amount': float(current_order.total_price()),
                    'items_count': current_order.order_items.count()
                },
                'requires_notification': False,
                'notification_data': None
            }
            
            # If there's a pending notification, include it
            if pending_notification:
                response_data['requires_notification'] = True
                response_data['notification_data'] = pending_notification
                
                # Clear the notification from session after sending it (except for persistent ones)
                if not pending_notification.get('persistent', False):
                    request.session.pop(notification_key, None)
            
            # Check if order status requires immediate notification
            elif current_order.status == 'Ready':
                response_data['requires_notification'] = True
                response_data['notification_data'] = {
                    'title': '🎉 Order Ready for Pickup!',
                    'message': f'Your order #{current_order.id} is ready for pickup at {current_order.college.name}. Please collect it from the canteen.',
                    'type': 'success',
                    'persistent': True,
                    'action_required': True,
                    'order_id': current_order.id,
                    'college_name': current_order.college.name,
                    'timestamp': timezone.now().isoformat()
                }
            
            elif current_order.status == 'In Progress':
                response_data['requires_notification'] = True
                response_data['notification_data'] = {
                    'title': '👨‍🍳 Order Being Prepared',
                    'message': f'Your order #{current_order.id} is being prepared at {current_order.college.name}. We\'ll notify you when it\'s ready!',
                    'type': 'info',
                    'persistent': False,
                    'action_required': False,
                    'order_id': current_order.id,
                    'college_name': current_order.college.name,
                    'timestamp': timezone.now().isoformat()
                }
            
            return JsonResponse(response_data)
        else:
            # No active orders
            return JsonResponse({
                'has_active_order': False,
                'order': None,
                'requires_notification': False,
                'notification_data': None
            })
            
    except Exception as e:
        logger.error(f"Error checking order status: {str(e)}")
        return JsonResponse({'error': 'Error checking order status'}, status=500)

@require_GET
def check_order_status_by_phone(request, user_phone):
    """Check order status by user phone number for real-time notifications"""
    try:
        # Get active orders for this user
        active_orders = Order.objects.filter(
            user_phone=user_phone,
            status__in=['Pending', 'Payment Pending', 'Paid', 'In Progress', 'Ready']
        ).order_by('-created_at')
        
        if not active_orders.exists():
            return JsonResponse({
                'has_active_order': False,
                'notifications': []
            })
        
        # Get the most recent active order
        latest_order = active_orders.first()
        
        # Check for notifications in session
        notifications = []
        persistent_notifications = []
        
        # Check for persistent notifications (order ready)
        persistent_key = f'persistent_notification_{user_phone}_{latest_order.id}'
        if request.session.get(persistent_key):
            persistent_notifications.append(request.session[persistent_key])
        
        # Check for regular notifications
        notification_key = f'order_notification_{user_phone}_{latest_order.id}'
        if request.session.get(notification_key):
            notifications.append(request.session[notification_key])
        
        return JsonResponse({
            'has_active_order': True,
            'order_id': latest_order.id,
            'order_status': latest_order.status,
            'college_name': latest_order.college.name,
            'notifications': notifications,
            'persistent_notifications': persistent_notifications,
            'status_color': latest_order.get_status_color() if hasattr(latest_order, 'get_status_color') else 'status-default'
        })
        
    except Exception as e:
        logger.error(f"Error checking order status by phone: {str(e)}")
        return JsonResponse({
            'error': 'Error checking order status',
            'has_active_order': False
        }, status=500)

@require_GET
def order_status_update(request, order_id):
    """Get real-time order status update for a specific order"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user has permission to view this order
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        
        # Allow canteen staff, college admin, super admin, or the order owner
        can_view = False
        if request.user.is_superuser:
            can_view = True
        elif hasattr(request.user, 'canteenstaff') and request.user.canteenstaff.college == order.college:
            can_view = True
        elif hasattr(order.college, 'admin_email') and order.college.admin_email == request.user.email:
            can_view = True
        elif hasattr(request.user, 'userprofile') and request.user.userprofile.phone_number == order.user_phone:
            can_view = True
        
        if not can_view:
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        return JsonResponse({
            'order_id': order.id,
            'status': order.status,
            'status_color': order.get_status_color() if hasattr(order, 'get_status_color') else 'status-default',
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat() if hasattr(order, 'updated_at') else order.created_at.isoformat(),
            'college_name': order.college.name,
            'user_name': order.user_name,
            'total_price': float(order.total_price()),
            'items': [
                {
                    'name': item.menu_item.name,
                    'quantity': item.quantity,
                    'price': float(item.menu_item.price)
                } for item in order.orderitem_set.all()
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting order status update: {str(e)}")
        return JsonResponse({'error': 'Error getting order status'}, status=500)

@login_required
def user_profile(request):
    """User profile view with comprehensive information - optimized for performance"""
    try:
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'phone_number': ''}
        )
        
        if created:
            messages.info(request, "Profile created successfully!")
        
        # Get user's recent orders with optimized queries (only if phone number exists)
        recent_orders = []
        if user_profile.phone_number:
            recent_orders = Order.objects.filter(
                user_phone=user_profile.phone_number
            ).select_related('college').prefetch_related('order_items__menu_item').order_by('-created_at')[:10]
        
        # Get user's favorite items with optimization
        favorite_items = user_profile.favorite_items.select_related('college').all()
        
        # Get user's preferred college (already loaded with select_related)
        preferred_college = user_profile.preferred_college
        
        # Calculate orders this month (only if phone number exists)
        orders_this_month = 0
        total_orders = 0
        total_spent = 0
        
        if user_profile.phone_number:
            from datetime import datetime, timedelta
            now = timezone.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            orders_this_month = Order.objects.filter(
                user_phone=user_profile.phone_number,
                created_at__gte=month_start
            ).count()
            
            # Optimize total calculations using database aggregation
            from django.db.models import Sum, Count
            order_stats = Order.objects.filter(
                user_phone=user_profile.phone_number
            ).aggregate(
                total_orders=Count('id'),
                total_spent=Sum('amount_paid')
            )
            
            total_orders = order_stats['total_orders'] or 0
            total_spent = order_stats['total_spent'] or 0
        
        context = {
            'user_profile': user_profile,
            'recent_orders': recent_orders,
            'favorite_items': favorite_items,
            'preferred_college': preferred_college,
            'total_orders': total_orders,
            'orders_this_month': orders_this_month,
            'total_spent': total_spent,
        }
        
        return render(request, 'orders/user_profile.html', context)
        
    except Exception as e:
        logger.error(f"Error in user profile view: {str(e)}")
        messages.error(request, "Error loading profile. Please try again.")
        return redirect('home')

@login_required
def edit_profile(request):
    """Edit user profile"""
    if request.method == 'POST':
        try:
            # Get or create user profile
            user_profile, created = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={'phone_number': ''}
            )
            
            # Update phone number
            phone = request.POST.get('phone_number')
            if phone and phone != user_profile.phone_number:
                if validate_phone_number(phone):
                    user_profile.phone_number = phone
                    user_profile.save()
                    messages.success(request, "Phone number updated successfully!")
                else:
                    messages.error(request, "Invalid phone number format.")
            
            # Update preferred college
            college_id = request.POST.get('preferred_college')
            if college_id:
                try:
                    college = College.objects.get(id=college_id)
                    user_profile.preferred_college = college
                    user_profile.save()
                    messages.success(request, "Preferred college updated successfully!")
                except College.DoesNotExist:
                    messages.error(request, "Selected college not found.")
            
            return redirect('user_profile')
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            messages.error(request, "Error updating profile. Please try again.")
            return redirect('user_profile')
    
    # GET request - show edit form
    colleges = College.objects.filter(is_active=True)
    try:
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'phone_number': ''}
        )
    except UserProfile.DoesNotExist:
        user_profile = None
    
    return render(request, 'orders/edit_profile.html', {
        'user_profile': user_profile,
        'colleges': colleges
    })

@require_GET
def check_active_orders(request):
    """Check if user has any active orders for the tracking bar"""
    if not request.user.is_authenticated:
        return JsonResponse({'has_active_order': False})
    
    try:
        # Get the most recent active order for the user
        active_order = Order.objects.filter(
            user=request.user,
            status__in=['Pending', 'Accepted', 'In Progress', 'Ready']
        ).order_by('-created_at').first()
        
        if active_order:
            order_data = {
                'id': active_order.id,
                'status': active_order.status,
                'created_at': active_order.created_at.isoformat(),
                'estimated_time': active_order.estimated_time,
                'college_name': active_order.college.name if active_order.college else 'Unknown',
                'total_amount': float(active_order.total_amount) if active_order.total_amount else 0.0
            }
            
            return JsonResponse({
                'has_active_order': True,
                'order': order_data
            })
        else:
            return JsonResponse({'has_active_order': False})
            
    except Exception as e:
        logger.error(f"Error checking active orders: {e}")
        return JsonResponse({'has_active_order': False})

@require_GET
def check_order_status(request, order_id):
    """Check order status for tracking updates"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user has permission to view this order
        if not request.user.is_authenticated or order.user != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        order_data = {
            'id': order.id,
            'status': order.status,
            'created_at': order.created_at.isoformat(),
            'estimated_time': order.estimated_time,
            'college_name': order.college.name if order.college else 'Unknown',
            'total_amount': float(order.total_amount) if order.total_amount else 0.0
        }
        
        return JsonResponse({
            'success': True,
            'order': order_data
        })
        
    except Exception as e:
        logger.error(f"Error checking order status: {e}")
        return JsonResponse({'error': 'Order not found'}, status=404)

@csrf_exempt
def check_active_orders(request):
    """Check for active orders for the current user - used for order tracking bar"""
    if not request.user.is_authenticated:
        return JsonResponse({'has_active_order': False})
    
    try:
        # Get user's active orders (not completed)
        active_orders = Order.objects.filter(
            user=request.user,
            status__in=['Pending', 'In Progress', 'Ready']
        ).order_by('-created_at')
        
        if active_orders.exists():
            latest_order = active_orders.first()
            return JsonResponse({
                'has_active_order': True,
                'order': {
                    'id': latest_order.id,
                    'status': latest_order.status,
                    'college_name': latest_order.college.name if latest_order.college else 'Unknown College',
                    'total_price': str(latest_order.total_price),
                    'created_at': latest_order.created_at.isoformat()
                }
            })
        else:
            return JsonResponse({'has_active_order': False})
            
    except Exception as e:
        logger.error(f"Error checking active orders: {e}")
        return JsonResponse({'has_active_order': False})

@csrf_exempt
def check_order_status(request, order_id):
    """Check order status for tracking"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user has permission to view this order
        if request.user.is_authenticated and order.user == request.user:
            return JsonResponse({
                'success': True,
                'order': {
                    'id': order.id,
                    'status': order.status,
                    'college_name': order.college.name if order.college else 'Unknown College',
                    'total_price': str(order.total_price),
                    'created_at': order.created_at.isoformat(),
                    'estimated_time': order.college.estimated_preparation_time if order.college else 15,
                    'items': [
                        {
                            'name': item.menu_item.name,
                            'quantity': item.quantity,
                            'price': str(item.menu_item.price)
                        } for item in order.order_items.all()
                    ]
                }
            })
        else:
            # For phone-based tracking (no user required)
            return JsonResponse({
                'success': True,
                'order': {
                    'id': order.id,
                    'status': order.status,
                    'college_name': order.college.name if order.college else 'Unknown College',
                    'total_price': str(order.total_price),
                    'created_at': order.created_at.isoformat(),
                    'estimated_time': order.college.estimated_preparation_time if order.college else 15,
                    'items': [
                        {
                            'name': item.menu_item.name,
                            'quantity': item.quantity,
                            'price': str(item.menu_item.price)
                        } for item in order.order_items.all()
                    ]
                }
            })
            
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'})
    except Exception as e:
        logger.error(f"Error checking order status: {e}")
        return JsonResponse({'success': False, 'error': 'Error checking order status'})

@csrf_exempt
def check_notifications(request):
    """Check for new notifications for the current user"""
    if not request.user.is_authenticated:
        return JsonResponse({'notifications': []})
    
    try:
        # Get user's phone number
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile or not user_profile.phone_number:
            return JsonResponse({'notifications': []})
        
        # Check for notifications in session
        notification_key = f'user_notification_{user_profile.phone_number}'
        notifications = request.session.get(notification_key, [])
        
        return JsonResponse({'notifications': notifications})
        
    except Exception as e:
        logger.error(f"Error checking notifications: {e}")
        return JsonResponse({'notifications': []})

@csrf_exempt
def dismiss_notification(request, order_id):
    """Dismiss a notification for an order"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    
    try:
        # Get user's phone number
        user_profile = UserProfile.objects.filter(user=request.user).first()
        if not user_profile or not user_profile.phone_number:
            return JsonResponse({'success': False, 'error': 'Phone number not found'})
        
        # Remove notification from session
        notification_key = f'user_notification_{user_profile.phone_number}_{order_id}'
        if notification_key in request.session:
            del request.session[notification_key]
        
        # Also remove from global notifications
        global_notifications_key = 'global_notifications'
        global_notifications = request.session.get(global_notifications_key, [])
        global_notifications = [n for n in global_notifications if n.get('order_id') != order_id]
        request.session[global_notifications_key] = global_notifications
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Error dismissing notification: {e}")
        return JsonResponse({'success': False, 'error': 'Error dismissing notification'})

# Fix the canteen_update_order_status function to ensure it works properly
@csrf_protect
def canteen_update_order_status(request, college_slug, order_id):
    """Update order status with enhanced security and notifications"""
    try:
        college = get_object_or_404(College, slug=college_slug)
        order = get_object_or_404(Order, id=order_id, college=college)
        new_status = request.POST.get('status')
        
        # Check permissions
        try:
            canteen_staff = CanteenStaff.objects.get(
                user=request.user, 
                college=college, 
                is_active=True
            )
        except CanteenStaff.DoesNotExist:
            if not request.user.is_superuser:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if new_status in ['In Progress', 'Ready', 'Completed']:
            old_status = order.status
            order.status = new_status
            order.save()
            
            # Prepare comprehensive notification data for user
            notification_data = {
                'success': True, 
                'message': f'Order #{order.id} status updated to {new_status}!',
                'order_id': order.id,
                'new_status': new_status,
                'old_status': old_status,
                'user_name': order.user_name,
                'college_name': college.name,
                'timestamp': timezone.now().isoformat(),
                'requires_user_action': False,
                'requires_notification': True
            }
            
            # Add specific notification for ready status - requires user action
            if new_status == 'Ready':
                notification_data['user_notification'] = {
                    'title': '🎉 Order Ready for Pickup!',
                    'message': f'Your order #{order.id} is ready for pickup at {college.name}. Please collect it from the canteen.',
                    'type': 'success',
                    'persistent': True,  # This notification won't auto-dismiss
                    'action_required': True,
                    'order_id': order.id,
                    'college_name': college.name
                }
                notification_data['requires_user_action'] = True
                notification_data['status_color'] = 'status-ready'
            elif new_status == 'In Progress':
                notification_data['user_notification'] = {
                    'title': '👨‍🍳 Order Being Prepared',
                    'message': f'Your order #{order.id} is being prepared at {college.name}. We\'ll notify you when it\'s ready!',
                    'type': 'info',
                    'persistent': False,
                    'action_required': False,
                    'order_id': order.id,
                    'college_name': college.name
                }
                notification_data['status_color'] = 'status-preparing'
            elif new_status == 'Completed':
                notification_data['user_notification'] = {
                    'title': '✅ Order Completed',
                    'message': f'Your order #{order.id} has been completed. Thank you for using SkipTheQueue!',
                    'type': 'success',
                    'persistent': False,
                    'action_required': False,
                    'order_id': order.id,
                    'college_name': college.name
                }
                notification_data['status_color'] = 'status-completed'
            
            # Store notification in session for the user to see
            if order.user_phone:
                # Create a session key for this user's notifications
                notification_key = f'order_notification_{order.user_phone}_{order.id}'
                request.session[notification_key] = notification_data
                
                # Also store in a general user notification key for easier retrieval
                user_notification_key = f'user_notification_{order.user_phone}_{order.id}'
                request.session[user_notification_key] = notification_data.get('user_notification', {})
                
                # Store the order in user's active orders for real-time tracking
                active_orders_key = f'active_orders_{order.user_phone}'
                active_orders = request.session.get(active_orders_key, [])
                if order.id not in active_orders:
                    active_orders.append(order.id)
                    request.session[active_orders_key] = active_orders
                
                # Store notification in a global notifications list for real-time access
                global_notifications_key = 'global_notifications'
                global_notifications = request.session.get(global_notifications_key, [])
                global_notifications.append({
                    'user_phone': order.user_phone,
                    'order_id': order.id,
                    'notification': notification_data,
                    'timestamp': timezone.now().isoformat()
                })
                request.session[global_notifications_key] = global_notifications
            
            return JsonResponse(notification_data)
        else:
            return JsonResponse({'error': 'Invalid status'}, status=400)
            
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

# Add these new API endpoints after the existing ones

@require_GET
def cart_count_api(request):
    """API endpoint to get cart count for the current user"""
    try:
        if request.user.is_authenticated:
            # Get cart count from session or database
            cart_count = request.session.get('cart_count', 0)
        else:
            # For anonymous users, get from session
            cart_count = request.session.get('cart_count', 0)
        
        return JsonResponse({
            'success': True,
            'count': cart_count
        })
    except Exception as e:
        logger.error(f"Error getting cart count: {e}")
        return JsonResponse({
            'success': False,
            'count': 0,
            'error': 'Failed to get cart count'
        }, status=500)

@require_GET
def api_cart_count(request):
    """Alternative API endpoint for cart count"""
    return cart_count_api(request)




