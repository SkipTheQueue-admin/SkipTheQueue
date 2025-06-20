from django.shortcuts import render , redirect , get_object_or_404
from django.http import HttpResponse
from .models import MenuItem, Order, OrderItem

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test

from django.contrib import messages

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse



@login_required(login_url='/auth/login/google-oauth2/')
def collect_phone(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')

        if phone_number:
            request.session['user_phone'] = phone_number
            return redirect('place_order')  # 👈 go to order placing now!

    return render(request, 'orders/collect_phone.html')


def test_auth(request):
    return HttpResponse(f"✅ You are logged in as: {request.user}")


@require_POST
def update_cart(request, item_id):
    action = request.POST.get('action')
    cart = request.session.get('cart', {})

    if str(item_id) in cart:
        if action == 'increase':
            cart[str(item_id)] += 1
        elif action == 'decrease':
            cart[str(item_id)] -= 1
            if cart[str(item_id)] <= 0:
                del cart[str(item_id)]

    request.session['cart'] = cart
    return redirect('view_cart')


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'orders/order_history.html', {'orders': orders})






@login_required(login_url='/auth/login/google-oauth2/')
def place_order(request):
    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('menu')

    # ✅ Check for stored phone number from session
    user_phone = request.session.get('user_phone')
    if not user_phone:
        return redirect('collect_phone')

    # ✅ Create Order: now linked to the user
    order = Order.objects.create(
        user=request.user,
        user_name=request.user.get_full_name() or request.user.username,
        user_phone=user_phone,
    )

    for item_id, quantity in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            OrderItem.objects.create(order=order, item=item, quantity=quantity)
        except MenuItem.DoesNotExist:
            continue  # Skip missing items

    # ✅ Clean up cart and phone from session
    request.session['cart'] = {}
    request.session.pop('user_phone', None)

    return redirect('order_success', order_id=order.id)



def menu(request):
    
    items = MenuItem.objects.all()
    return render(request, 'orders/menu.html', {'items': items})

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/order_success.html', {'order': order})

def home(request):
    return render(request, 'orders/home.html')
def add_to_cart(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    cart = request.session.get('cart', {})

    if str(item_id) in cart:
        cart[str(item_id)] += 1
    else:
        cart[str(item_id)] = 1

    request.session['cart'] = cart
    messages.success(request, f"✅ {item.name} added to cart!")

    return redirect('menu')
def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0

    for item_id, quantity in cart.items():
        item = get_object_or_404(MenuItem, id=item_id)
        item_total = item.price * quantity
        total += item_total
        cart_items.append({
            'item': item,
            'quantity': quantity,
            'total': item_total,
        })

    return render(request, 'orders/cart.html', {
        'cart_items': cart_items,
        'total': total
    })

def remove_from_cart(request, item_id):
    cart = request.session.get('cart', {})

    if str(item_id) in cart:
        del cart[str(item_id)]
        request.session['cart'] = cart

    return redirect('view_cart')



def canteen_dashboard(request):
    orders = Order.objects.all().order_by('-created_at')
    status_choices = Order._meta.get_field('status').choices
    return render(request, 'orders/canteen_dashboard.html', {
        'orders': orders,
        'status_choices': status_choices
    })

def update_order_status(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status in dict(order.STATUS_CHOICES):  # ✅ corrected here
            order.status = new_status
            order.save()
    return redirect('canteen_dashboard')

def track_order(request):
    phone = request.GET.get('phone')
    if phone:
        orders = Order.objects.filter(user_phone=phone).order_by('-created_at')
    else:
        orders = []
    return render(request, 'orders/track_order.html', {'orders': orders})

@csrf_exempt
def accept_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = "In Progress"
    order.save()
    return redirect('canteen_dashboard')

@csrf_exempt
def decline_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = "Declined"
    order.save()
    return redirect('canteen_dashboard')

def custom_logout(request):
    logout(request)
    return redirect('home')  # or wherever you want to redirect after logout
