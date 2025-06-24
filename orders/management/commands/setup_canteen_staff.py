from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from orders.models import College, CanteenStaff
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import getpass

class Command(BaseCommand):
    help = 'Set up canteen staff accounts for colleges'

    def add_arguments(self, parser):
        parser.add_argument(
            '--college-slug',
            type=str,
            help='Slug of the college to add canteen staff to'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email address for the canteen staff account'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Username for the canteen staff account'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            help='First name of the canteen staff'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            help='Last name of the canteen staff'
        )
        parser.add_argument(
            '--list-colleges',
            action='store_true',
            help='List all available colleges'
        )
        parser.add_argument(
            '--list-staff',
            action='store_true',
            help='List all canteen staff'
        )

    def handle(self, *args, **options):
        if options['list_colleges']:
            self.list_colleges()
            return
        
        if options['list_staff']:
            self.list_staff()
            return

        # Interactive mode
        if not options['college_slug']:
            self.interactive_setup()
        else:
            self.create_staff_account(options)

    def list_colleges(self):
        """List all available colleges"""
        colleges = College.objects.filter(is_active=True)
        if not colleges:
            self.stdout.write(
                self.style.WARNING('No active colleges found.')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {colleges.count()} active colleges:')
        )
        for college in colleges:
            self.stdout.write(f'  - {college.name} (slug: {college.slug})')

    def list_staff(self):
        """List all canteen staff"""
        staff = CanteenStaff.objects.filter(is_active=True).select_related('user', 'college')
        if not staff:
            self.stdout.write(
                self.style.WARNING('No active canteen staff found.')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {staff.count()} active canteen staff:')
        )
        for member in staff:
            self.stdout.write(
                f'  - {member.user.get_full_name() or member.user.username} '
                f'({member.user.email}) at {member.college.name}'
            )

    def interactive_setup(self):
        """Interactive setup for canteen staff"""
        self.stdout.write(
            self.style.SUCCESS('=== Canteen Staff Setup ===')
        )
        
        # List available colleges
        colleges = College.objects.filter(is_active=True)
        if not colleges:
            self.stdout.write(
                self.style.ERROR('No active colleges found. Please create a college first.')
            )
            return
        
        self.stdout.write('\nAvailable colleges:')
        for i, college in enumerate(colleges, 1):
            self.stdout.write(f'{i}. {college.name} (slug: {college.slug})')
        
        # Get college selection
        while True:
            try:
                choice = input('\nSelect college number: ').strip()
                college_index = int(choice) - 1
                if 0 <= college_index < len(colleges):
                    college = colleges[college_index]
                    break
                else:
                    self.stdout.write(
                        self.style.ERROR('Invalid selection. Please try again.')
                    )
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Please enter a valid number.')
                )
        
        # Get user details
        self.stdout.write(f'\nSetting up canteen staff for: {college.name}')
        
        # Email
        while True:
            email = input('Email address: ').strip()
            try:
                validate_email(email)
                if User.objects.filter(email=email).exists():
                    self.stdout.write(
                        self.style.WARNING('User with this email already exists.')
                    )
                    continue
                break
            except ValidationError:
                self.stdout.write(
                    self.style.ERROR('Please enter a valid email address.')
                )
        
        # Username
        while True:
            username = input('Username: ').strip()
            if not username:
                username = email.split('@')[0]  # Use email prefix as username
                self.stdout.write(f'Using username: {username}')
            
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING('Username already taken. Please choose another.')
                )
                continue
            break
        
        # Name
        first_name = input('First name: ').strip()
        last_name = input('Last name: ').strip()
        
        # Password
        while True:
            password = getpass.getpass('Password: ')
            if len(password) < 8:
                self.stdout.write(
                    self.style.ERROR('Password must be at least 8 characters long.')
                )
                continue
            
            confirm_password = getpass.getpass('Confirm password: ')
            if password != confirm_password:
                self.stdout.write(
                    self.style.ERROR('Passwords do not match.')
                )
                continue
            break
        
        # Create user and staff account
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            canteen_staff = CanteenStaff.objects.create(
                user=user,
                college=college,
                is_active=True,
                can_accept_orders=True,
                can_update_status=True,
                can_view_orders=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Canteen staff account created successfully!\n'
                    f'User: {user.get_full_name() or user.username}\n'
                    f'Email: {user.email}\n'
                    f'College: {college.name}\n'
                    f'Login URL: /canteen/login/\n'
                    f'Dashboard URL: /canteen/dashboard/{college.slug}/'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating account: {str(e)}')
            )

    def create_staff_account(self, options):
        """Create staff account with provided options"""
        try:
            # Validate college
            college = College.objects.get(slug=options['college_slug'], is_active=True)
        except College.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'College with slug "{options["college_slug"]}" not found or not active.')
            )
            return
        
        # Validate email
        email = options['email']
        try:
            validate_email(email)
        except ValidationError:
            self.stdout.write(
                self.style.ERROR('Invalid email address.')
            )
            return
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR('User with this email already exists.')
            )
            return
        
        # Get username
        username = options['username'] or email.split('@')[0]
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR('Username already taken.')
            )
            return
        
        # Get password
        password = getpass.getpass('Password: ')
        if len(password) < 8:
            self.stdout.write(
                self.style.ERROR('Password must be at least 8 characters long.')
            )
            return
        
        confirm_password = getpass.getpass('Confirm password: ')
        if password != confirm_password:
            self.stdout.write(
                self.style.ERROR('Passwords do not match.')
            )
            return
        
        # Create user and staff account
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=options.get('first_name', ''),
                last_name=options.get('last_name', '')
            )
            
            canteen_staff = CanteenStaff.objects.create(
                user=user,
                college=college,
                is_active=True,
                can_accept_orders=True,
                can_update_status=True,
                can_view_orders=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Canteen staff account created successfully!\n'
                    f'User: {user.get_full_name() or user.username}\n'
                    f'Email: {user.email}\n'
                    f'College: {college.name}\n'
                    f'Login URL: /canteen/login/\n'
                    f'Dashboard URL: /canteen/dashboard/{college.slug}/'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating account: {str(e)}')
            ) 