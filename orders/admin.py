from django.contrib import admin
from .models import MenuItem, Order, OrderItem, College, Payment, UserProfile, CanteenStaff

admin.site.register(MenuItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(College)

@admin.register(CanteenStaff)
class CanteenStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'college', 'is_active', 'can_accept_orders', 'can_update_status', 'can_view_orders']
    list_filter = ['college', 'is_active', 'can_accept_orders', 'can_update_status', 'can_view_orders']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'college__name']
    list_editable = ['is_active', 'can_accept_orders', 'can_update_status', 'can_view_orders']
