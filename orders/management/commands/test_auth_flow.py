from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from orders.models import CanteenStaff, College

class Command(BaseCommand):
    help = 'Test authentication flow and user types'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Testing Authentication Flow...")
        
        # Test superuser
        admin_user = User.objects.filter(email='skipthequeue.app@gmail.com').first()
        if admin_user:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Super Admin User Found:\n"
                    f"   Username: {admin_user.username}\n"
                    f"   Email: {admin_user.email}\n"
                    f"   Is Superuser: {admin_user.is_superuser}\n"
                    f"   Is Staff: {admin_user.is_staff}\n"
                    f"   Is Active: {admin_user.is_active}"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR("❌ Super Admin User Not Found!")
            )
        
        # Test canteen staff
        canteen_staff_list = CanteenStaff.objects.filter(is_active=True).select_related('user', 'college')
        if canteen_staff_list:
            self.stdout.write(f"\n📋 Found {canteen_staff_list.count()} Canteen Staff:")
            for staff in canteen_staff_list:
                self.stdout.write(
                    f"   - {staff.user.username} ({staff.user.email}) → {staff.college.name}"
                )
        else:
            self.stdout.write(self.style.WARNING("⚠️ No Canteen Staff Found"))
        
        # Test colleges
        colleges = College.objects.filter(is_active=True)
        if colleges:
            self.stdout.write(f"\n🏫 Found {colleges.count()} Active Colleges:")
            for college in colleges:
                self.stdout.write(f"   - {college.name} (slug: {college.slug})")
        else:
            self.stdout.write(self.style.WARNING("⚠️ No Active Colleges Found"))
        
        # Test regular users
        regular_users = User.objects.filter(
            is_superuser=False,
            is_staff=False
        ).exclude(
            canteen_staff__isnull=False
        )
        
        self.stdout.write(f"\n👥 Found {regular_users.count()} Regular Users")
        
        self.stdout.write(
            self.style.SUCCESS("\n✅ Authentication Flow Test Complete!")
        ) 