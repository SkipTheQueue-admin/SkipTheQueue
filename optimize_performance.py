#!/usr/bin/env python3
"""
Performance optimization script for SkipTheQueue
Run this script to analyze and optimize performance
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.cache import cache
from django.db import connection
from django.conf import settings
from orders.models import MenuItem, Order, College, UserProfile
from orders.utils import clear_related_caches
import logging

logger = logging.getLogger(__name__)

def analyze_database_performance():
    """Analyze database performance and suggest optimizations"""
    print("🔍 Analyzing database performance...")
    
    # Check database indexes
    with connection.cursor() as cursor:
        # Get table sizes
        cursor.execute("""
            SELECT 
                name,
                sql
            FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = cursor.fetchall()
        
        print(f"📊 Found {len(tables)} tables")
        
        for table_name, sql in tables:
            if table_name in ['orders_order', 'orders_menuitem', 'orders_college']:
                print(f"  📋 {table_name}: {sql[:100]}...")
    
    # Check model performance
    print("\n📈 Model performance analysis:")
    
    # MenuItem performance
    menu_count = MenuItem.objects.count()
    print(f"  🍽️  MenuItem: {menu_count} items")
    
    # Order performance
    order_count = Order.objects.count()
    print(f"  📦 Order: {order_count} orders")
    
    # College performance
    college_count = College.objects.count()
    print(f"  🏫 College: {college_count} colleges")
    
    # UserProfile performance
    profile_count = UserProfile.objects.count()
    print(f"  👤 UserProfile: {profile_count} profiles")

def optimize_cache():
    """Optimize cache configuration"""
    print("\n⚡ Optimizing cache...")
    
    # Clear old cache entries
    cache.clear()
    print("  🗑️  Cleared old cache entries")
    
    # Pre-populate cache with frequently accessed data
    colleges = College.objects.filter(is_active=True)
    for college in colleges:
        cache_key = f'college_{college.slug}'
        cache.set(cache_key, college, 1800)  # 30 minutes
        
        # Cache menu items
        menu_items = MenuItem.objects.filter(college=college, is_available=True)
        menu_cache_key = f'menu_items_{college.id}'
        cache.set(menu_cache_key, list(menu_items), 300)  # 5 minutes
        
        # Cache categories
        categories = menu_items.values_list('category', flat=True).distinct()
        categories_cache_key = f'categories_{college.id}'
        cache.set(categories_cache_key, list(categories), 600)  # 10 minutes
    
    print(f"  💾 Pre-populated cache for {colleges.count()} colleges")

def check_performance_settings():
    """Check and display performance settings"""
    print("\n⚙️  Performance settings:")
    
    # Cache settings
    print(f"  🗄️  Cache backend: {settings.CACHES['default']['BACKEND']}")
    print(f"  ⏱️  Cache timeout: {settings.CACHES['default']['TIMEOUT']}s")
    
    # Database settings
    print(f"  🗃️  Database: {settings.DATABASES['default']['ENGINE']}")
    print(f"  🔗 Connection max age: {settings.DATABASES['default'].get('CONN_MAX_AGE', 'Not set')}s")
    
    # Static files
    print(f"  📁 Static files storage: {settings.STATICFILES_STORAGE}")
    print(f"  🗜️  Compression enabled: {getattr(settings, 'COMPRESS_ENABLED', False)}")
    
    # Template optimization
    print(f"  📝 Template caching: {'Enabled' if not settings.DEBUG else 'Disabled (DEBUG mode)'}")

def generate_performance_report():
    """Generate a comprehensive performance report"""
    print("\n📊 Performance Report:")
    
    # Database queries
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA cache_size")
        cache_size = cursor.fetchone()[0]
        print(f"  🗃️  SQLite cache size: {cache_size} pages")
        
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        print(f"  📄 SQLite page size: {page_size} bytes")
    
    # Cache statistics
    cache_stats = {
        'college_cache': len([k for k in cache._cache.keys() if k.startswith('college_')]),
        'menu_cache': len([k for k in cache._cache.keys() if k.startswith('menu_items_')]),
        'user_cache': len([k for k in cache._cache.keys() if k.startswith('user_profile_')]),
    }
    
    print(f"  💾 Cache entries: {sum(cache_stats.values())} total")
    print(f"    - College: {cache_stats['college_cache']}")
    print(f"    - Menu: {cache_stats['menu_cache']}")
    print(f"    - User: {cache_stats['user_cache']}")

def main():
    """Main optimization function"""
    print("🚀 SkipTheQueue Performance Optimization")
    print("=" * 50)
    
    try:
        # Analyze current performance
        analyze_database_performance()
        
        # Check settings
        check_performance_settings()
        
        # Optimize cache
        optimize_cache()
        
        # Generate report
        generate_performance_report()
        
        print("\n✅ Performance optimization completed!")
        print("\n💡 Recommendations:")
        print("  1. Monitor cache hit rates")
        print("  2. Use select_related and prefetch_related in views")
        print("  3. Consider database connection pooling for production")
        print("  4. Monitor slow queries and optimize them")
        print("  5. Use template fragment caching for complex templates")
        
    except Exception as e:
        print(f"\n❌ Error during optimization: {e}")
        logger.error(f"Performance optimization failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
