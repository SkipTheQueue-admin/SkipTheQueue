from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from orders.models import College, CanteenStaff

class Command(BaseCommand):
    help = 'Add canteen staff to a college'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the canteen staff')
        parser.add_argument('college_slug', type=str, help='Slug of the college')
        parser.add_argument('--email', type=str, help='Email for the user (if user does not exist)')
        parser.add_argument('--password', type=str, help='Password for the user (if user does not exist)')

    def handle(self, *args, **options):
        username = options['username']
        college_slug = options['college_slug']
        email = options.get('email')
        password = options.get('password')

        try:
            # Get or create user
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email or f'{username}@example.com',
                    'first_name': username.title(),
                    'is_staff': True,
                }
            )
            
            if created and password:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {username}')
                )
            elif created:
                self.stdout.write(
                    self.style.WARNING(f'Created user: {username} (set password manually)')
                )

            # Get college
            college = College.objects.get(slug=college_slug)
            
            # Create canteen staff
            canteen_staff, created = CanteenStaff.objects.get_or_create(
                user=user,
                college=college,
                defaults={
                    'is_active': True,
                    'can_accept_orders': True,
                    'can_update_status': True,
                    'can_view_orders': True,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Added {username} as canteen staff for {college.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'{username} is already canteen staff for {college.name}')
                )
                
        except College.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'College with slug "{college_slug}" not found')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            ) 