from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from .models import MenuItem, Order, OrderItem, College, Payment, UserProfile, CanteenStaff

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test

from django.contrib import messages

from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.urls import reverse
from django.db.models import Q, Count
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.views.decorators.vary import vary_on_cookie
from datetime import timedelta
import json
import uuid
import re
import hashlib
import hmac
from functools import wraps
import logging
from core.security import SecurityValidator, SessionSecurity

logger = logging.getLogger(__name__)

# Security decorators and utilities
def rate_limit(max_requests=10, window=60):
    """Rate limiting decorator"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            # Simple rate limiting using session
            now = timezone.now()
            request_count = request.session.get('request_count', 0)
            last_request_str = request.session.get('last_request')
            
            if last_request_str:
                try:
                    last_request = timezone.datetime.fromisoformat(last_request_str.replace('Z', '+00:00'))
                    time_diff = (now - last_request).seconds
                    if time_diff > window:
                        request_count = 0
                except (ValueError, TypeError):
                    # If there's an error parsing the datetime, reset
                    request_count = 0
            
            if request_count >= max_requests:
                return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
            
            request.session['request_count'] = request_count + 1
            request.session['last_request'] = now.isoformat()
            
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
    """Decorator to check if user is canteen staff for the college"""
    @wraps(view_func)
    def wrapped(request, college_slug, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('custom_login')
        
        try:
            college = College.objects.get(slug=college_slug)
            canteen_staff = CanteenStaff.objects.filter(
                user=request.user,
                college=college,
                is_active=True
            ).first()
            
            # Superuser can access any college
            if request.user.is_superuser:
                return view_func(request, college_slug, *args, **kwargs)
            
            # Check if user is canteen staff for this college
            if not canteen_staff:
                messages.error(request, "Access denied. You don't have permission to access this college's dashboard.")
                return redirect('home')
            
            return view_func(request, college_slug, *args, **kwargs)
            
        except College.DoesNotExist:
            messages.error(request, "College not found.")
            return redirect('home')
    
    return wrapped

@login_required(login_url='/login/?next=/collect-phone/')
@csrf_protect
def collect_phone(request):
    """Collect phone number for order with profile update"""
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('menu')
    valid_items = []
    for item_id, quantity in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            if item.is_available:
                valid_items.append((item, quantity))
        except MenuItem.DoesNotExist:
            continue
    if not valid_items:
        messages.error(request, "No valid items in your cart.")
        return redirect('menu')
    if request.method == 'POST':
        phone = SecurityValidator.sanitize_input(request.POST.get('phone'))
        payment_method = request.POST.get('payment_method', 'Online')
        is_valid, phone_result = SecurityValidator.validate_phone_number(phone)
        if not is_valid:
            messages.error(request, f"Please enter a valid phone number: {phone_result}")
            cart = request.session.get('cart', {})
            menu_items = []
            total = 0
            for item_id, quantity in cart.items():
                try:
                    item = MenuItem.objects.get(id=item_id)
                    item_total = item.price * quantity
                    menu_items.append({
                        'id': item.id,
                        'name': item.name,
                        'price': item.price,
                        'quantity': quantity,
                        'total': item_total
                    })
                    total += item_total
                except MenuItem.DoesNotExist:
                    continue
            selected_college = request.session.get('selected_college')
            college = None
            if selected_college and isinstance(selected_college, dict) and 'id' in selected_college:
                try:
                    college = College.objects.get(id=selected_college['id'])
                except College.DoesNotExist:
                    pass
            return render(request, 'orders/collect_phone.html', {
                'menu_items': menu_items,
                'total': total,
                'college': college
            })
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
    # GET request: render form with context
    cart = request.session.get('cart', {})
    menu_items = []
    total = 0
    for item_id, quantity in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            item_total = item.price * quantity
            menu_items.append({
                'id': item.id,
                'name': item.name,
                'price': item.price,
                'quantity': quantity,
                'total': item_total
            })
            total += item_total
        except MenuItem.DoesNotExist:
            continue
    selected_college = request.session.get('selected_college')
    college = None
    if selected_college and isinstance(selected_college, dict) and 'id' in selected_college:
        try:
            college = College.objects.get(id=selected_college['id'])
        except College.DoesNotExist:
            pass
    return render(request, 'orders/collect_phone.html', {
        'menu_items': menu_items,
        'total': total,
        'college': college
    })

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
    """Test authentication"""
    return HttpResponse(f"✅ You are logged in as: {request.user}")

@csrf_exempt
@require_POST
def update_cart_api(request, item_id):
    import logging
    logger = logging.getLogger(__name__)
    try:
        cart = request.session.get('cart', {})
        if not isinstance(cart, dict):
            logger.warning('Cart session corrupted: not a dict')
            cart = {}
        cart = {str(k): v for k, v in cart.items()}
        action = request.POST.get('action')
        logger.info(f'Cart action: {action} for item {item_id}')
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
        request.session['cart'] = cart
        request.session.modified = True
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
        logger.info(f'Cart updated: {cart}')
        return JsonResponse({
            'success': True,
            'cart_items': cart_items,
            'cart_total': float(cart_total),
            'cart_count': len(cart_items),
            'message': 'Cart updated successfully'
        })
    except Exception as e:
        logger.error(f'Cart update error: {str(e)}')
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
@rate_limit(max_requests=5, window=300)  # 5 orders per 5 minutes
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

def home(request):
    """Home page with auto-redirect based on user email and enhanced security"""
    # Auto-redirect logic for logged-in users
    if request.user.is_authenticated:
        user_email = request.user.email
        
        # Log access attempt for security monitoring
        logger.info(f"User {request.user.username} ({user_email}) accessed home page")
        
        # Check if user is the main admin (only if they are actually superuser)
        if user_email == 'skipthequeue.app@gmail.com' and request.user.is_superuser:
            logger.info(f"Super admin {user_email} redirected to super admin dashboard")
            return redirect('super_admin_dashboard')
        elif user_email == 'skipthequeue.app@gmail.com' and not request.user.is_superuser:
            # Security alert: someone with admin email but not superuser status
            logger.warning(f"Security alert: User {user_email} has admin email but not superuser status")
            messages.warning(request, "Access restricted. Please contact administrator.")
        
        # Check if user is canteen staff for any college
        try:
            canteen_staff = CanteenStaff.objects.get(user=request.user, is_active=True)
            logger.info(f"Canteen staff {user_email} redirected to {canteen_staff.college.name} dashboard")
            return redirect('canteen_staff_dashboard', college_slug=canteen_staff.college.slug)
        except CanteenStaff.DoesNotExist:
            # Regular user - continue to normal home page
            logger.info(f"Regular user {user_email} accessing home page")
            pass
    
    colleges = College.objects.filter(is_active=True)
    
    # Get selected college from session
    selected_college = request.session.get('selected_college')
    
    context = {
        'colleges': colleges,
        'selected_college': selected_college,
    }
    return render(request, 'orders/home.html', context)

@never_cache
@vary_on_cookie
def menu(request):
    """Menu page - requires college selection but not login"""
    # Check if college is selected
    selected_college = request.session.get('selected_college')
    if not selected_college:
        messages.warning(request, "Please select a college first.")
        return redirect('home')
    
    try:
        college = College.objects.get(id=selected_college['id'])
    except College.DoesNotExist:
        messages.error(request, "Selected college not found.")
        return redirect('home')
    
    # Get search query
    search_query = request.GET.get('search', '').strip()
    
    # Get menu items for the college
    menu_items = MenuItem.objects.filter(
        college=college,
        is_available=True
    ).order_by('category', 'name')
    
    # Apply search filter
    if search_query:
        menu_items = menu_items.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    # Get cart items for display
    cart = request.session.get('cart', {})
    cart_items = []
    cart_total = 0
    
    for item_id, quantity in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            cart_items.append({
                'item': item,
                'quantity': quantity,
                'total': item.price * quantity
            })
            cart_total += item.price * quantity
        except MenuItem.DoesNotExist:
            continue
    
    # Get favorite items if user is logged in
    favorite_items = []
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            favorite_items = user_profile.favorite_items.filter(college=college)
        except UserProfile.DoesNotExist:
            pass
    
    context = {
        'college': college,
        'menu_items': menu_items,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': len(cart_items),
        'search_query': search_query,
        'favorite_items': favorite_items,
        'categories': menu_items.values_list('category', flat=True).distinct(),
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
@rate_limit(max_requests=5, window=300)  # 5 requests per 5 minutes
def register_college(request):
    """College registration form with security"""
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
@rate_limit(max_requests=20, window=60)  # 20 requests per minute
def add_to_cart(request, item_id):
    """Add item to cart - no login required, login only needed for checkout"""
    # Check if college is selected
    selected_college = request.session.get('selected_college')
    if not selected_college:
        messages.warning(request, "Please select a college first.")
        return redirect('home')
    
    try:
        item = MenuItem.objects.get(id=item_id)
        
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
                    'quantity': quantity,
                    'total': cart_item.price * quantity
                })
                cart_total += cart_item.price * quantity
            except MenuItem.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'message': f"{item.name} added to cart!",
            'cart_count': len(cart_items),
            'cart_total': cart_total,
            'cart_items': cart_items
        })
    
    messages.success(request, f"{item.name} added to cart!")
    return redirect('menu')

@never_cache
@ensure_csrf_cookie
@csrf_protect
def view_cart(request):
    """Enhanced cart with payment options - no login required to view"""
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    selected_college = request.session.get('selected_college')

    # Clean up invalid items from cart
    items_to_remove = []
    for item_id, quantity in cart.items():
        try:
            item = get_object_or_404(MenuItem, id=item_id)
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
        except Exception as e:
            items_to_remove.append(item_id)
            continue
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
    # Save session explicitly
    request.session.modified = True
    user_authenticated = request.user.is_authenticated
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
        'user_authenticated': user_authenticated
    })

@require_POST
@csrf_protect
@rate_limit(max_requests=30, window=60)
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart = request.session.get('cart', {})
    if str(item_id) in cart:
        del cart[str(item_id)]
        request.session['cart'] = cart
        messages.success(request, "Item removed from cart!")
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
    """Custom login view that handles both OAuth and email-based login"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    from django.contrib.auth import login
                    login(request, user)
                    next_url = request.GET.get('next', '/')
                    return redirect(next_url)
                else:
                    messages.error(request, "Invalid password.")
            except User.DoesNotExist:
                messages.error(request, "User with this email does not exist.")
        else:
            messages.error(request, "Please provide both email and password.")
    
    next_url = request.GET.get('next', '/')
    
    # Store the next URL in session for after login
    request.session['next_url'] = next_url
    
    # If it's a GET request, show the login form
    return render(request, 'orders/login.html', {'next': next_url})

def oauth_complete(request):
    """Handle redirect after successful OAuth login"""
    if request.user.is_authenticated:
        # Get the stored next URL from session
        next_url = request.session.get('next_url', '/')
        # Clear the stored URL
        request.session.pop('next_url', None)
        
        # If user is on cart page and doesn't have phone number, redirect to collect_phone
        if (next_url == '/cart/' or next_url == '/cart') and not request.session.get('user_phone'):
            return redirect('collect_phone')
        
        # If user is trying to place an order and phone is missing, redirect to collect_phone
        if (
            next_url in ['/place-order/', '/place_order/', 'place_order', 'place-order'] or
            next_url.endswith('/place-order/') or next_url.endswith('/place_order/')
        ) and not request.session.get('user_phone'):
            return redirect('collect_phone')
        
        return redirect(next_url)
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
@rate_limit(max_requests=60, window=60)  # 60 requests per minute
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
    # Check if user is superuser
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super admin privileges required.")
        return redirect('home')
    
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
    # Check if user is superuser
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super admin privileges required.")
        return redirect('home')
    
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
    """PWA manifest for mobile app installation"""
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

@login_required(login_url='/admin/login/')
@require_POST
@csrf_protect
def update_order_status(request, order_id):
    """Update order status for canteen staff"""
    # Check if user is superuser
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Access denied. Super admin privileges required.'}, status=403)
    
    try:
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            return JsonResponse({'success': True, 'status': new_status})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid status'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

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
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super admin privileges required.")
        return redirect('home')
    
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
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super admin privileges required.")
        return redirect('home')
    
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
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super admin privileges required.")
        return redirect('home')
    
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
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super admin privileges required.")
        return redirect('home')
    
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
    from django.contrib.auth import logout, login
    
    # If user is already authenticated, check if they are valid canteen staff
    if request.user.is_authenticated:
        try:
            canteen_staff = CanteenStaff.objects.get(user=request.user, is_active=True)
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
                try:
                    # Check if user is authorized as canteen staff
                    canteen_staff = CanteenStaff.objects.get(user=user, is_active=True)
                    login(request, user)
                    request.session.save()  # Force session save
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
    from django.contrib.auth import logout
    
    try:
        # Get the user's assigned canteen staff record
        try:
            canteen_staff = CanteenStaff.objects.get(user=request.user, is_active=True)
        except CanteenStaff.DoesNotExist:
            logout(request)
            messages.error(request, "Access denied. You are not authorized as canteen staff.")
            return redirect('canteen_staff_login')
        
        # Get the assigned college
        assigned_college = canteen_staff.college
        
        # If URL slug doesn't match assigned college, redirect to correct dashboard
        if college_slug != assigned_college.slug:
            return redirect('canteen_staff_dashboard', college_slug=assigned_college.slug)
        
        college = assigned_college
        
        # Check if user has permission (superuser can access any college)
        if not (request.user.is_superuser or is_canteen_staff(request.user, college)):
            logout(request)
            messages.error(request, "Access denied. You don't have permission to access this college's dashboard.")
            return redirect('canteen_staff_login')
        
        print(f"DEBUG: User {request.user.username} is authorized for college {college.name}")
        
        # Get orders with different statuses using efficient queries
        active_orders = Order.objects.filter(
            college=college,
            status__in=['Paid', 'In Progress', 'Ready']
        ).select_related('user').order_by('-created_at')
        
        pending_orders = Order.objects.filter(
            college=college,
            status='Paid'
        ).select_related('user').order_by('-created_at')
        
        in_progress_orders = Order.objects.filter(
            college=college,
            status='In Progress'
        ).select_related('user').order_by('-created_at')
        
        ready_orders = Order.objects.filter(
            college=college,
            status='Ready'
        ).select_related('user').order_by('-created_at')
        
        # Get today's orders
        today = timezone.now().date()
        today_orders = Order.objects.filter(
            college=college,
            created_at__date=today
        )
        
        # Get statistics
        total_today = today_orders.count()
        completed_today = today_orders.filter(status='Completed').count()
        total_revenue_today = sum(order.total_price() for order in today_orders.filter(status='Completed'))
        
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
@rate_limit(max_requests=10, window=60)
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
@rate_limit(max_requests=10, window=60)
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

@login_required(login_url='/canteen/login/')
@require_POST
@csrf_protect
@rate_limit(max_requests=10, window=60)
def canteen_update_order_status(request, college_slug, order_id):
    """Update order status with enhanced security"""
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
            order.status = new_status
            order.save()
            
            # Prepare notification data for user
            notification_data = {
                'success': True, 
                'message': f'Order #{order.id} status updated to {new_status}!',
                'order_id': order.id,
                'new_status': new_status,
                'user_name': order.user_name,
                'college_name': college.name
            }
            
            # Add specific notification for ready status
            if new_status == 'Ready':
                notification_data['user_notification'] = {
                    'title': 'Order Ready! 🎉',
                    'message': f'Your order #{order.id} is ready for pickup at {college.name}!',
                    'type': 'success'
                }
            elif new_status == 'In Progress':
                notification_data['user_notification'] = {
                    'title': 'Order Being Prepared 👨‍🍳',
                    'message': f'Your order #{order.id} is being prepared at {college.name}.',
                    'type': 'info'
                }
            
            return JsonResponse(notification_data)
        else:
            return JsonResponse({'error': 'Invalid status'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': 'Error updating order status'}, status=500)

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
        
        context = {
            'college': college,
            'menu_items': menu_items,
            'canteen_staff': canteen_staff if 'canteen_staff' in locals() else None
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
            password='Paras@999stq'
        )
        return HttpResponse("✅ Superuser created! Email: skipthequeue.app@gmail.com, Password: Paras@999stq")
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
