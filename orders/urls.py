from django.urls import path, include
from . import views
from django.conf import settings
from .views import test_auth, collect_phone

urlpatterns = [
    # Core pages
    path('', views.home, name='home'),
    path('menu/', views.menu, name='menu'),
    path('cart/', views.view_cart, name='view_cart'),
    path('favorites/', views.favorites, name='favorites'),
    
    # College registration and selection
    path('register-college/', views.register_college, name='register_college'),
    path('college/<slug:college_slug>/', views.select_college, name='select_college'),
    
    # Cart operations
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', views.update_cart, name='update_cart'),
    
    # Favorite operations
    path('toggle-favorite/<int:item_id>/', views.toggle_favorite, name='toggle_favorite'),
    
    # Order management
    path('place-order/', views.place_order, name='place_order'),
    path('process-payment/<int:order_id>/', views.process_payment, name='process_payment'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('order-history/', views.order_history, name='order_history'),
    path('track-order/', views.track_order, name='track_order'),
    
    # Phone collection
    path('collect-phone/', collect_phone, name='collect_phone'),
    path('test-collect-phone/', views.test_collect_phone, name='test_collect_phone'),
    
    # College Admin Dashboard
    path('college-admin/<slug:college_slug>/', views.college_admin_dashboard, name='college_admin_dashboard'),
    path('manage-menu/<slug:college_slug>/', views.manage_menu, name='manage_menu'),
    
    # Canteen Staff Dashboard (Legacy - keeping for backward compatibility)
    path('canteen/<slug:college_slug>/', views.canteen_dashboard, name='canteen_dashboard'),
    path('canteen/<slug:college_slug>/update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('canteen/<slug:college_slug>/accept-order/<int:order_id>/', views.accept_order, name='accept_order'),
    path('canteen/<slug:college_slug>/decline-order/<int:order_id>/', views.decline_order, name='decline_order'),
    
    # New Canteen Staff Authentication and Management System
    path('canteen/login/', views.canteen_staff_login, name='canteen_staff_login'),
    path('canteen/logout/', views.canteen_staff_logout, name='canteen_staff_logout'),
    path('canteen/dashboard/<slug:college_slug>/', views.canteen_staff_dashboard, name='canteen_staff_dashboard'),
    path('canteen/dashboard/<slug:college_slug>/accept-order/<int:order_id>/', views.canteen_accept_order, name='canteen_accept_order'),
    path('canteen/dashboard/<slug:college_slug>/decline-order/<int:order_id>/', views.canteen_decline_order, name='canteen_decline_order'),
    path('canteen/dashboard/<slug:college_slug>/update-status/<int:order_id>/', views.canteen_update_order_status, name='canteen_update_order_status'),
    path('canteen/dashboard/<slug:college_slug>/menu/', views.canteen_manage_menu, name='canteen_manage_menu'),
    path('canteen/dashboard/<slug:college_slug>/history/', views.canteen_order_history, name='canteen_order_history'),
    
    # API endpoints
    path('api/orders/<slug:college_slug>/', views.get_orders_json, name='get_orders_json'),
    path('api/update_cart/<int:item_id>/', views.update_cart_api, name='update_cart_api'),
    path('api/check-order-status/<int:order_id>/', views.check_order_status, name='check_order_status'),
    path('api/check-active-orders/', views.check_active_orders, name='check_active_orders'),
    path('api/cart-count/', views.cart_count_api, name='cart_count_api'),
    path('check-order-status/', views.check_order_status_main, name='check_order_status_main'),
    path('check-notifications/', views.check_notifications, name='check_notifications'),
    path('api/update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('api/dismiss-notification/<int:order_id>/', views.dismiss_notification, name='dismiss_notification'),
    
    # Notification and order status endpoints
    path('check-order-status/<str:user_phone>/', views.check_order_status_by_phone, name='check_order_status_by_phone'),
    path('dismiss-notification/<int:order_id>/', views.dismiss_notification, name='dismiss_notification'),
    path('order-status-update/<int:order_id>/', views.order_status_update, name='order_status_update'),
    
    # PWA
    path('manifest.json', views.pwa_manifest, name='pwa_manifest'),
    path('sw.js', views.pwa_service_worker, name='pwa_service_worker'),
    
    # Authentication
    path('login/', views.custom_login, name='custom_login'),
    path('oauth-complete/', views.oauth_complete, name='oauth_complete'),
    path('logout/', views.custom_logout, name='logout'),
    path('test-auth/', test_auth, name='test-auth'),
    
    # User Profile
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Help Center, Privacy Policy, and Terms of Service
    path('help-center/', views.help_center, name='help_center'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    
    # Super Admin Dashboard
    path('admin-dashboard/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('admin-dashboard/college/<int:college_id>/', views.manage_college, name='manage_college'),
    path('admin-dashboard/menu-items/', views.manage_menu_items, name='manage_menu_items'),
    path('admin-dashboard/delete-college/<int:college_id>/', views.delete_college, name='delete_college'),
    path('admin-dashboard/order-history/', views.view_order_history, name='view_order_history'),
]

# Debug and diagnostic routes only in DEBUG
if settings.DEBUG:
    from . import views as _views
    from .views import create_temp_superuser, debug_canteen_staff
    urlpatterns += [
        path('create-temp-superuser/', create_temp_superuser),
        path('debug-canteen-staff/', debug_canteen_staff),
        path('security-test/', _views.security_test, name='security_test'),
        path('debug-home/', _views.debug_home, name='debug_home'),
        path('health/', _views.health_check, name='health_check'),
        path('diagnostic/', _views.site_diagnostic, name='site_diagnostic'),
        path('error-monitoring/', _views.error_monitoring_dashboard, name='error_monitoring_dashboard'),
    ]
