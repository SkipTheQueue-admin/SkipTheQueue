from django.urls import path , include
from . import views
from .views import test_auth , collect_phone

urlpatterns = [
    path('menu/', views.menu, name='menu'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),

    path('', views.home, name='home'),
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('update_cart/<int:item_id>/', views.update_cart, name='update_cart'),
       
    path('canteen-admin/', views.canteen_dashboard, name='canteen_dashboard'),
    path('update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('track-order/', views.track_order, name='track_order'),
    path('accept-order/<int:order_id>/', views.accept_order, name='accept_order'),
    path('decline-order/<int:order_id>/', views.decline_order, name='decline_order'),
    path('logout/', views.custom_logout, name='logout'),
    path('test-auth/', test_auth, name='test-auth'),
    path('collect-phone/', collect_phone, name='collect_phone'),
    path('order-history/', views.order_history, name='order_history'),
    
   

]
