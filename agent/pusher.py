"""
OC-Monitor v3.0 - 推送引擎
设计目标: 批量发送、失败重试、断网容灾
"""
import asyncio
import time
import json
from collections import deque
from pathlib import Path
from typing import List, Optional, Callable
import httpx

from collector import MetricSnapshot


class PushEngine:
    """
    推送引擎
    
    特性:
    1. 批量发送 - 累积 10 条或 5 秒窗口后发送
    2. 失败重试 - 指数退避重试，最多 5 次
    3. 断网容灾 - 本地缓存最多 1000 条
    """
    
    def __init__(
        self,
        endpoint: str,
        token: str,
        batch_size: int = 10,
        batch_window: int = 5,
        max_retries: int = 5,
        cache_size: int = 1000,
        cache_dir: Optional[Path] = None
    ):
        self.endpoint = endpoint
        self.token = token
        self.batch_size = batch_size
        self.batch_window = batch_window
        self.max_retries = max_retries
        
        # 内存缓冲区
        self.buffer: deque = deque(maxlen=cache_size)
        
        # 本地缓存目录（断网容灾）
        self.cache_dir = cache_dir or Path("/tmp/oc-monitor-cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # HTTP 客户端
        self.client = httpx.AsyncClient(timeout=10)
        
        # 上次发送时间
        self._last_flush = time.time()
        
        # 重试计数
        self._retry_count = 0
    
    async def push(self, metric: MetricSnapshot):
        """
        推送指标
        
        1. 添加到缓冲区
        2. 达到批量大小或时间窗口时发送
        """
        self.buffer.append(metric)
        
        # 检查是否需要发送
        should_flush = (
            len(self.buffer) >= self.batch_size or
            time.time() - self._last_flush >= self.batch_window
        )
        
        if should_flush:
            await self._flush()
    
    async def _flush(self):
        """批量发送"""
        if not self.buffer:
            return
        
        # 取出数据
        batch = list(self.buffer)
        self.buffer.clear()
        
        # 尝试发送
        success = await self._send_batch(batch)
        
        if success:
            self._last_flush = time.time()
            self._retry_count = 0
        else:
            # 失败：放回缓冲区
            self.buffer.extendleft(batch)
            await self._save_to_cache(batch)  # 同时保存到本地
    
    async def _send_batch(self, batch: List[MetricSnapshot]) -> bool:
        """发送批量数据"""
        try:
            response = await self.client.post(
                f"{self.endpoint}/api/v1/metrics/batch",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                json={
                    "metrics": [m.to_dict() for m in batch]
                }
            )
            
            if response.status_code == 200:
                print(f"✅ 发送成功: {len(batch)} 条指标")
                return True
            else:
                print(f"❌ 发送失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 发送异常: {e}")
            return False
    
    async def _save_to_cache(self, batch: List[MetricSnapshot]):
        """保存到本地缓存（断网容灾）"""
        cache_file = self.cache_dir / f"metrics_{int(time.time())}.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump([m.to_dict() for m in batch], f)
            print(f"💾 已缓存: {cache_file}")
        except Exception as e:
            print(f"❌ 缓存失败: {e}")
    
    async def retry_with_backoff(self):
        """指数退避重试"""
        if self._retry_count >= self.max_retries:
            print("⚠️ 达到最大重试次数，停止重试")
            return
        
        wait_time = min(2 ** self._retry_count, 60)  # 最大 60 秒
        self._retry_count += 1
        
        print(f"⏳ 第 {self._retry_count} 次重试，等待 {wait_time} 秒...")
        await asyncio.sleep(wait_time)
        
        await self._flush()
    
    async def flush_cached_data(self):
        """
        发送缓存数据
        
        网络恢复后调用
        """
        cache_files = list(self.cache_dir.glob("metrics_*.json"))
        
        if not cache_files:
            return
        
        print(f"📤 发现 {len(cache_files)} 个缓存文件")
        
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                # 转换为 MetricSnapshot
                batch = [MetricSnapshot(**m) for m in data]
                
                # 发送
                success = await self._send_batch(batch)
                
                if success:
                    cache_file.unlink()  # 删除缓存文件
                    print(f"🗑️ 已删除缓存: {cache_file.name}")
                else:
                    break  # 发送失败，停止处理后续文件
                    
            except Exception as e:
                print(f"❌ 处理缓存失败 {cache_file.name}: {e}")
    
    async def close(self):
        """关闭连接"""
        await self.client.aclose()


# 测试代码
if __name__ == "__main__":
    async def test():
        # 模拟推送
        pusher = PushEngine(
            endpoint="http://localhost:8000",
            token="test-token"
        )
        
        print("测试推送引擎...")
        
        # 模拟 20 条数据
        for i in range(20):
            metric = MetricSnapshot(
                cpu=50 + i,
                memory=60 + i,
                disk=70 + i,
                gateway_status=True,
                timestamp=time.time()
            )
            
            await pusher.push(metric)
            print(f"[{i+1}] 已推送")
            await asyncio.sleep(0.5)
        
        await pusher.close()
    
    asyncio.run(test())
