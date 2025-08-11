from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create a superuser account for SkipTheQueue'

    def handle(self, *args, **options):
        # Check if user already exists
        if User.objects.filter(email='skipthequeue.app@gmail.com').exists():
            self.stdout.write(
                self.style.WARNING('Superuser already exists with email skipthequeue.app@gmail.com')
            )
            return

        # Create superuser
        user = User.objects.create_superuser(
            username='skipthequeue',
            email='skipthequeue.app@gmail.com',
            password='Paras@999'
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created superuser: {user.username} ({user.email})')
        )
        self.stdout.write('Password: Paras@999') 