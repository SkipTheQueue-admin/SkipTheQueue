"""
Django management command to optimize database performance
Usage: python manage.py optimize_database
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from orders.models import Order, MenuItem, College, UserProfile
from django.db.models import Count, Avg
import time


class Command(BaseCommand):
    help = 'Optimize database performance with indexes and caching'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create database indexes for better performance',
        )
        parser.add_argument(
            '--setup-caching',
            action='store_true',
            help='Setup caching for frequently accessed data',
        )
        parser.add_argument(
            '--analyze-performance',
            action='store_true',
            help='Analyze current database performance',
        )

    def handle(self, *args, **options):
        if options['create_indexes']:
            self.create_indexes()
        
        if options['setup_caching']:
            self.setup_caching()
        
        if options['analyze_performance']:
            self.analyze_performance()
        
        if not any([options['create_indexes'], options['setup_caching'], options['analyze_performance']]):
            self.stdout.write('Running all optimizations...')
            self.create_indexes()
            self.setup_caching()
            self.analyze_performance()

    def create_indexes(self):
        """Create database indexes for better query performance"""
        self.stdout.write('Creating database indexes...')
        
        with connection.cursor() as cursor:
            # Indexes for Order model
            indexes = [
                # Order indexes
                "CREATE INDEX IF NOT EXISTS idx_order_status ON orders_order(status);",
                "CREATE INDEX IF NOT EXISTS idx_order_created_at ON orders_order(created_at);",
                "CREATE INDEX IF NOT EXISTS idx_order_college ON orders_order(college_id);",
                "CREATE INDEX IF NOT EXISTS idx_order_user ON orders_order(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_order_payment_status ON orders_order(payment_status);",
                "CREATE INDEX IF NOT EXISTS idx_order_status_created ON orders_order(status, created_at);",
                
                # MenuItem indexes
                "CREATE INDEX IF NOT EXISTS idx_menuitem_college ON orders_menuitem(college_id);",
                "CREATE INDEX IF NOT EXISTS idx_menuitem_category ON orders_menuitem(category);",
                "CREATE INDEX IF NOT EXISTS idx_menuitem_available ON orders_menuitem(is_available);",
                "CREATE INDEX IF NOT EXISTS idx_menuitem_college_category ON orders_menuitem(college_id, category);",
                "CREATE INDEX IF NOT EXISTS idx_menuitem_college_available ON orders_menuitem(college_id, is_available);",
                
                # College indexes
                "CREATE INDEX IF NOT EXISTS idx_college_slug ON orders_college(slug);",
                "CREATE INDEX IF NOT EXISTS idx_college_active ON orders_college(is_active);",
                
                # UserProfile indexes
                "CREATE INDEX IF NOT EXISTS idx_userprofile_user ON orders_userprofile(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_userprofile_college ON orders_userprofile(preferred_college_id);",
                "CREATE INDEX IF NOT EXISTS idx_userprofile_phone ON orders_userprofile(phone_number);",
                
                # OrderItem indexes
                "CREATE INDEX IF NOT EXISTS idx_orderitem_order ON orders_orderitem(order_id);",
                "CREATE INDEX IF NOT EXISTS idx_orderitem_item ON orders_orderitem(item_id);",
                "CREATE INDEX IF NOT EXISTS idx_orderitem_order_item ON orders_orderitem(order_id, item_id);",
            ]
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    self.stdout.write(f'✓ Created index: {index_sql.split("idx_")[1].split(" ")[0]}')
                except Exception as e:
                    self.stdout.write(f'⚠ Index already exists or error: {e}')
        
        self.stdout.write(self.style.SUCCESS('Database indexes created successfully!'))

    def setup_caching(self):
        """Setup caching for frequently accessed data"""
        self.stdout.write('Setting up caching...')
        
        # Cache college data
        colleges = College.objects.filter(is_active=True)
        for college in colleges:
            cache_key = f'college_{college.slug}'
            cache.set(cache_key, {
                'id': college.id,
                'name': college.name,
                'slug': college.slug,
                'estimated_preparation_time': college.estimated_preparation_time,
                'is_active': college.is_active
            }, timeout=3600)  # 1 hour
            self.stdout.write(f'✓ Cached college: {college.name}')
        
        # Cache menu items by college
        for college in colleges:
            menu_items = MenuItem.objects.filter(college=college, is_available=True)
            cache_key = f'menu_items_{college.slug}'
            cache.set(cache_key, list(menu_items.values()), timeout=1800)  # 30 minutes
            self.stdout.write(f'✓ Cached menu items for: {college.name}')
        
        # Cache popular items (simplified to avoid schema issues)
        popular_items = MenuItem.objects.filter(is_available=True)[:20]
        
        cache.set('popular_items', list(popular_items.values()), timeout=3600)  # 1 hour
        self.stdout.write('✓ Cached popular items')
        
        # Cache order statistics
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status='Pending').count()
        completed_orders = Order.objects.filter(status='Completed').count()
        
        stats = {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0
        }
        
        cache.set('order_stats', stats, timeout=1800)  # 30 minutes
        self.stdout.write('✓ Cached order statistics')
        
        self.stdout.write(self.style.SUCCESS('Caching setup completed!'))

    def analyze_performance(self):
        """Analyze current database performance"""
        self.stdout.write('Analyzing database performance...')
        
        # Test query performance
        start_time = time.time()
        
        # Test 1: Order queries
        orders = Order.objects.select_related('college', 'user').filter(status='Pending')
        order_time = time.time() - start_time
        
        # Test 2: Menu item queries
        start_time = time.time()
        menu_items = MenuItem.objects.filter(is_available=True).select_related('college')
        menu_time = time.time() - start_time
        
        # Test 3: Simple college query
        start_time = time.time()
        college_stats = College.objects.filter(is_active=True)
        complex_time = time.time() - start_time
        
        # Performance report
        self.stdout.write('\n' + '='*50)
        self.stdout.write('DATABASE PERFORMANCE ANALYSIS')
        self.stdout.write('='*50)
        
        self.stdout.write(f'Order queries: {order_time:.4f}s ({orders.count()} orders)')
        self.stdout.write(f'Menu queries: {menu_time:.4f}s ({menu_items.count()} items)')
        self.stdout.write(f'Complex queries: {complex_time:.4f}s ({college_stats.count()} colleges)')
        
        # Performance recommendations
        self.stdout.write('\nPERFORMANCE RECOMMENDATIONS:')
        if order_time > 0.1:
            self.stdout.write('⚠ Order queries are slow - consider adding more indexes')
        if menu_time > 0.05:
            self.stdout.write('⚠ Menu queries are slow - consider caching')
        if complex_time > 0.2:
            self.stdout.write('⚠ Complex queries are slow - consider query optimization')
        
        # Cache hit analysis
        cache_hits = cache.get('cache_hits', 0)
        cache_misses = cache.get('cache_misses', 0)
        total_requests = cache_hits + cache_misses
        hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        self.stdout.write(f'\nCACHE PERFORMANCE:')
        self.stdout.write(f'Cache hit rate: {hit_rate:.1f}% ({cache_hits}/{total_requests})')
        
        if hit_rate < 70:
            self.stdout.write('⚠ Cache hit rate is low - consider caching more data')
        else:
            self.stdout.write('✓ Cache performance is good')
        
        self.stdout.write(self.style.SUCCESS('\nPerformance analysis completed!'))

    def clear_cache(self):
        """Clear all cached data"""
        self.stdout.write('Clearing cache...')
        cache.clear()
        self.stdout.write(self.style.SUCCESS('Cache cleared successfully!'))
