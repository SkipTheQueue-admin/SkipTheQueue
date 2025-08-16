"""
Performance optimization utilities for SkipTheQueue
"""

from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def get_cached_menu_items(college_id, category=None, search_query=None):
    """
    Get cached menu items with optimized database queries
    """
    cache_key = f'menu_items_{college_id}'
    if category:
        cache_key += f'_{category}'
    if search_query:
        cache_key += f'_{hash(search_query)}'
    
    menu_items = cache.get(cache_key)
    
    if menu_items is None:
        from .models import MenuItem
        
        # Optimized query with select_related and prefetch_related
        queryset = MenuItem.objects.filter(
            college_id=college_id,
            is_available=True
        ).select_related('college')
        
        if category:
            queryset = queryset.filter(category=category)
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__icontains=search_query)
            )
        
        menu_items = list(queryset.order_by('category', 'name'))
        
        # Cache for 5 minutes
        cache.set(cache_key, menu_items, 300)
    
    return menu_items

def get_cached_college(college_slug):
    """
    Get cached college information
    """
    cache_key = f'college_{college_slug}'
    college = cache.get(cache_key)
    
    if college is None:
        from .models import College
        try:
            college = College.objects.get(slug=college_slug, is_active=True)
            cache.set(cache_key, college, 1800)  # Cache for 30 minutes
        except College.DoesNotExist:
            college = None
    
    return college

def get_cached_user_profile(user_id):
    """
    Get cached user profile
    """
    cache_key = f'user_profile_{user_id}'
    profile = cache.get(cache_key)
    
    if profile is None:
        from .models import UserProfile
        try:
            profile = UserProfile.objects.select_related('user', 'preferred_college').get(user_id=user_id)
            cache.set(cache_key, profile, 300)  # Cache for 5 minutes
        except UserProfile.DoesNotExist:
            profile = None
    
    return profile

def clear_related_caches(college_id=None, user_id=None):
    """
    Clear related caches when data changes
    """
    if college_id:
        # Clear college-related caches
        cache.delete(f'college_{college_id}')
        cache.delete(f'menu_items_{college_id}')
        cache.delete(f'categories_{college_id}')
        
        # Clear all menu item caches for this college
        cache_keys = [
            f'menu_items_{college_id}',
            f'categories_{college_id}',
        ]
        for key in cache_keys:
            cache.delete(key)
    
    if user_id:
        # Clear user-related caches
        cache.delete(f'user_profile_{user_id}')
        cache.delete(f'favorites_{user_id}')

def optimize_queryset(queryset, select_related=None, prefetch_related=None):
    """
    Apply common optimizations to querysets
    """
    if select_related:
        queryset = queryset.select_related(*select_related)
    
    if prefetch_related:
        queryset = queryset.prefetch_related(*prefetch_related)
    
    return queryset

def batch_update_cache(cache_data, timeout=300):
    """
    Batch update multiple cache keys for better performance
    """
    for key, value in cache_data.items():
        cache.set(key, value, timeout)

def get_performance_stats():
    """
    Get performance statistics for monitoring
    """
    stats = {
        'cache_hits': 0,
        'cache_misses': 0,
        'db_queries': 0,
        'response_time': 0,
    }
    
    # This would be populated by middleware or decorators
    return stats
