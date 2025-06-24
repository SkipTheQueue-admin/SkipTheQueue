# SkipTheQueue Deployment Checklist

## ✅ **Pre-Deployment Tasks**

### 1. **Environment Setup**
- [ ] Set up production server (Ubuntu/CentOS recommended)
- [ ] Install Python 3.8+ and pip
- [ ] Install PostgreSQL database
- [ ] Install Redis for caching
- [ ] Install Nginx web server
- [ ] Set up SSL certificate (Let's Encrypt)

### 2. **Code Preparation**
- [ ] Update `core/production.py` with your domain
- [ ] Generate a secure SECRET_KEY
- [ ] Set up your payment gateway keys
- [ ] Configure Google Analytics ID
- [ ] Set up Google AdSense publisher ID
- [ ] Replace placeholder PWA icons with your branding

### 3. **Database Setup**
- [ ] Create PostgreSQL database
- [ ] Create database user with proper permissions
- [ ] Update database settings in production.py
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`

### 4. **Static Files**
- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Configure Nginx to serve static files
- [ ] Test PWA icons and manifest

## ✅ **Security Configuration**

### 1. **Django Security**
- [ ] Set `DEBUG = False`
- [ ] Use production SECRET_KEY
- [ ] Enable HTTPS redirect
- [ ] Configure secure cookies
- [ ] Set up CSRF protection
- [ ] Enable HSTS headers

### 2. **Server Security**
- [ ] Configure firewall (UFW)
- [ ] Set up fail2ban
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity
- [ ] Set up automated backups

### 3. **Payment Security**
- [ ] Use HTTPS for all payment pages
- [ ] Configure payment gateway webhooks
- [ ] Test payment flow in sandbox mode
- [ ] Set up payment monitoring
- [ ] Implement fraud detection

## ✅ **Performance Optimization**

### 1. **Database**
- [ ] Set up database indexes
- [ ] Configure connection pooling
- [ ] Regular database maintenance
- [ ] Monitor query performance

### 2. **Caching**
- [ ] Configure Redis caching
- [ ] Set up CDN for static files
- [ ] Enable browser caching
- [ ] Monitor cache hit rates

### 3. **Monitoring**
- [ ] Set up application monitoring
- [ ] Configure error tracking
- [ ] Set up uptime monitoring
- [ ] Monitor server resources

## ✅ **Testing**

### 1. **Functionality Testing**
- [ ] Test user registration and login
- [ ] Test college registration
- [ ] Test menu browsing and cart
- [ ] Test order placement
- [ ] Test payment processing
- [ ] Test order tracking
- [ ] Test admin dashboard
- [ ] Test canteen dashboard

### 2. **Security Testing**
- [ ] Test CSRF protection
- [ ] Test SQL injection protection
- [ ] Test XSS protection
- [ ] Test rate limiting
- [ ] Test payment security
- [ ] Test session security

### 3. **Performance Testing**
- [ ] Load testing with multiple users
- [ ] Test payment gateway under load
- [ ] Test database performance
- [ ] Test mobile responsiveness
- [ ] Test PWA functionality

## ✅ **PWA Testing**

### 1. **Installation**
- [ ] Test "Add to Home Screen" on Android
- [ ] Test "Add to Home Screen" on iOS
- [ ] Verify app icon displays correctly
- [ ] Test app launch from home screen

### 2. **Offline Functionality**
- [ ] Test offline menu browsing
- [ ] Test offline cart functionality
- [ ] Test service worker caching
- [ ] Test offline order tracking

### 3. **Push Notifications**
- [ ] Test order status notifications
- [ ] Test payment confirmation
- [ ] Test order ready notifications

## ✅ **Payment Gateway Integration**

### 1. **Razorpay Setup**
- [ ] Create Razorpay account
- [ ] Get API keys
- [ ] Configure webhooks
- [ ] Test sandbox payments
- [ ] Test live payments

### 2. **Paytm Setup**
- [ ] Create Paytm account
- [ ] Get API keys
- [ ] Configure webhooks
- [ ] Test sandbox payments
- [ ] Test live payments

### 3. **Other Gateways**
- [ ] Configure additional payment gateways
- [ ] Test all payment methods
- [ ] Set up payment monitoring

## ✅ **Analytics and Ads**

### 1. **Google Analytics**
- [ ] Set up Google Analytics 4
- [ ] Configure conversion tracking
- [ ] Set up e-commerce tracking
- [ ] Test data collection

### 2. **Google AdSense**
- [ ] Create AdSense account
- [ ] Add ad units to templates
- [ ] Test ad display
- [ ] Monitor ad performance

## ✅ **Final Deployment**

### 1. **Go Live Checklist**
- [ ] All tests passing
- [ ] Security audit completed
- [ ] Performance optimized
- [ ] Monitoring configured
- [ ] Backup system tested
- [ ] SSL certificate active
- [ ] Domain configured
- [ ] DNS settings updated

### 2. **Post-Deployment**
- [ ] Monitor application logs
- [ ] Monitor error rates
- [ ] Monitor payment success rates
- [ ] Monitor user engagement
- [ ] Monitor server performance
- [ ] Set up automated alerts

### 3. **Maintenance**
- [ ] Regular security updates
- [ ] Database backups
- [ ] Log rotation
- [ ] Performance monitoring
- [ ] User feedback collection
- [ ] Feature updates

## 🚨 **Emergency Contacts**

- **Technical Support**: tech@skipqueue.com
- **Payment Issues**: payments@skipqueue.com
- **Security Issues**: security@skipqueue.com
- **Server Admin**: admin@skipqueue.com

## 📋 **Useful Commands**

```bash
# Check application status
python manage.py check --deploy

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Test payment gateway
python manage.py test orders.tests.PaymentTestCase

# Monitor logs
tail -f /var/log/skipqueue/django.log

# Check server status
systemctl status nginx
systemctl status postgresql
systemctl status redis
```

---

**Last Updated**: December 2024  
**Version**: 1.0  
**Status**: Ready for Production 

```bash
# Run the Django development server
python manage.py runserver
``` 