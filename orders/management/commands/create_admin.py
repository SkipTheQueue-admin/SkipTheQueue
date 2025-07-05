from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create a superuser account'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='skipthequeue.app@gmail.com',
            help='Email for the admin account'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='skiptheq',
            help='Username for the admin account'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='Skip1the1queue@paras999',
            help='Password for the admin account'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        
        if not User.objects.filter(is_superuser=True).exists():
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Superuser created successfully!\n'
                    f'👤 Username: {user.username}\n'
                    f'📧 Email: {user.email}\n'
                    f'🔑 Password: {password}\n'
                    f'🔗 Login at: https://skipthequeue.onrender.com/admin/'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ Superuser already exists')
            ) 