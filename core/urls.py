from django.contrib import admin
from django.urls import path , include
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('orders.urls')),
    path('auth/', include('social_django.urls', namespace='social')),
    path('logout/', LogoutView.as_view(next_page='/'), name='custom_logout'),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
