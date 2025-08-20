#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def test_login():
    """Test the login functionality"""
    print("Testing login functionality...")
    
    # Test superuser login
    user = authenticate(username='skiptheq', password='Paras@999stq')
    if user:
        print(f"✅ Superuser login successful: {user.email}")
        print(f"   Is superuser: {user.is_superuser}")
        print(f"   Is staff: {user.is_staff}")
    else:
        print("❌ Superuser login failed")
    
    # Test with email
    user = authenticate(username='skipthequeue.app@gmail.com', password='Paras@999stq')
    if user:
        print(f"✅ Email login successful: {user.email}")
    else:
        print("❌ Email login failed")
    
    # Create a test user
    test_user, created = User.objects.get_or_create(
        username='testuser',
        email='test@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': True
        }
    )
    
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print("✅ Created test user: test@example.com / testpass123")
    else:
        print("ℹ️ Test user already exists")
    
    # Test regular user login
    user = authenticate(username='testuser', password='testpass123')
    if user:
        print(f"✅ Regular user login successful: {user.email}")
    else:
        print("❌ Regular user login failed")

if __name__ == '__main__':
    test_login()
