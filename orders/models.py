from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.core.cache import cache
from django.db.models import Q
from django.core.exceptions import ValidationError
import re

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(
        max_length=15, 
        blank=True, 
        null=True, 
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9\-\s]+$',
                message='Phone number must contain only digits, spaces, hyphens, and optionally start with +'
            )
        ]
    )
    preferred_college = models.ForeignKey('College', on_delete=models.SET_NULL, null=True, blank=True)
    last_login_college = models.ForeignKey('College', on_delete=models.SET_NULL, null=True, blank=True, related_name='last_login_users')
    favorite_items = models.ManyToManyField('MenuItem', blank=True, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'preferred_college']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.phone_number or 'No phone'}"
    
    def clean(self):
        """Validate the model"""
        if self.phone_number:
            # Remove any non-digit characters except + for validation
            clean_phone = re.sub(r'[^\d+]', '', self.phone_number)
            if len(clean_phone) < 10 or len(clean_phone) > 15:
                raise ValidationError('Phone number must be between 10 and 15 digits')
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation and clear cache"""
        self.clean()
        super().save(*args, **kwargs)
        
        # Clear cache when profile is updated
        cache_key = f'user_profile_{self.user.id}'
        cache.delete(cache_key)
    
    @classmethod
    def get_cached_profile(cls, user_id):
        """Get user profile with caching for better performance"""
        cache_key = f'user_profile_{user_id}'
        profile = cache.get(cache_key)
        
        if profile is None:
            try:
                profile = cls.objects.select_related('preferred_college').get(user_id=user_id)
                cache.set(cache_key, profile, 300)  # Cache for 5 minutes
            except cls.DoesNotExist:
                profile = None
        
        return profile

class College(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, db_index=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # College admin details
    admin_name = models.CharField(max_length=100, default='Admin')
    admin_email = models.EmailField(default='admin@college.com', db_index=True)
    admin_phone = models.CharField(
        max_length=15, 
        default='+91-0000000000',
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9\-\s]+$',
                message='Phone number must contain only digits, spaces, hyphens, and optionally start with +'
            )
        ]
    )
    
    # Payment settings
    allow_pay_later = models.BooleanField(default=True, help_text="Allow students to pay later with cash")
    payment_gateway_enabled = models.BooleanField(default=True, help_text="Enable online payment gateway")
    
    # College settings
    estimated_preparation_time = models.IntegerField(
        default=15, 
        help_text="Default preparation time in minutes",
        validators=[
            MinValueValidator(5, message="Preparation time must be at least 5 minutes"),
            MaxValueValidator(120, message="Preparation time cannot exceed 120 minutes")
        ]
    )
    
    class Meta:
        verbose_name = 'College'
        verbose_name_plural = 'Colleges'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['admin_email']),
            models.Index(fields=['is_active', 'name']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate the model"""
        if self.estimated_preparation_time < 5:
            raise ValidationError('Estimated preparation time must be at least 5 minutes')
        
        if self.estimated_preparation_time > 120:
            raise ValidationError('Estimated preparation time cannot exceed 120 minutes')
        
        # Validate phone number format
        if self.admin_phone:
            clean_phone = re.sub(r'[^\d+]', '', self.admin_phone)
            if len(clean_phone) < 10 or len(clean_phone) > 15:
                raise ValidationError('Admin phone number must be between 10 and 15 digits')
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation and clear cache"""
        self.clean()
        super().save(*args, **kwargs)
        
        # Clear cache when college is updated
        cache_key = f'college_{self.slug}'
        cache.delete(cache_key)
    
    @classmethod
    def get_cached_college(cls, slug):
        """Get college with caching for better performance"""
        cache_key = f'college_{slug}'
        college = cache.get(cache_key)
        
        if college is None:
            try:
                college = cls.objects.get(slug=slug, is_active=True)
                cache.set(cache_key, college, 300)  # Cache for 5 minutes
            except cls.DoesNotExist:
                college = None
        
        return college

class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
        ('Snacks', 'Snacks'),
        ('Beverages', 'Beverages'),
        ('Desserts', 'Desserts'),
        ('General', 'General'),
    ]
    
    name = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        db_index=True,
        validators=[
            MinValueValidator(0.01, message="Price must be at least ₹0.01"),
            MaxValueValidator(9999.99, message="Price cannot exceed ₹9,999.99")
        ]
    )
    is_available = models.BooleanField(default=True, db_index=True)
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='menu_items', null=True, blank=True, db_index=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General', db_index=True)
    image_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Stock management
    stock_quantity = models.PositiveIntegerField(
        default=0, 
        help_text="0 means unlimited",
        validators=[
            MaxValueValidator(99999, message="Stock quantity cannot exceed 99,999")
        ]
    )
    is_stock_managed = models.BooleanField(default=False, help_text="Enable stock management for this item")

    class Meta:
        ordering = ['college', 'category', 'name']
        verbose_name = 'Menu Item'
        verbose_name_plural = 'Menu Items'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['price']),
            models.Index(fields=['is_available']),
            models.Index(fields=['college']),
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
            models.Index(fields=['college', 'category']),
            models.Index(fields=['college', 'is_available']),
            models.Index(fields=['is_available', 'category']),
            models.Index(fields=['college', 'is_available', 'category']),
            models.Index(fields=['name', 'college']),
            models.Index(fields=['is_stock_managed', 'stock_quantity']),
        ]

    def __str__(self):
        return f"{self.name} - {self.college.name if self.college else 'General'}"
    
    @property
    def is_in_stock(self):
        if not self.is_stock_managed:
            return self.is_available
        return self.is_available and self.stock_quantity > 0
    
    def clean(self):
        """Validate the model"""
        if self.price < 0.01:
            raise ValidationError('Price must be at least ₹0.01')
        
        if self.price > 9999.99:
            raise ValidationError('Price cannot exceed ₹9,999.99')
        
        if self.is_stock_managed and self.stock_quantity < 0:
            raise ValidationError('Stock quantity cannot be negative')
        
        if self.is_stock_managed and self.stock_quantity > 99999:
            raise ValidationError('Stock quantity cannot exceed 99,999')
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation and clear cache"""
        self.clean()
        super().save(*args, **kwargs)
        
        # Clear cache when menu item is updated
        if self.college:
            cache_key = f'menu_items_{self.college.id}'
            cache.delete(cache_key)
    
    @classmethod
    def get_cached_menu_items(cls, college_id, category=None):
        """Get menu items with caching for better performance"""
        cache_key = f'menu_items_{college_id}'
        if category:
            cache_key += f'_{category}'
        
        menu_items = cache.get(cache_key)
        
        if menu_items is None:
            queryset = cls.objects.filter(college_id=college_id, is_available=True)
            if category:
                queryset = queryset.filter(category=category)
            menu_items = list(queryset.select_related('college').order_by('category', 'name'))
            cache.set(cache_key, menu_items, 300)  # Cache for 5 minutes
        
        return menu_items

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
    
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    user_name = models.CharField(max_length=100, db_index=True)
    user_phone = models.CharField(max_length=15, db_index=True)
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    estimated_time = models.IntegerField(default=15, help_text="Estimated time in minutes")
    special_instructions = models.TextField(blank=True)
    
    # Payment fields
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='Online', db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending', db_index=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    payment_signature = models.CharField(max_length=255, blank=True, null=True)
    payment_gateway = models.CharField(max_length=50, blank=True, null=True)
    payment_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['user_name']),
            models.Index(fields=['user_phone']),
            models.Index(fields=['college']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['college', 'status']),
            models.Index(fields=['user_phone', 'status']),
            models.Index(fields=['created_at', 'status']),
            models.Index(fields=['payment_status', 'created_at']),
            models.Index(fields=['college', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.user_name} ({self.status})"

    def total_price(self):
        """Calculate total price of all items in the order - optimized"""
        # Use cached total if available
        cache_key = f'order_total_{self.id}'
        total = cache.get(cache_key)
        
        if total is None:
            total = sum(item.total_price() for item in self.order_items.all())
            cache.set(cache_key, total, 300)  # Cache for 5 minutes
        
        return total
    
    def get_status_color(self):
        """Get CSS classes for status styling"""
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
    
    def save(self, *args, **kwargs):
        """Override save to clear cache when order is updated"""
        super().save(*args, **kwargs)
        
        # Clear related caches
        cache.delete(f'order_total_{self.id}')
        if self.user_phone:
            cache.delete(f'active_orders_{self.user_phone}')
    
    @classmethod
    def get_cached_orders(cls, college_id, status=None, limit=None):
        """Get orders with caching for better performance"""
        cache_key = f'orders_{college_id}'
        if status:
            cache_key += f'_{status}'
        if limit:
            cache_key += f'_limit_{limit}'
        
        orders = cache.get(cache_key)
        
        if orders is None:
            queryset = cls.objects.filter(college_id=college_id)
            if status:
                queryset = queryset.filter(status=status)
            if limit:
                queryset = queryset[:limit]
            
            orders = list(queryset.select_related('college', 'user').prefetch_related('order_items__menu_item'))
            cache.set(cache_key, orders, 300)  # Cache for 5 minutes
        
        return orders
    
    @property
    def requires_payment(self):
        """Check if order requires payment"""
        return self.payment_method == 'Online' and self.payment_status != 'Completed'
    
    @property
    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in ['Pending', 'Payment_Pending', 'Paid']
    
    @property
    def is_active(self):
        """Check if order is still active (not completed/cancelled)"""
        return self.status not in ['Completed', 'Cancelled', 'Declined']
    
    def clean(self):
        """Validate the model"""
        if self.estimated_time < 0:
            raise ValidationError('Estimated time cannot be negative')
        
        if self.amount_paid and self.amount_paid < 0:
            raise ValidationError('Amount paid cannot be negative')
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation"""
        self.clean()
        super().save(*args, **kwargs)

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items', db_index=True)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, db_index=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=6, decimal_places=2)
    total_price = models.DecimalField(max_digits=8, decimal_places=2)
    special_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['menu_item']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} for Order #{self.order.id}"

    def save(self, *args, **kwargs):
        """Override save to calculate total price and clear cache"""
        if not self.total_price:
            self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
        
        # Clear order total cache when item is updated
        if self.order:
            cache.delete(f'order_total_{self.order.id}')
    
    def delete(self, *args, **kwargs):
        """Override delete to clear cache"""
        order_id = self.order.id if self.order else None
        super().delete(*args, **kwargs)
        
        # Clear order total cache when item is deleted
        if order_id:
            cache.delete(f'order_total_{order_id}')

class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
        ('Cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('Online', 'Online Payment'),
        ('Cash', 'Cash Payment'),
        ('Card', 'Card Payment'),
        ('UPI', 'UPI Payment'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_gateway = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    signature = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment for Order #{self.order.id} - {self.status}"
    
    def clean(self):
        """Validate the model"""
        if self.amount <= 0:
            raise ValidationError('Payment amount must be greater than 0')
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation"""
        self.clean()
        super().save(*args, **kwargs)

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
        verbose_name = 'Canteen Staff'
        verbose_name_plural = 'Canteen Staff'
        ordering = ['college', 'user__username']
    
    def __str__(self):
        return f"{self.user.username} - {self.college.name}"
    
    def clean(self):
        """Validate the model"""
        from django.core.exceptions import ValidationError
        
        # Ensure user is not already staff for another college
        if self.pk:  # Only check on update
            existing_staff = CanteenStaff.objects.filter(
                user=self.user,
                college__isnull=False
            ).exclude(pk=self.pk)
            
            if existing_staff.exists():
                raise ValidationError('User is already staff for another college')
    
    def save(self, *args, **kwargs):
        """Override save to ensure validation"""
        self.clean()
        super().save(*args, **kwargs)
