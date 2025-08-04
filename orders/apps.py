from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib.auth.models import User

def create_superuser(sender, **kwargs):
    """Create superuser if it doesn't exist"""
    if not User.objects.filter(email='skipthequeue.app@gmail.com').exists():
        try:
            user = User.objects.create_superuser(
                username='skipthequeue',
                email='skipthequeue.app@gmail.com',
                password='SkipTheQueue2024!'
            )
            print(f"✅ Created superuser: {user.username} ({user.email})")
            print("🔑 Password: SkipTheQueue2024!")
        except Exception as e:
            print(f"❌ Error creating superuser: {e}")
    else:
        print("ℹ️ Superuser already exists: skipthequeue.app@gmail.com")

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        # Connect the signal to create superuser after migrations
        post_migrate.connect(create_superuser, sender=self)
