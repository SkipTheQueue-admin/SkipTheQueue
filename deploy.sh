#!/bin/bash

# SkipTheQueue Deployment Script
# This script handles the deployment process for both local and production

echo "🚀 SkipTheQueue Deployment Script"
echo "=================================="

# Check if we're in production mode
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🌍 Production Mode Detected"
    
    # Collect static files
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput --clear
    
    # Run migrations
    echo "🗄️ Running database migrations..."
    python manage.py migrate
    
    # Start the application
    echo "🚀 Starting application with Gunicorn..."
    exec gunicorn core.wsgi:application --bind 0.0.0.0:$PORT --workers 4 --timeout 120
    
else
    echo "💻 Local Development Mode"
    
    # Check if migrations need to be merged
    echo "🔍 Checking migration status..."
    python manage.py showmigrations orders
    
    # Run migrations if needed
    echo "🗄️ Running migrations..."
    python manage.py migrate
    
    # Collect static files
    echo "📁 Collecting static files..."
    python manage.py collectstatic --noinput
    
    # Start development server
    echo "🚀 Starting development server..."
    python manage.py runserver 0.0.0.0:8000
fi
