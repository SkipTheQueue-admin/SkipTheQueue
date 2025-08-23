from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    preferred_college = models.ForeignKey('College', on_delete=models.SET_NULL, null=True, blank=True)
    last_login_college = models.ForeignKey('College', on_delete=models.SET_NULL, null=True, blank=True, related_name='last_login_users')
    favorite_items = models.ManyToManyField('MenuItem', blank=True, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.phone_number}"

class College(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # College admin details
    admin_name = models.CharField(max_length=100, default='Admin')
    admin_email = models.EmailField(default='admin@college.com')
    admin_phone = models.CharField(max_length=15, default='+91-0000000000')
    
    # Payment settings
    allow_pay_later = models.BooleanField(default=True, help_text="Allow students to pay later with cash")
    payment_gateway_enabled = models.BooleanField(default=True, help_text="Enable online payment gateway")
    
    # College settings
    estimated_preparation_time = models.IntegerField(default=15, help_text="Default preparation time in minutes")
    
    def __str__(self):
        return self.name

class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_available = models.BooleanField(default=True)
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='menu_items', null=True, blank=True)
    category = models.CharField(max_length=50, default='General')
    image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Stock management
    stock_quantity = models.PositiveIntegerField(default=0, help_text="0 means unlimited")
    is_stock_managed = models.BooleanField(default=False, help_text="Enable stock management for this item")

    def __str__(self):
        return f"{self.name} - {self.college.name if self.college else 'General'}"
    
    @property
    def is_in_stock(self):
        if not self.is_stock_managed:
            return self.is_available
        return self.is_available and self.stock_quantity > 0

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Payment_Pending', 'Payment Pending'),
        ('Paid', 'Paid'),
        ('In Progress', 'In Progress'),
        ('Ready', 'Ready'),
        ('Declined', 'Declined'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('Online', 'Online Payment'),
        ('Cash', 'Pay Later (Cash)'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user_name = models.CharField(max_length=100)
    user_phone = models.CharField(max_length=15)
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    estimated_time = models.IntegerField(default=15, help_text="Estimated time in minutes")
    special_instructions = models.TextField(blank=True)
    
    # Payment fields
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='Online')
    payment_status = models.CharField(max_length=20, default='Pending')
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    payment_signature = models.CharField(max_length=255, blank=True, null=True)
    payment_gateway = models.CharField(max_length=50, blank=True, null=True)
    payment_completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user_name} ({self.status})"

    def total_price(self):
        try:
            return sum(item.item.price * item.quantity for item in self.order_items.all())
        except (AttributeError, TypeError):
            return 0.00
    
    def get_status_color(self):
        status_colors = {
            'Pending': 'bg-yellow-100 text-yellow-800',
            'Payment_Pending': 'bg-orange-100 text-orange-800',
            'Paid': 'bg-blue-100 text-blue-800',
            'In Progress': 'bg-blue-100 text-blue-800',
            'Ready': 'bg-green-100 text-green-800',
            'Declined': 'bg-red-100 text-red-800',
            'Completed': 'bg-gray-100 text-gray-800',
            'Cancelled': 'bg-red-100 text-red-800',
        }
        return status_colors.get(self.status, 'bg-gray-100 text-gray-800')
    
    @property
    def requires_payment(self):
        return self.payment_method == 'Online' and self.payment_status != 'Paid'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    special_notes = models.TextField(blank=True)
    price_at_time = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="Price when order was placed")

    def __str__(self):
        return f"{self.quantity} x {self.item.name} (Order #{self.order.id})"
    
    def total_price(self):
        return self.price_at_time * self.quantity

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.CharField(max_length=20)
    payment_gateway = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    signature = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, default='Pending')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment for Order #{self.order.id} - {self.status}"

class CanteenStaff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='canteen_staff')
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='canteen_staff')
    is_active = models.BooleanField(default=True)
    can_accept_orders = models.BooleanField(default=True)
    can_update_status = models.BooleanField(default=True)
    can_view_orders = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'college']
    
    def __str__(self):
        return f"{self.user.username} - {self.college.name}"
