import time, threading
class TTLCache:
    def __init__(self): self._d={}; self._lock=threading.RLock()
    def set(self,k,v,ttl=60):
        if ttl<=0: raise ValueError('ttl must be positive')
        with self._lock:self._d[k]=(v,time.monotonic()+ttl)
    def get(self,k):
        with self._lock:
            x=self._d.get(k)
            if not x:return None
            if x[1]<=time.monotonic():self._d.pop(k,None);return None
            return x[0]
    def delete(self,k):
        with self._lock:self._d.pop(k,None)
    def clear(self):
        with self._lock:self._d.clear()
class RedisCache:
    def __init__(self,url):
        try: import redis
        except ImportError as e: raise RuntimeError('Redis adapter requires redis package') from e
        self.client=redis.Redis.from_url(url,decode_responses=False)
    def set(self,k,v,ttl=60):
        if ttl<=0: raise ValueError('ttl must be positive')
        import pickle; self.client.setex(k,ttl,pickle.dumps(v))
    def get(self,k):
        import pickle; v=self.client.get(k); return None if v is None else pickle.loads(v)
    def delete(self,k): self.client.delete(k)
