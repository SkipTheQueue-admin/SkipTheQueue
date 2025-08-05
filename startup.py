#!/usr/bin/env python
"""
Startup script for SkipTheQueue
This script runs automatically when the app starts on Render
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to the Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import execute_from_command_line

def create_superuser():
    """Create or update the superuser with specified credentials"""
    email = 'skipthequeue.app@gmail.com'
    username = 'skiptheq'
    password = 'Paras@999stq'
    
    try:
        # Check if user already exists
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': username,
                'first_name': 'SkipTheQueue',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            }
        )
        
        if not created:
            # Update existing user
            user.username = username
            user.first_name = 'SkipTheQueue'
            user.last_name = 'Admin'
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            print(f"✅ Updated existing superuser: {username}")
        else:
            print(f"✅ Created new superuser: {username}")
        
        # Set password
        user.set_password(password)
        user.save()
        
        print(f"✅ Superuser setup complete!")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Django Admin URL: /admin/")
        
    except Exception as e:
        print(f"❌ Error creating superuser: {e}")

def run_migrations():
    """Run database migrations"""
    try:
        print("🔄 Running database migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrations completed successfully")
    except Exception as e:
        print(f"❌ Error running migrations: {e}")

def collect_static():
    """Collect static files"""
    try:
        print("🔄 Collecting static files...")
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
        print("✅ Static files collected successfully")
    except Exception as e:
        print(f"❌ Error collecting static files: {e}")

if __name__ == '__main__':
    print("🚀 Starting SkipTheQueue application...")
    
    # Run migrations first
    run_migrations()
    
    # Create superuser
    create_superuser()
    
    # Collect static files
    collect_static()
    
    print("✅ SkipTheQueue startup completed successfully!")
    print("🌐 Application is ready to serve requests!") 