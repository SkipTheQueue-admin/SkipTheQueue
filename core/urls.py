from django.contrib import admin
from django.urls import path , include
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('orders.urls')),
    path('auth/', include('social_django.urls', namespace='social')),
    path('logout/', LogoutView.as_view(next_page='/'), name='custom_logout'),
   ]
