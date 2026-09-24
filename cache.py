"""執行緒安全的 TTL 記憶體快取。用於避免對來源站高頻重複抓取。"""
import threading
import time


class TTLCache:
    def __init__(self, ttl=None):
        self.ttl = ttl
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            value, expires = item
            if expires < now:
                del self._store[key]
                return None
            return value

    def set(self, key, value, ttl=None):
        ttl = self.ttl if ttl is None else ttl
        with self._lock:
            self._store[key] = (value, time.time() + ttl)
        return value

    def get_or_set(self, key, producer, ttl=None):
        cached = self.get(key)
        if cached is not None:
            return cached
        value = producer()
        return self.set(key, value, ttl)

    def clear(self):
        with self._lock:
            self._store.clear()
