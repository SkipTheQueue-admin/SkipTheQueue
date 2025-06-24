from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from orders.models import College, MenuItem, UserProfile
from django.utils import timezone

class Command(BaseCommand):
    help = 'Setup sample data for SkipTheQueue'

    def handle(self, *args, **options):
        self.stdout.write('Setting up sample data...')
        
        # Clear existing data
        MenuItem.objects.all().delete()
        College.objects.all().delete()
        
        # Create Ramdeo Baba College
        college = College.objects.create(
            name='Ramdeo Baba College of Engineering and Management',
            slug='ramdeo-baba-college',
            address='Ramdeo Baba College, Nagpur, Maharashtra',
            is_active=True,
            admin_name='College Admin',
            admin_email='admin@ramdeobaba.ac.in',
            admin_phone='+91-712-1234567',
            allow_pay_later=True,
            payment_gateway_enabled=True,
            estimated_preparation_time=15
        )
        
        self.stdout.write(f'Created college: {college.name}')
        
        # Create menu items
        menu_items = [
            # Breakfast
            {'name': 'Masala Dosa', 'description': 'Crispy dosa with potato filling and chutney', 'price': 60.00, 'category': 'Breakfast'},
            {'name': 'Idli Sambar', 'description': 'Soft idli with hot sambar and coconut chutney', 'price': 40.00, 'category': 'Breakfast'},
            {'name': 'Poha', 'description': 'Flattened rice with vegetables and spices', 'price': 35.00, 'category': 'Breakfast'},
            {'name': 'Bread Omelette', 'description': 'Fresh bread with egg omelette', 'price': 45.00, 'category': 'Breakfast'},
            {'name': 'Tea', 'description': 'Hot masala tea', 'price': 15.00, 'category': 'Beverages'},
            {'name': 'Coffee', 'description': 'Filter coffee', 'price': 20.00, 'category': 'Beverages'},
            
            # Main Course
            {'name': 'Veg Thali', 'description': 'Complete meal with rice, dal, vegetables, roti, and salad', 'price': 80.00, 'category': 'Main Course'},
            {'name': 'Chicken Biryani', 'description': 'Aromatic rice with tender chicken pieces', 'price': 120.00, 'category': 'Main Course'},
            {'name': 'Paneer Butter Masala', 'description': 'Cottage cheese in rich tomato gravy', 'price': 90.00, 'category': 'Main Course'},
            {'name': 'Dal Khichdi', 'description': 'Comfort food with rice and lentils', 'price': 70.00, 'category': 'Main Course'},
            {'name': 'Roti', 'description': 'Whole wheat flatbread', 'price': 15.00, 'category': 'Main Course'},
            {'name': 'Rice', 'description': 'Steamed basmati rice', 'price': 25.00, 'category': 'Main Course'},
            
            # Snacks
            {'name': 'Samosa', 'description': 'Crispy pastry with potato and peas filling', 'price': 25.00, 'category': 'Snacks'},
            {'name': 'Vada Pav', 'description': 'Mumbai style potato fritter in bread', 'price': 30.00, 'category': 'Snacks'},
            {'name': 'Pav Bhaji', 'description': 'Spicy vegetable curry with bread', 'price': 50.00, 'category': 'Snacks'},
            {'name': 'French Fries', 'description': 'Crispy potato fries', 'price': 40.00, 'category': 'Snacks'},
            {'name': 'Sandwich', 'description': 'Grilled vegetable sandwich', 'price': 45.00, 'category': 'Snacks'},
            
            # Beverages
            {'name': 'Lassi', 'description': 'Sweet yogurt drink', 'price': 30.00, 'category': 'Beverages'},
            {'name': 'Lemon Soda', 'description': 'Refreshing lemon soda', 'price': 25.00, 'category': 'Beverages'},
            {'name': 'Milk Shake', 'description': 'Chocolate milk shake', 'price': 50.00, 'category': 'Beverages'},
            {'name': 'Cold Coffee', 'description': 'Iced coffee with cream', 'price': 40.00, 'category': 'Beverages'},
            
            # Desserts
            {'name': 'Gulab Jamun', 'description': 'Sweet milk dumplings in sugar syrup', 'price': 35.00, 'category': 'Desserts'},
            {'name': 'Rasgulla', 'description': 'Soft cottage cheese balls in syrup', 'price': 30.00, 'category': 'Desserts'},
            {'name': 'Ice Cream', 'description': 'Vanilla ice cream', 'price': 40.00, 'category': 'Desserts'},
            {'name': 'Jalebi', 'description': 'Crispy sweet pretzel', 'price': 25.00, 'category': 'Desserts'},
        ]
        
        for item_data in menu_items:
            menu_item = MenuItem.objects.create(
                name=item_data['name'],
                description=item_data['description'],
                price=item_data['price'],
                category=item_data['category'],
                college=college,
                is_available=True,
                stock_quantity=100,
                is_stock_managed=False
            )
            self.stdout.write(f'Created menu item: {menu_item.name}')
        
        self.stdout.write(self.style.SUCCESS('Sample data setup completed successfully!'))
        self.stdout.write(f'Created {len(menu_items)} menu items for {college.name}') 