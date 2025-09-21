# backend/app/services/cache_service.py - CREATE NEW FILE
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List
import redis
import pickle
import logging

logger = logging.getLogger(__name__)

class CacheService:
    """Advanced caching service with multiple strategies"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hour
        self.cache_prefix = "cache:"
        
    async def get(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """Get cached value"""
        try:
            cache_key = f"{self.cache_prefix}{key}"
            cached_data = self.redis.get(cache_key)
            
            if cached_data:
                if deserialize:
                    return pickle.loads(cached_data)
                return cached_data.decode('utf-8')
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """Set cached value"""
        try:
            cache_key = f"{self.cache_prefix}{key}"
            ttl = ttl or self.default_ttl
            
            if serialize:
                serialized_value = pickle.dumps(value)
            else:
                serialized_value = str(value).encode('utf-8')
            
            return self.redis.setex(cache_key, ttl, serialized_value)
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete cached value"""
        try:
            cache_key = f"{self.cache_prefix}{key}"
            return bool(self.redis.delete(cache_key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        callback: callable,
        ttl: Optional[int] = None,
        *args,
        **kwargs
    ) -> Any:
        """Get cached value or compute and cache it"""
        cached_value = await self.get(key)
        
        if cached_value is not None:
            return cached_value
        
        # Compute value
        value = await callback(*args, **kwargs) if callable(callback) else callback
        
        # Cache the computed value
        await self.set(key, value, ttl)
        
        return value
    
    def cache_key_for_user_transcriptions(self, user_id: str, page: int = 1) -> str:
        """Generate cache key for user transcriptions"""
        return f"user_transcriptions:{user_id}:page:{page}"
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        pattern = f"{self.cache_prefix}user_*:{user_id}:*"
        keys = self.redis.keys(pattern)
        
        if keys:
            self.redis.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries for user {user_id}")

# Cache decorators
def cache_result(ttl: int = 3600, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # You'll need to inject cache_service instance
            # For now, we'll skip caching in decorator
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator