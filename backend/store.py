from dataclasses import dataclass
from threading import Lock
from time import monotonic
from uuid import uuid4

from fastapi import HTTPException


@dataclass(frozen=True)
class StoredSystem:
    source: bytes
    name: str
    num_states: int
    schemas: dict
    created: float


class SystemStore:
    def __init__(self, capacity=100, ttl=3600):
        self.capacity = capacity
        self.ttl = ttl
        self._items = {}
        self._lock = Lock()

    def _expire(self):
        now = monotonic()
        for key in list(self._items):
            if now - self._items[key].created >= self.ttl:
                del self._items[key]

    def add(self, source, name, num_states, schemas):
        with self._lock:
            self._expire()
            if len(self._items) >= self.capacity:
                raise HTTPException(503, 'Upload capacity reached. Remove an unused system or try again later.')
            key = str(uuid4())
            self._items[key] = StoredSystem(source, name, num_states, schemas, monotonic())
            return key

    def get(self, key):
        with self._lock:
            self._expire()
            if key not in self._items:
                raise HTTPException(404, 'System expired or not found. Please upload the dynamics file again.')
            return self._items[key]

    def delete(self, key):
        with self._lock:
            self._expire()
            if key not in self._items:
                raise HTTPException(404, 'System not found.')
            del self._items[key]

    def clear(self):
        with self._lock:
            self._items.clear()
