from django.conf import settings

def authentication_backends(request):
    """Make AUTHENTICATION_BACKENDS available in all templates"""
    return {
        'AUTHENTICATION_BACKENDS': getattr(settings, 'AUTHENTICATION_BACKENDS', [])
    }
