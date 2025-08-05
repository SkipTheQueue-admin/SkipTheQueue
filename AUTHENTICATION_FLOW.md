# SkipTheQueue Authentication Flow

## Overview

SkipTheQueue implements a role-based authentication system that automatically redirects users to the appropriate dashboard based on their email address and role.

## User Types & Flow

### 1. Super Admin (skipthequeue.app@gmail.com)
- **Email**: skipthequeue.app@gmail.com
- **Username**: skiptheq
- **Password**: Paras@999stq
- **Redirect**: Super Admin Dashboard (/super-admin/)
- **Access**: Django Admin (/admin/)

### 2. Canteen Staff
- **Email**: Any email assigned to canteen staff
- **Redirect**: Canteen Dashboard for their assigned college
- **Access**: College-specific canteen management

### 3. Regular Users
- **Email**: Any other email
- **Redirect**: User pages (menu, cart, etc.)
- **Access**: Order food, view menu, track orders

## Authentication Flow

### Login Process
1. User visits https://skipthequeue.onrender.com/
2. User clicks "Login with Google"
3. After successful OAuth:
   - **Super Admin**: Automatically redirected to Super Admin Dashboard
   - **Canteen Staff**: Automatically redirected to their college's Canteen Dashboard
   - **Regular Users**: Stay on user pages (menu, cart, etc.)

### Session Management
- Sessions persist for 30 days
- Users stay logged in across browser sessions
- Manual logout available via logout button

## Setup Instructions

### 1. Create Super Admin
```bash
python manage.py setup_superuser
```

### 2. Create Canteen Staff
```bash
python manage.py setup_canteen_staff
```

### 3. Test Authentication Flow
```bash
python manage.py test_auth_flow
```

## URLs

### Public URLs
- `/` - Home page (auto-redirects based on user type)
- `/menu/` - Menu page
- `/cart/` - Shopping cart
- `/login/` - Google OAuth login

### Admin URLs
- `/admin/` - Django Admin (username: skiptheq, password: Paras@999stq)
- `/super-admin/` - Super Admin Dashboard
- `/canteen/login/` - Canteen Staff Login
- `/canteen/dashboard/{college_slug}/` - Canteen Dashboard

## Testing

### Test Authentication Status
Visit: `/test-auth/` to see your current authentication status and user type.

### Django Admin Access
- URL: https://skipthequeue.onrender.com/admin/
- Username: skiptheq
- Password: Paras@999stq

## Security Features

1. **Role-based Access**: Users can only access their assigned areas
2. **Session Security**: Secure cookies, CSRF protection
3. **Auto-redirect**: Prevents unauthorized access attempts
4. **Persistent Sessions**: Users don't need to login repeatedly

## Troubleshooting

### "College not found" Error
- This occurs when a user tries to access a college they're not assigned to
- Solution: Ensure user is properly assigned to the correct college

### Login Issues
- Clear browser cookies and try again
- Ensure using the correct Google account
- Check if user account is active in database

### Django Admin Access Issues
- Run `python manage.py setup_superuser` to reset credentials
- Ensure user has is_superuser=True and is_staff=True

## Deployment Notes

The authentication flow is automatically set up when the app starts on Render via the `startup.py` script, which:
1. Runs database migrations
2. Creates/updates the superuser
3. Collects static files
4. Sets up the application for production use 