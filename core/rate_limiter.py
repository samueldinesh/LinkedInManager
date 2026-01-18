import asyncio
import time
from collections import deque

class RateLimiter:
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period
        self.history = deque()
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        async with self._lock:
            self._clean_history()
            if len(self.history) >= self.calls:
                wait_time = self.period - (time.monotonic() - self.history[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            self.history.append(time.monotonic())

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def _clean_history(self):
        now = time.monotonic()
        while self.history and now - self.history[0] > self.period:
            self.history.popleft()