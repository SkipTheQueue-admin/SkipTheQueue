# Canteen Staff System Guide

## Overview

The SkipTheQueue canteen staff system provides secure access for college canteen staff to manage orders, menu items, and view analytics. This system is completely separate from the public-facing website and requires authentication.

## Security Features

- **Separate Authentication**: Canteen staff use email/password login instead of Google OAuth
- **Role-based Access**: Staff can only access their assigned college's data
- **Permission System**: Granular permissions for accepting orders, updating status, and viewing data
- **Session Management**: Secure session handling with automatic logout
- **CSRF Protection**: All forms are protected against CSRF attacks
- **Rate Limiting**: API endpoints are rate-limited to prevent abuse

## URL Structure

### Public URLs (Students)
- `/` - Home page
- `/menu/` - Menu page
- `/cart/` - Shopping cart
- `/place-order/` - Place order

### Canteen Staff URLs (Private)
- `/canteen/login/` - Canteen staff login
- `/canteen/dashboard/{college_slug}/` - Main dashboard
- `/canteen/dashboard/{college_slug}/menu/` - Menu management
- `/canteen/dashboard/{college_slug}/history/` - Order history
- `/canteen/logout/` - Logout

## Setting Up Canteen Staff

### Method 1: Interactive Setup (Recommended)

```bash
python manage.py setup_canteen_staff
```

This will:
1. List all available colleges
2. Let you select a college
3. Collect staff details (email, name, password)
4. Create the user account and link it to the college

### Method 2: Command Line Setup

```bash
python manage.py setup_canteen_staff \
    --college-slug your-college-slug \
    --email staff@college.com \
    --first-name "John" \
    --last-name "Doe"
```

### Method 3: List Existing Data

```bash
# List all colleges
python manage.py setup_canteen_staff --list-colleges

# List all canteen staff
python manage.py setup_canteen_staff --list-staff
```

## Canteen Staff Features

### 1. Dashboard (`/canteen/dashboard/{college_slug}/`)

**Statistics Cards:**
- Pending Orders: Orders waiting to be accepted
- Today's Orders: Total orders placed today
- In Progress: Orders being prepared
- Today's Revenue: Total revenue from completed orders today

**Active Orders Management:**
- View all active orders (Paid, In Progress, Ready)
- Accept orders (changes status from Paid to In Progress)
- Mark orders as ready (changes status to Ready)
- Complete orders (changes status to Completed)
- Decline orders (changes status to Declined)

**Real-time Updates:**
- Auto-refresh every 30 seconds
- Live status indicators
- Instant notifications for actions

### 2. Menu Management (`/canteen/dashboard/{college_slug}/menu/`)

**Menu Item Operations:**
- Toggle item availability (Enable/Disable)
- Update item prices
- Update stock quantities (if stock management is enabled)
- View item statistics

**Statistics:**
- Total menu items
- Available items count
- Categories count
- Stock-managed items count

### 3. Order History (`/canteen/dashboard/{college_slug}/history/`)

**Filtering Options:**
- Date range (From/To)
- Order status filter
- Search and filter orders

**Analytics:**
- Total orders count
- Total revenue
- Average order value
- Completed orders count

**Order Details:**
- Customer information
- Order items and quantities
- Payment method and status
- Special instructions
- Order timestamps

## Access Control

### Permission Levels

Each canteen staff member has specific permissions:

- **can_accept_orders**: Can accept/decline orders
- **can_update_status**: Can update order status (In Progress → Ready → Completed)
- **can_view_orders**: Can view order history and analytics

### College Isolation

- Staff can only see orders and menu items for their assigned college
- No cross-college data access
- Super admin can access all colleges

## Security Best Practices

### For Administrators

1. **Strong Passwords**: Ensure canteen staff use strong passwords (minimum 8 characters)
2. **Regular Account Review**: Periodically review active canteen staff accounts
3. **Limited Access**: Only grant necessary permissions to each staff member
4. **Secure Communication**: Share login credentials securely with college staff

### For Canteen Staff

1. **Secure Login**: Use the dedicated canteen login page (`/canteen/login/`)
2. **Logout**: Always logout when finished (especially on shared computers)
3. **Password Security**: Don't share passwords with others
4. **Report Issues**: Contact administrators for any security concerns

## Troubleshooting

### Common Issues

**"Access denied" error:**
- Check if the user is assigned to the correct college
- Verify the user account is active
- Ensure the college is active

**"College not found" error:**
- Verify the college slug in the URL
- Check if the college is active in the database

**Login issues:**
- Ensure using the correct email address
- Check if the password is correct
- Verify the user account is active

### Support Commands

```bash
# Check if a user exists
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.filter(email='staff@college.com').exists()

# Check canteen staff assignments
>>> from orders.models import CanteenStaff
>>> CanteenStaff.objects.filter(user__email='staff@college.com')

# List all colleges
python manage.py setup_canteen_staff --list-colleges
```

## Deployment Checklist

### Before Going Live

1. **Create Canteen Staff Accounts**: Use the setup command for each college
2. **Test Login**: Verify all staff can log in successfully
3. **Test Permissions**: Ensure staff can only access their college's data
4. **Test Order Management**: Verify order status updates work correctly
5. **Test Menu Management**: Ensure menu updates work properly

### Security Verification

1. **URL Protection**: Verify canteen URLs are not accessible without login
2. **Data Isolation**: Confirm staff can't see other colleges' data
3. **Session Security**: Test logout functionality
4. **CSRF Protection**: Verify all forms have CSRF tokens

### Monitoring

1. **Log Monitoring**: Check Django logs for authentication attempts
2. **Order Activity**: Monitor order processing times
3. **User Activity**: Track staff login patterns
4. **Error Tracking**: Monitor for any access denied errors

## API Endpoints

### For Developers

The system includes secure API endpoints for real-time updates:

- `GET /api/orders/{college_slug}/` - Get orders JSON (super admin only)
- `POST /canteen/dashboard/{college_slug}/accept-order/{order_id}/` - Accept order
- `POST /canteen/dashboard/{college_slug}/decline-order/{order_id}/` - Decline order
- `POST /canteen/dashboard/{college_slug}/update-status/{order_id}/` - Update order status

All endpoints require authentication and proper permissions.

## Contact and Support

For technical support or questions about the canteen staff system:

1. Check this documentation first
2. Review Django logs for error messages
3. Use the management commands for troubleshooting
4. Contact the system administrator for additional help

---

**Important**: The canteen staff system is designed to be secure and isolated. Never share canteen staff login credentials publicly or include them in public documentation. 