# Tawk.to Setup Guide for SkipTheQueue

## ✅ What's Already Done

I've already added the Tawk.to widget code to your `base.html` template. The widget will now appear on all pages of your website.

## 🔧 Next Steps to Complete Setup

### Step 1: Create Tawk.to Account

1. Go to [https://www.tawk.to](https://www.tawk.to)
2. Click "Get Started Free"
3. Sign up with your email address
4. No credit card required!

### Step 2: Get Your Widget Code

1. After signing up, you'll be taken to the dashboard
2. Click on "Administration" → "Chat Widget"
3. Copy your unique widget ID (it looks like: `5f7d1234567890abcdef1234`)

### Step 3: Update Your Code

Replace `YOUR_TAWK_TO_WIDGET_ID` in your `base.html` file with your actual widget ID:

```html
<!-- Find this line in orders/templates/orders/base.html -->
s1.src='https://embed.tawk.to/YOUR_TAWK_TO_WIDGET_ID/default';

<!-- Replace with your actual ID, for example: -->
s1.src='https://embed.tawk.to/5f7d1234567890abcdef1234/default';
```

### Step 4: Customize Your Chat Widget

1. **In Tawk.to Dashboard:**
   - Go to "Administration" → "Chat Widget"
   - Customize colors, position, and appearance
   - Set your welcome message

2. **Recommended Welcome Message:**
   ```
   👋 Hi! Welcome to SkipTheQueue! 
   
   I'm here to help you with:
   • Placing orders
   • Tracking your order
   • Payment issues
   • Menu questions
   • Technical support
   
   How can I help you today?
   ```

### Step 5: Set Up Quick Responses

In your Tawk.to dashboard, create these quick responses:

#### **Order Help:**
- "How do I place an order?" → "Go to the Menu page, add items to cart, and click 'Place Order'"
- "Where is my order?" → "Check the 'Track Order' page or 'My Orders' section"
- "Can I cancel my order?" → "Orders can only be cancelled within 5 minutes of placement"

#### **Payment Help:**
- "Payment failed" → "Try using UPI or check your card balance. Contact support if the issue persists."
- "What payment methods do you accept?" → "We accept UPI, credit/debit cards, and cash on delivery"

#### **Menu Help:**
- "What's on the menu today?" → "Check our Menu page for today's available items"
- "Is there a vegetarian option?" → "Yes! We have many vegetarian items. Check the Menu page for details"

#### **Technical Help:**
- "App not loading" → "Try refreshing the page or clearing your browser cache"
- "Can't add to cart" → "Make sure you're logged in and have selected a college"

## 🎨 Customization Options

### Widget Appearance
- **Position**: Bottom right (recommended)
- **Colors**: Match your app's blue/purple theme
- **Size**: Medium (good for mobile and desktop)

### Auto-Show Settings
- **Current setting**: Shows after 10 seconds
- **You can change this** in the Tawk.to dashboard

### Visitor Information
The widget automatically shows:
- User's name (if logged in)
- User's email (if logged in)
- User role (Student/Guest)
- Selected college

## 📱 Mobile Optimization

The widget is already mobile-optimized and will work perfectly on:
- ✅ Mobile phones
- ✅ Tablets
- ✅ Desktop computers
- ✅ PWA (Progressive Web App)

## 🔒 Privacy & Security

- **GDPR Compliant**: Tawk.to is GDPR compliant
- **No Personal Data**: Only shows what you configure
- **Secure**: Uses HTTPS encryption
- **Free Forever**: No hidden costs

## 🚀 Testing Your Setup

1. **Start your Django server:**
   ```bash
   python manage.py runserver
   ```

2. **Visit your website** and wait 10 seconds

3. **You should see** a chat widget appear in the bottom right

4. **Test the chat** by sending a message

5. **Check your Tawk.to dashboard** to see the conversation

## 📊 Analytics & Reports

Once set up, you can view:
- **Chat conversations** in real-time
- **Visitor information** and behavior
- **Response times** and satisfaction
- **Popular questions** and topics

## 🆘 Support

If you need help:
1. Check Tawk.to's help center
2. Contact Tawk.to support (they're very responsive)
3. Check the browser console for any errors

## 💡 Pro Tips

1. **Set up notifications** in Tawk.to to get alerts when someone messages
2. **Create canned responses** for common questions
3. **Use the mobile app** to respond on the go
4. **Set business hours** so visitors know when you'll respond
5. **Add your team members** to help manage chats

---

**That's it!** Your SkipTheQueue app now has a professional chat support system that will help your students and reduce your support workload. 🎉 