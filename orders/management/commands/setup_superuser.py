from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Command(BaseCommand):
    help = 'Create or update superuser with specified credentials'

    def handle(self, *args, **options):
        email = 'skipthequeue.app@gmail.com'
        username = 'skiptheq'
        password = 'Paras@999stq'
        
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
            self.stdout.write(
                self.style.WARNING(f'Updated existing user: {username}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Created new superuser: {username}')
            )
        
        # Set password
        user.set_password(password)
        user.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Superuser setup complete!\n'
                f'Username: {username}\n'
                f'Email: {email}\n'
                f'Password: {password}\n'
                f'Django Admin URL: /admin/'
            )
        ) 