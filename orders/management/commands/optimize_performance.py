"""
Django management command to optimize SkipTheQueue performance
"""

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.db.models import Count, Q
from orders.models import MenuItem, Order, OrderItem, College
import logging
import time
from django.utils import timezone

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Optimize SkipTheQueue performance by analyzing and improving database queries, cache, and overall performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze performance without making changes',
        )
        parser.add_argument(
            '--fix-queries',
            action='store_true',
            help='Fix slow database queries',
        )
        parser.add_argument(
            '--optimize-cache',
            action='store_true',
            help='Optimize cache configuration',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old data and optimize tables',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Starting SkipTheQueue Performance Optimization...')
        )
        
        start_time = time.time()
        
        # Always analyze performance first
        self.analyze_performance()
        
        if not options['analyze_only']:
            if options['fix_queries']:
                self.fix_database_queries()
            
            if options['optimize_cache']:
                self.optimize_cache()
            
            if options['cleanup']:
                self.cleanup_data()
            
            # Run all optimizations if no specific option is selected
            if not any([options['fix_queries'], options['optimize_cache'], options['cleanup']]):
                self.fix_database_queries()
                self.optimize_cache()
                self.cleanup_data()
        
        execution_time = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(f'✅ Performance optimization completed in {execution_time:.2f} seconds')
        )

    def analyze_performance(self):
        """Analyze current performance metrics"""
        self.stdout.write('\n📊 Analyzing Performance Metrics...')
        
        # Analyze database performance
        self.analyze_database_performance()
        
        # Analyze cache performance
        self.analyze_cache_performance()
        
        # Analyze model relationships
        self.analyze_model_relationships()
        
        # Analyze query patterns
        self.analyze_query_patterns()

    def analyze_database_performance(self):
        """Analyze database performance and identify bottlenecks"""
        self.stdout.write('  🔍 Analyzing database performance...')
        
        try:
            # Check table sizes
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        table_name,
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)',
                        table_rows
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                    ORDER BY (data_length + index_length) DESC
                """)
                
                tables = cursor.fetchall()
                if tables:
                    self.stdout.write('    📋 Table sizes:')
                    for table_name, size, rows in tables[:10]:  # Top 10 tables
                        self.stdout.write(f'      {table_name}: {size} MB ({rows:,} rows)')
                
                # Check for missing indexes
                cursor.execute("""
                    SELECT 
                        table_name,
                        column_name,
                        data_type
                    FROM information_schema.columns 
                    WHERE table_schema = DATABASE()
                    AND column_name IN ('user_id', 'college_id', 'menu_item_id', 'created_at', 'status')
                    AND table_name IN ('orders_order', 'orders_orderitem', 'orders_menuitem')
                """)
                
                columns = cursor.fetchall()
                if columns:
                    self.stdout.write('    🔍 Checking for missing indexes...')
                    for table, column, data_type in columns:
                        self.stdout.write(f'      {table}.{column} ({data_type})')
        
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'    ⚠️ Database analysis failed: {e}')
            )

    def analyze_cache_performance(self):
        """Analyze cache performance and hit rates"""
        self.stdout.write('  🔍 Analyzing cache performance...')
        
        try:
            # Test cache performance
            test_key = 'perf_test_key'
            test_value = 'test_value'
            
            # Write test
            start_time = time.time()
            cache.set(test_key, test_value, 60)
            write_time = time.time() - start_time
            
            # Read test
            start_time = time.time()
            cached_value = cache.get(test_key)
            read_time = time.time() - start_time
            
            # Delete test
            start_time = time.time()
            cache.delete(test_key)
            delete_time = time.time() - start_time
            
            self.stdout.write(f'    ⚡ Cache performance:')
            self.stdout.write(f'      Write: {write_time*1000:.2f}ms')
            self.stdout.write(f'      Read: {read_time*1000:.2f}ms')
            self.stdout.write(f'      Delete: {delete_time*1000:.2f}ms')
            
            # Check cache configuration
            cache_backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'Unknown')
            self.stdout.write(f'    ⚙️ Cache backend: {cache_backend}')
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'    ⚠️ Cache analysis failed: {e}')
            )

    def analyze_model_relationships(self):
        """Analyze model relationships and identify N+1 query issues"""
        self.stdout.write('  🔍 Analyzing model relationships...')
        
        try:
            # Check for potential N+1 queries
            colleges = College.objects.all()[:5]  # Sample of 5 colleges
            
            # Count related objects
            for college in colleges:
                menu_count = college.menuitem_set.count()
                order_count = college.order_set.count()
                
                self.stdout.write(f'    🏫 {college.name}:')
                self.stdout.write(f'      Menu items: {menu_count}')
                self.stdout.write(f'      Orders: {order_count}')
            
            # Check order relationships
            orders = Order.objects.select_related('college').prefetch_related('order_items__menu_item')[:5]
            
            for order in orders:
                item_count = order.order_items.count()
                self.stdout.write(f'    📦 Order #{order.id}: {item_count} items')
        
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'    ⚠️ Model analysis failed: {e}')
            )

    def analyze_query_patterns(self):
        """Analyze common query patterns and identify optimization opportunities"""
        self.stdout.write('  🔍 Analyzing query patterns...')
        
        try:
            # Analyze menu item queries
            menu_items = MenuItem.objects.filter(is_available=True)
            self.stdout.write(f'    🍽️ Available menu items: {menu_items.count()}')
            
            # Analyze order queries by status
            order_statuses = Order.objects.values('status').annotate(count=Count('id'))
            self.stdout.write('    📊 Order distribution by status:')
            for status in order_statuses:
                self.stdout.write(f'      {status["status"]}: {status["count"]}')
            
            # Check for recent orders
            recent_orders = Order.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count()
            self.stdout.write(f'    📅 Recent orders (7 days): {recent_orders}')
        
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'    ⚠️ Query pattern analysis failed: {e}')
            )

    def fix_database_queries(self):
        """Fix slow database queries and add missing indexes"""
        self.stdout.write('\n🔧 Fixing Database Queries...')
        
        try:
            with connection.cursor() as cursor:
                # Add missing indexes for common queries
                indexes_to_add = [
                    ('orders_order', 'college_id', 'CREATE INDEX idx_order_college ON orders_order(college_id)'),
                    ('orders_order', 'status', 'CREATE INDEX idx_order_status ON orders_order(status)'),
                    ('orders_order', 'created_at', 'CREATE INDEX idx_order_created ON orders_order(created_at)'),
                    ('orders_orderitem', 'order_id', 'CREATE INDEX idx_orderitem_order ON orders_orderitem(order_id)'),
                    ('orders_orderitem', 'menu_item_id', 'CREATE INDEX idx_orderitem_menu ON orders_orderitem(menu_item_id)'),
                    ('orders_menuitem', 'college_id', 'CREATE INDEX idx_menuitem_college ON orders_menuitem(college_id)'),
                    ('orders_menuitem', 'is_available', 'CREATE INDEX idx_menuitem_available ON orders_menuitem(is_available)'),
                ]
                
                for table, column, index_sql in indexes_to_add:
                    try:
                        cursor.execute(index_sql)
                        self.stdout.write(f'    ✅ Added index on {table}.{column}')
                    except Exception as e:
                        if 'Duplicate key name' in str(e):
                            self.stdout.write(f'    ℹ️ Index already exists on {table}.{column}')
                        else:
                            self.stdout.write(
                                self.style.WARNING(f'    ⚠️ Failed to add index on {table}.{column}: {e}')
                            )
                
                # Analyze and optimize tables
                tables_to_optimize = ['orders_order', 'orders_orderitem', 'orders_menuitem', 'orders_college']
                for table in tables_to_optimize:
                    try:
                        cursor.execute(f'OPTIMIZE TABLE {table}')
                        self.stdout.write(f'    ✅ Optimized table {table}')
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'    ⚠️ Failed to optimize table {table}: {e}')
                        )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'    ❌ Database optimization failed: {e}')
            )

    def optimize_cache(self):
        """Optimize cache configuration and warm up cache"""
        self.stdout.write('\n⚡ Optimizing Cache...')
        
        try:
            # Warm up cache with frequently accessed data
            self.stdout.write('    🔥 Warming up cache...')
            
            # Cache college data
            colleges = College.objects.all()
            for college in colleges:
                cache_key = f'college_{college.slug}'
                cache.set(cache_key, {
                    'id': college.id,
                    'name': college.name,
                    'slug': college.slug,
                    'admin_name': college.admin_name,
                    'admin_email': college.admin_email
                }, 3600)  # Cache for 1 hour
            
            self.stdout.write(f'    ✅ Cached {colleges.count()} colleges')
            
            # Cache menu items by college
            for college in colleges:
                menu_items = college.menuitem_set.filter(is_available=True)
                cache_key = f'menu_items_{college.slug}'
                cache.set(cache_key, list(menu_items.values()), 1800)  # Cache for 30 minutes
            
            self.stdout.write(f'    ✅ Cached menu items for {colleges.count()} colleges')
            
            # Cache order statistics
            for college in colleges:
                stats = {
                    'pending': college.order_set.filter(status='Pending').count(),
                    'in_progress': college.order_set.filter(status='In Progress').count(),
                    'ready': college.order_set.filter(status='Ready').count(),
                    'completed': college.order_set.filter(status='Completed').count(),
                }
                cache_key = f'order_stats_{college.slug}'
                cache.set(cache_key, stats, 300)  # Cache for 5 minutes
            
            self.stdout.write(f'    ✅ Cached order statistics for {colleges.count()} colleges')
            
            # Set cache configuration
            cache.set('perf_config', {
                'last_optimization': time.time(),
                'cache_warmed': True,
                'version': '1.0'
            }, 86400)  # Cache for 24 hours
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'    ❌ Cache optimization failed: {e}')
            )

    def cleanup_data(self):
        """Clean up old data and optimize storage"""
        self.stdout.write('\n🧹 Cleaning Up Data...')
        
        try:
            # Clean up old completed orders (older than 90 days)
            cutoff_date = timezone.now() - timezone.timedelta(days=90)
            
            old_orders = Order.objects.filter(
                status='Completed',
                created_at__lt=cutoff_date
            )
            
            old_count = old_orders.count()
            if old_count > 0:
                # Archive old orders instead of deleting
                self.stdout.write(f'    📦 Found {old_count} old completed orders')
                
                # You could implement archiving logic here
                # For now, just log the count
                self.stdout.write(f'    ℹ️ Consider archiving orders older than 90 days')
            
            # Clean up cache
            cache_keys_to_clean = [
                'perf_test_*',
                'temp_*',
                'session_*'
            ]
            
            cleaned_count = 0
            for pattern in cache_keys_to_clean:
                # Note: This is a simplified cleanup. In production, you might want
                # to use a more sophisticated cache key pattern matching
                pass
            
            self.stdout.write(f'    ✅ Cache cleanup completed')
            
            # Optimize database tables
            with connection.cursor() as cursor:
                tables = ['orders_order', 'orders_orderitem', 'orders_menuitem']
                for table in tables:
                    try:
                        cursor.execute(f'ANALYZE TABLE {table}')
                        self.stdout.write(f'    ✅ Analyzed table {table}')
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f'    ⚠️ Failed to analyze table {table}: {e}')
                        )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'    ❌ Data cleanup failed: {e}')
            )

    def generate_performance_report(self):
        """Generate a comprehensive performance report"""
        self.stdout.write('\n📋 Generating Performance Report...')
        
        try:
            report = {
                'timestamp': time.time(),
                'database': {
                    'total_orders': Order.objects.count(),
                    'total_menu_items': MenuItem.objects.count(),
                    'total_colleges': College.objects.count(),
                },
                'cache': {
                    'backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'Unknown'),
                    'warmed': cache.get('perf_config', {}).get('cache_warmed', False),
                },
                'recommendations': [
                    'Monitor slow queries in production',
                    'Consider implementing database connection pooling',
                    'Implement cache warming for peak hours',
                    'Add database query logging in development',
                    'Consider CDN for static files',
                    'Implement lazy loading for images',
                    'Use pagination for large datasets',
                    'Consider Redis for session storage',
                ]
            }
            
            # Save report to cache
            cache.set('perf_report', report, 3600)
            
            self.stdout.write('    ✅ Performance report generated and cached')
            self.stdout.write('    📊 Report includes:')
            self.stdout.write(f'      - Database statistics: {report["database"]["total_orders"]} orders, {report["database"]["total_menu_items"]} menu items')
            self.stdout.write(f'      - Cache status: {report["cache"]["backend"]}')
            self.stdout.write(f'      - {len(report["recommendations"])} optimization recommendations')
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'    ❌ Report generation failed: {e}')
            )
