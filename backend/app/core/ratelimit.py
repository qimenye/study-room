"""进程内滑动窗口限流。

单实例够用；将来多实例部署时替换成 Redis 计数即可，接口保持不变。
"""

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Tuple

_lock = threading.Lock()
_buckets: Dict[Tuple[str, int], Deque[float]] = defaultdict(deque)


def hit(key: str, user_id: int, limit: int, window_seconds: int = 60) -> bool:
    """返回 True 表示允许通过，False 表示被限流。"""
    now = time.monotonic()
    bucket_key = (key, user_id)
    with _lock:
        bucket = _buckets[bucket_key]
        while bucket and now - bucket[0] > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True