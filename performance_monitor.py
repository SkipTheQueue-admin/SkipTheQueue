#!/usr/bin/env python3
"""
Performance Monitoring Script for SkipTheQueue
Monitors database queries, cache performance, and response times
"""

import os
import sys
import django
import time
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Avg, Max, Min
from orders.models import Order, MenuItem, UserProfile, College

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def check_database_performance():
    """Check database performance and identify slow queries"""
    print("🔍 Checking Database Performance...")
    
    # Check table sizes
    print("\n📊 Table Sizes:")
    for model in [Order, MenuItem, UserProfile, College]:
        count = model.objects.count()
        print(f"  {model.__name__}: {count:,} records")
    
    # Check for missing indexes
    print("\n🔍 Checking for potential missing indexes...")
    
    # Check Order model queries
    if Order.objects.count() > 1000:
        print("  ⚠️  Large Order table detected - consider adding indexes on:")
        print("     - user_phone + status")
        print("     - college + status")
        print("     - created_at + status")
    
    # Check for slow queries
    print("\n⏱️  Checking for slow queries...")
    slow_queries = []
    
    # Test common queries
    start_time = time.time()
    Order.objects.filter(status='Pending').count()
    query_time = time.time() - start_time
    if query_time > 0.1:
        slow_queries.append(f"Order status filter: {query_time:.3f}s")
    
    start_time = time.time()
    MenuItem.objects.filter(is_available=True).count()
    query_time = time.time() - start_time
    if query_time > 0.1:
        slow_queries.append(f"MenuItem availability filter: {query_time:.3f}s")
    
    if slow_queries:
        print("  ⚠️  Slow queries detected:")
        for query in slow_queries:
            print(f"     {query}")
    else:
        print("  ✅ All queries are performing well")

def check_cache_performance():
    """Check cache performance"""
    print("\n💾 Checking Cache Performance...")
    
    # Test cache operations
    test_key = "performance_test"
    test_value = "test_data"
    
    # Write test
    start_time = time.time()
    cache.set(test_key, test_value, 60)
    write_time = time.time() - start_time
    
    # Read test
    start_time = time.time()
    result = cache.get(test_key)
    read_time = time.time() - start_time
    
    # Delete test
    start_time = time.time()
    cache.delete(test_key)
    delete_time = time.time() - start_time
    
    print(f"  Cache Write: {write_time:.4f}s")
    print(f"  Cache Read: {read_time:.4f}s")
    print(f"  Cache Delete: {delete_time:.4f}s")
    
    if write_time > 0.01 or read_time > 0.01:
        print("  ⚠️  Cache operations are slow - consider optimizing")
    else:
        print("  ✅ Cache performance is good")

def check_memory_usage():
    """Check memory usage patterns"""
    print("\n🧠 Checking Memory Usage Patterns...")
    
    # Check for potential memory leaks
    large_querysets = []
    
    # Check for large querysets that might be loaded into memory
    if Order.objects.count() > 10000:
        large_querysets.append("Order table has over 10,000 records")
    
    if MenuItem.objects.count() > 1000:
        large_querysets.append("MenuItem table has over 1,000 records")
    
    if large_querysets:
        print("  ⚠️  Large datasets detected:")
        for dataset in large_querysets:
            print(f"     {dataset}")
        print("  💡 Consider implementing pagination and lazy loading")
    else:
        print("  ✅ Dataset sizes are manageable")

def generate_optimization_recommendations():
    """Generate optimization recommendations"""
    print("\n🚀 Performance Optimization Recommendations:")
    
    recommendations = [
        "1. Database Indexes:",
        "   - Add composite index on Order(user_phone, status)",
        "   - Add composite index on Order(college, status)",
        "   - Add index on Order(created_at)",
        "",
        "2. Query Optimization:",
        "   - Use select_related() for foreign key relationships",
        "   - Use prefetch_related() for many-to-many relationships",
        "   - Implement database-level aggregation for calculations",
        "",
        "3. Caching Strategy:",
        "   - Cache frequently accessed data (menu items, user profiles)",
        "   - Implement cache warming for popular queries",
        "   - Use cache versioning for data invalidation",
        "",
        "4. Frontend Optimization:",
        "   - Implement lazy loading for images",
        "   - Use pagination for large lists",
        "   - Minimize DOM manipulation",
        "",
        "5. Mobile Performance:",
        "   - Optimize images for mobile devices",
        "   - Implement touch-friendly interactions",
        "   - Reduce JavaScript bundle size"
    ]
    
    for rec in recommendations:
        print(rec)

def main():
    """Main performance monitoring function"""
    print("🚀 SkipTheQueue Performance Monitor")
    print("=" * 50)
    
    try:
        check_database_performance()
        check_cache_performance()
        check_memory_usage()
        generate_optimization_recommendations()
        
        print("\n✅ Performance monitoring completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during performance monitoring: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
