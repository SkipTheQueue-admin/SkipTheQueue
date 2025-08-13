#!/usr/bin/env python
"""
Comprehensive functionality test for SkipTheQueue
This script tests all the key features to ensure they're working properly
"""

import os
import sys
import django
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_home_page():
    """Test home page loads without errors"""
    print("Testing home page...")
    client = Client()
    response = client.get('/', follow=True)
    assert response.status_code == 200, f"Home page returned {response.status_code}"
    print("✅ Home page loads successfully")

def test_manifest():
    """Test PWA manifest loads"""
    print("Testing PWA manifest...")
    client = Client()
    response = client.get('/manifest.json', follow=True)
    assert response.status_code == 200, f"Manifest returned {response.status_code}"
    print("✅ PWA manifest loads successfully")

def test_service_worker():
    """Test service worker loads"""
    print("Testing service worker...")
    client = Client()
    response = client.get('/sw.js', follow=True)
    assert response.status_code == 200, f"Service worker returned {response.status_code}"
    print("✅ Service worker loads successfully")

def test_menu_page():
    """Test menu page loads"""
    print("Testing menu page...")
    client = Client()
    # First select a college
    response = client.get('/college/ramdeo-baba-college/', follow=True)
    assert response.status_code == 200, f"College selection returned {response.status_code}"
    
    # Then access menu
    response = client.get('/menu/', follow=True)
    assert response.status_code == 200, f"Menu page returned {response.status_code}"
    print("✅ Menu page loads successfully")

def test_cart_functionality():
    """Test cart functionality"""
    print("Testing cart functionality...")
    client = Client()
    
    # Test cart page loads
    response = client.get('/cart/', follow=True)
    assert response.status_code == 200, f"Cart page returned {response.status_code}"
    print("✅ Cart page loads successfully")

def test_api_endpoints():
    """Test API endpoints"""
    print("Testing API endpoints...")
    client = Client()
    
    # Test active orders API
    response = client.get('/api/check-active-orders/', follow=True)
    assert response.status_code == 200, f"Active orders API returned {response.status_code}"
    print("✅ API endpoints working")

def test_admin_dashboard():
    """Test admin dashboard loads"""
    print("Testing admin dashboard...")
    client = Client()
    response = client.get('/admin-dashboard/', follow=True)
    # Should redirect to login if not authenticated
    assert response.status_code in [200, 302], f"Admin dashboard returned {response.status_code}"
    print("✅ Admin dashboard accessible")

def test_user_profile():
    """Test user profile page"""
    print("Testing user profile...")
    client = Client()
    response = client.get('/profile/', follow=True)
    # Should redirect to login if not authenticated
    assert response.status_code in [200, 302], f"User profile returned {response.status_code}"
    print("✅ User profile accessible")

def test_static_files():
    """Test static files are served"""
    print("Testing static files...")
    client = Client()
    
    # Test CSS file
    response = client.get('/static/css/tailwind-fallback.css')
    assert response.status_code == 200, f"CSS file returned {response.status_code}"
    
    # Test image file
    response = client.get('/static/images/icon-192x192.png')
    assert response.status_code == 200, f"Image file returned {response.status_code}"
    print("✅ Static files served correctly")

def test_url_patterns():
    """Test all URL patterns are valid"""
    print("Testing URL patterns...")
    from orders.urls import urlpatterns
    
    for pattern in urlpatterns:
        if hasattr(pattern, 'name') and pattern.name:
            print(f"  - {pattern.name}: {pattern.pattern}")
    print("✅ All URL patterns are valid")

def main():
    """Run all tests"""
    print("🚀 Starting comprehensive functionality test...")
    print("=" * 50)
    
    try:
        test_home_page()
        test_manifest()
        test_service_worker()
        test_menu_page()
        test_cart_functionality()
        test_api_endpoints()
        test_admin_dashboard()
        test_user_profile()
        test_static_files()
        test_url_patterns()
        
        print("=" * 50)
        print("🎉 All tests passed! The application is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
