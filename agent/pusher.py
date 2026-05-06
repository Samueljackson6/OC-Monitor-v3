"""Batch push engine for collector metrics."""
import asyncio
import json
import time
from collections import deque
from pathlib import Path
from typing import List, Optional
import httpx
from collector import MetricSnapshot


class PushEngine:
    def __init__(
        self,
        endpoint: str,
        token: str = "",
        batch_size: int = 10,
        batch_window: int = 5,
        max_retries: int = 5,
        cache_size: int = 1000,
        cache_dir: Optional[Path] = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.batch_size = batch_size
        self.batch_window = batch_window
        self.max_retries = max_retries
        self.buffer: deque[MetricSnapshot] = deque(maxlen=cache_size)
        self.cache_dir = cache_dir or Path("/tmp/oc-monitor-cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.AsyncClient(timeout=10)
        self._last_flush = time.time()
        self._retry_count = 0

    async def push(self, metric: MetricSnapshot):
        self.buffer.append(metric)
        if len(self.buffer) >= self.batch_size or time.time() - self._last_flush >= self.batch_window:
            await self._flush()

    async def _flush(self):
        if not self.buffer:
            return
        batch = list(self.buffer)
        self.buffer.clear()
        success = await self._send_batch(batch)
        if success:
            self._last_flush = time.time()
            self._retry_count = 0
            return
        self.buffer.extend(batch)
        await self._save_to_cache(batch)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-OC-Monitor-Token"] = self.token
        return headers

    async def _send_batch(self, batch: List[MetricSnapshot]) -> bool:
        try:
            response = await self.client.post(
                f"{self.endpoint}/api/v1/metrics/batch",
                headers=self._headers(),
                json={"metrics": [m.to_dict() for m in batch]},
            )
            if response.status_code == 200:
                print(f"sent {len(batch)} metrics")
                return True
            print(f"send failed: HTTP {response.status_code} {response.text[:200]}")
            return False
        except Exception as exc:
            print(f"send exception: {exc}")
            return False

    async def _save_to_cache(self, batch: List[MetricSnapshot]):
        cache_file = self.cache_dir / f"metrics_{int(time.time())}.json"
        try:
            cache_file.write_text(json.dumps([m.to_dict() for m in batch]), encoding="utf-8")
            print(f"cached metrics: {cache_file}")
        except Exception as exc:
            print(f"cache failed: {exc}")

    async def retry_with_backoff(self):
        if self._retry_count >= self.max_retries:
            print("max retry count reached")
            return
        wait_time = min(2 ** self._retry_count, 60)
        self._retry_count += 1
        await asyncio.sleep(wait_time)
        await self._flush()

    async def flush_cached_data(self):
        cache_files = sorted(self.cache_dir.glob("metrics_*.json"))
        for cache_file in cache_files:
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                batch = [MetricSnapshot(**m) for m in data]
                if await self._send_batch(batch):
                    cache_file.unlink()
                else:
                    break
            except Exception as exc:
                print(f"cache replay failed {cache_file.name}: {exc}")

    async def close(self):
        await self._flush()
        await self.client.aclose()
