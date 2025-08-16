import os
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-default-insecure-secret-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    'skipthequeue.onrender.com',
    'testserver',  # For testing
    '*',  # Allow all hosts in development
]

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'compressor',  # For static file optimization
    'orders',
    'social_django',
]

MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.performance_middleware.PerformanceMiddleware',  # Performance monitoring
    'core.performance_middleware.DatabaseOptimizationMiddleware',  # Database optimization
    'core.middleware.SecurityMiddleware',
    'core.middleware.AuthenticationMiddleware',
    'core.middleware.LoggingMiddleware',
]

ROOT_URLCONF = 'core.urls'

# Template optimization
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,  # Always enable app directories
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database optimization
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR}/db.sqlite3', 
        conn_max_age=300,  # Reduced from 600 for better connection management
        conn_health_checks=True,
        ssl_require=False
    )
}

# Database query optimization
DB_OPTIMIZATION = {
    'ATOMIC_REQUESTS': False,  # Disable for better performance
    'CONN_MAX_AGE': 300,
    'OPTIONS': {
        'timeout': 20,
        'check_same_thread': False,
        'isolation_level': 'READ_COMMITTED',  # Better performance isolation level
    },
    'POOL_OPTIONS': {
        'max_connections': 20,
        'min_connections': 5,
        'connection_timeout': 30,
    }
}

# Cache configuration for better performance
# Enhanced cache configuration for better performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 2000,  # Increased for better cache utilization
            'CULL_FREQUENCY': 3,
        }
    }
}

# Cache optimization settings
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'skipthequeue'
CACHE_MIDDLEWARE_ALIAS = 'default'

# Performance optimization settings
SLOW_REQUEST_THRESHOLD = 1.0  # Log requests slower than 1 second
DB_QUERY_TIMEOUT = 10  # Database query timeout in seconds
MAX_CACHE_ENTRIES = 5000  # Maximum cache entries

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Social Auth (Google OAuth2)
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get('GOOGLE_CLIENT_ID', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

# OAuth Settings
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
    'access_type': 'offline',
    'prompt': 'select_account'
}

# Social Auth Pipeline
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# Disable OAuth if not configured
if not SOCIAL_AUTH_GOOGLE_OAUTH2_KEY or not SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET:
    AUTHENTICATION_BACKENDS = [
        'django.contrib.auth.backends.ModelBackend',
    ]
else:
    AUTHENTICATION_BACKENDS = [
        'social_core.backends.google.GoogleOAuth2',
        'django.contrib.auth.backends.ModelBackend',
    ]

# Use our internal login view
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# CSRF trusted origins (for Render)
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'https://skipthequeue.onrender.com').split(',') 

# Session settings for better performance
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_SAVE_EVERY_REQUEST = False  # Keep False for better performance
SESSION_COOKIE_AGE = 30 * 24 * 60 * 60  # 30 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

# Static files optimization
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
WHITENOISE_MAX_AGE = 31536000  # 1 year
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = False  # Disable for production performance
WHITENOISE_INDEX_FILE = True

# Security settings - optimized for performance
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Enhanced Security Settings - only in production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSRF Settings - optimized
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

# Session Security - optimized
SESSION_COOKIE_SAMESITE = 'Lax'

# Rate Limiting - optimized for performance
RATE_LIMIT_ENABLED = False  # Keep disabled for performance
RATE_LIMIT_REQUESTS = 10000
RATE_LIMIT_WINDOW = 60

# Logging configuration - optimized for performance
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',  # Reduced from INFO for better performance
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'WARNING',  # Reduced from INFO for better performance
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',  # Reduced from INFO for better performance
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',  # Reduced from INFO for better performance
            'propagate': False,
        },
        'orders': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',  # Reduced from INFO for better performance
            'propagate': False,
        },
        'django.db.backends': {
            'level': 'WARNING',  # Reduce SQL logging for performance
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

# Performance monitoring
PERFORMANCE_MONITORING = {
    'ENABLE_QUERY_LOGGING': False,  # Disable for production
    'ENABLE_SLOW_QUERY_LOGGING': True,
    'SLOW_QUERY_THRESHOLD': 0.5,  # Log queries slower than 0.5 seconds
    'SLOW_REQUEST_THRESHOLD': 0.5,  # Log requests slower than 0.5 seconds
    'ENABLE_PERFORMANCE_MONITORING': True,
    'ENABLE_CACHE_MONITORING': True,
    'CACHE_HIT_RATIO_THRESHOLD': 0.8,  # Alert if cache hit ratio is below 80%
}

# Cache key prefixes for better organization
CACHE_KEY_PREFIX = 'skipthequeue'

# Database query optimization
DATABASE_OPTIMIZATION = {
    'ENABLE_QUERY_OPTIMIZATION': True,
    'SELECT_RELATED_DEPTH': 2,
    'PREFETCH_RELATED_DEPTH': 2,
    'BATCH_SIZE': 100,
    'MAX_QUERIES_PER_REQUEST': 50,
}

# Template fragment caching
TEMPLATE_FRAGMENT_CACHE = {
    'ENABLED': True,
    'DEFAULT_TIMEOUT': 300,
    'KEY_PREFIX': 'template',
}

# Static file optimization
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Compression settings
COMPRESS_ENABLED = not DEBUG
COMPRESS_CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter', 'compressor.filters.cssmin.rCSSMinFilter']
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
