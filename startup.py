#!/usr/bin/env python
"""
Startup script for SkipTheQueue
This script will be run by Render to set up the application
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from orders.models import College

def create_superuser():
    """Create superuser if it doesn't exist"""
    if not User.objects.filter(email='skipthequeue.app@gmail.com').exists():
        try:
            user = User.objects.create_superuser(
                username='skipthequeue',
                email='skipthequeue.app@gmail.com',
                password='SkipTheQueue2024!'
            )
            print(f"✅ Created superuser: {user.username} ({user.email})")
            print("🔑 Password: SkipTheQueue2024!")
            return True
        except Exception as e:
            print(f"❌ Error creating superuser: {e}")
            return False
    else:
        print("ℹ️ Superuser already exists: skipthequeue.app@gmail.com")
        return True

def check_colleges():
    """Check if colleges exist"""
    colleges = College.objects.all()
    print(f"📚 Found {colleges.count()} colleges:")
    for college in colleges:
        print(f"   - {college.name} (slug: {college.slug})")
    return colleges.count() > 0

if __name__ == '__main__':
    print("🚀 Starting SkipTheQueue setup...")
    
    # Create superuser
    superuser_created = create_superuser()
    
    # Check colleges
    colleges_exist = check_colleges()
    
    if superuser_created and colleges_exist:
        print("✅ Setup completed successfully!")
    else:
        print("⚠️ Setup completed with warnings")
        if not superuser_created:
            print("   - Superuser creation failed")
        if not colleges_exist:
            print("   - No colleges found")
    
    print("🎯 Ready to serve!") 