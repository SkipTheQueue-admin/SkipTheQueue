"""
Django management command to optimize database performance
Usage: python manage.py optimize_database
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from orders.models import Order, MenuItem, College, UserProfile, CanteenStaff
from django.db.models import Count, Q
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Optimize database performance by creating indexes and cleaning up data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force optimization even if not needed',
        )
        parser.add_argument(
            '--analyze',
            action='store_true',
            help='Analyze table statistics',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting database optimization...')
        )

        try:
            # Clear cache to ensure fresh data
            cache.clear()
            self.stdout.write('✓ Cache cleared')

            # Analyze table statistics if requested
            if options['analyze']:
                self.analyze_tables()

            # Create database indexes for better performance
            self.create_indexes()

            # Clean up old data
            self.cleanup_old_data()

            # Optimize queries
            self.optimize_queries()

            # Update table statistics
            self.update_statistics()

            self.stdout.write(
                self.style.SUCCESS('Database optimization completed successfully!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Database optimization failed: {str(e)}')
            )
            logger.error(f'Database optimization error: {e}')

    def analyze_tables(self):
        """Analyze table statistics for better query planning"""
        self.stdout.write('Analyzing table statistics...')
        
        with connection.cursor() as cursor:
            tables = ['orders_order', 'orders_menuitem', 'orders_college', 'orders_userprofile']
            
            for table in tables:
                try:
                    cursor.execute(f'ANALYZE {table};')
                    self.stdout.write(f'✓ Analyzed {table}')
                except Exception as e:
                    self.stdout.write(f'⚠ Could not analyze {table}: {e}')

    def create_indexes(self):
        """Create database indexes for better performance"""
        self.stdout.write('Creating database indexes...')
        
        with connection.cursor() as cursor:
            # Indexes for Order model
            indexes = [
                # Order status and college for filtering
                'CREATE INDEX IF NOT EXISTS idx_order_status_college ON orders_order(status, college_id)',
                # Order creation date for time-based queries
                'CREATE INDEX IF NOT EXISTS idx_order_created_at ON orders_order(created_at)',
                # Order user for user-specific queries
                'CREATE INDEX IF NOT EXISTS idx_order_user ON orders_order(user_id)',
                # Order status for status filtering
                'CREATE INDEX IF NOT EXISTS idx_order_status ON orders_order(status)',
                
                # MenuItem indexes
                'CREATE INDEX IF NOT EXISTS idx_menuitem_college_available ON orders_menuitem(college_id, is_available)',
                'CREATE INDEX IF NOT EXISTS idx_menuitem_category ON orders_menuitem(category)',
                'CREATE INDEX IF NOT EXISTS idx_menuitem_name ON orders_menuitem(name)',
                
                # College indexes
                'CREATE INDEX IF NOT EXISTS idx_college_slug ON orders_college(slug)',
                'CREATE INDEX IF NOT EXISTS idx_college_active ON orders_college(is_active)',
                
                # UserProfile indexes
                'CREATE INDEX IF NOT EXISTS idx_userprofile_phone ON orders_userprofile(phone_number)',
                'CREATE INDEX IF NOT EXISTS idx_userprofile_user ON orders_userprofile(user_id)',
                
                # CanteenStaff indexes
                'CREATE INDEX IF NOT EXISTS idx_canteenstaff_user_active ON orders_canteenstaff(user_id, is_active)',
                'CREATE INDEX IF NOT EXISTS idx_canteenstaff_college ON orders_canteenstaff(college_id)',
            ]
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    self.stdout.write(f'✓ Created index: {index_sql.split("idx_")[1].split(" ")[0]}')
                except Exception as e:
                    self.stdout.write(f'⚠ Could not create index: {e}')

    def cleanup_old_data(self):
        """Clean up old and unnecessary data"""
        self.stdout.write('Cleaning up old data...')
        
        # Clean up old completed orders (older than 30 days)
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=30)
        old_orders = Order.objects.filter(
            status='Completed',
            created_at__lt=cutoff_date
        )
        
        old_count = old_orders.count()
        if old_count > 0:
            old_orders.delete()
            self.stdout.write(f'✓ Cleaned up {old_count} old completed orders')
        
        # Clean up orphaned order items
        from orders.models import OrderItem
        
        orphaned_items = OrderItem.objects.filter(order__isnull=True)
        orphaned_count = orphaned_items.count()
        if orphaned_count > 0:
            orphaned_items.delete()
            self.stdout.write(f'✓ Cleaned up {orphaned_count} orphaned order items')

    def optimize_queries(self):
        """Optimize common queries"""
        self.stdout.write('Optimizing common queries...')
        
        # Pre-calculate common aggregations
        college_stats = {}
        
        for college in College.objects.filter(is_active=True):
            # Cache college statistics
            stats = {
                'total_orders': Order.objects.filter(college=college).count(),
                'pending_orders': Order.objects.filter(college=college, status='Paid').count(),
                'in_progress_orders': Order.objects.filter(college=college, status='In Progress').count(),
                'ready_orders': Order.objects.filter(college=college, status='Ready').count(),
                'menu_items': MenuItem.objects.filter(college=college, is_available=True).count(),
            }
            
            college_stats[college.id] = stats
            
            # Cache these statistics
            cache.set(f'college_stats_{college.id}', stats, 3600)  # 1 hour
        
        self.stdout.write(f'✓ Cached statistics for {len(college_stats)} colleges')

    def update_statistics(self):
        """Update database statistics for better query planning"""
        self.stdout.write('Updating database statistics...')
        
        with connection.cursor() as cursor:
            try:
                # Update statistics for better query planning
                cursor.execute('VACUUM ANALYZE;')
                self.stdout.write('✓ Database vacuum and analyze completed')
            except Exception as e:
                self.stdout.write(f'⚠ Could not vacuum database: {e}')

    def log_optimization_results(self):
        """Log optimization results for monitoring"""
        try:
            # Get database size
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)
                db_size = cursor.fetchone()[0]
                
                # Get table sizes
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """)
                table_sizes = cursor.fetchall()
                
                logger.info(f'Database optimization completed. DB size: {db_size}')
                for table in table_sizes:
                    logger.info(f'Table {table[1]}: {table[2]}')
                    
        except Exception as e:
            logger.error(f'Could not log optimization results: {e}')
