from django.contrib import admin
from .models import MenuItem, Order, OrderItem, College, Payment, UserProfile, CanteenStaff

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'college', 'category', 'price', 'is_available', 'stock_quantity', 'is_stock_managed']
    list_filter = ['college', 'category', 'is_available', 'is_stock_managed', 'created_at']
    search_fields = ['name', 'description', 'college__name']
    list_editable = ['is_available', 'price', 'stock_quantity', 'is_stock_managed']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['college', 'category', 'name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_name', 'user_phone', 'college', 'status', 'payment_method', 'payment_status', 'total_price', 'created_at']
    list_filter = ['status', 'payment_method', 'payment_status', 'college', 'created_at']
    search_fields = ['user_name', 'user_phone', 'college__name', 'id']
    list_editable = ['status', 'payment_status']
    readonly_fields = ['created_at', 'updated_at', 'total_price']
    ordering = ['-created_at']
    
    def total_price(self, obj):
        return obj.total_price()
    total_price.short_description = 'Total Price'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'menu_item', 'quantity', 'unit_price', 'total_price']
    list_filter = ['order__status', 'menu_item__college']
    search_fields = ['order__user_name', 'menu_item__name']
    readonly_fields = ['total_price']
    
    def total_price(self, obj):
        return obj.total_price
    total_price.short_description = 'Total Price'

@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'admin_name', 'admin_email', 'is_active', 'allow_pay_later', 'payment_gateway_enabled']
    list_filter = ['is_active', 'allow_pay_later', 'payment_gateway_enabled']
    search_fields = ['name', 'admin_name', 'admin_email']
    list_editable = ['is_active', 'allow_pay_later', 'payment_gateway_enabled']
    readonly_fields = ['created_at']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'amount', 'payment_method', 'payment_gateway', 'status', 'completed_at']
    list_filter = ['status', 'payment_method', 'payment_gateway', 'completed_at']
    search_fields = ['order__user_name', 'transaction_id']
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'preferred_college', 'last_login_college', 'created_at']
    list_filter = ['preferred_college', 'last_login_college', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CanteenStaff)
class CanteenStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'college', 'is_active', 'can_accept_orders', 'can_update_status', 'can_view_orders']
    list_filter = ['college', 'is_active', 'can_accept_orders', 'can_update_status', 'can_view_orders']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'college__name']
    list_editable = ['is_active', 'can_accept_orders', 'can_update_status', 'can_view_orders']
