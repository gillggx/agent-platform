"""In-memory cache replacing Redis for prototype"""
from typing import Optional, Any
import json
import time


class InMemoryCache:
    """Simple in-memory key-value cache (replaces Redis)"""
    
    def __init__(self):
        self._store: dict[str, dict] = {}  # key -> {"value": ..., "expires_at": ...}
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        entry = self._store.get(key)
        if entry is None:
            return None
        # Check expiry
        if entry.get("expires_at") and time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        return entry["value"]
    
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set value with optional TTL (seconds)"""
        expires_at = None
        if ex is not None:
            expires_at = time.time() + ex
        self._store[key] = {"value": value, "expires_at": expires_at}
    
    async def delete(self, key: str):
        """Delete key"""
        self._store.pop(key, None)
    
    def cleanup_expired(self):
        """Remove all expired entries"""
        now = time.time()
        expired_keys = [
            k for k, v in self._store.items()
            if v.get("expires_at") and now > v["expires_at"]
        ]
        for k in expired_keys:
            del self._store[k]


# Global instance
cache = InMemoryCache()
