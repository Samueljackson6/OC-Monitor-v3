"""
OC-Monitor v3.0 - 轻量级采集器
设计目标: 非阻塞、低资源占用、自适应频率
"""
import asyncio
import time
import socket
import psutil
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path
import json


@dataclass
class MetricSnapshot:
    """轻量级指标快照"""
    cpu: float
    memory: float
    disk: float
    gateway_status: bool
    timestamp: float
    
    def to_dict(self) -> dict:
        return asdict(self)


class LightweightCollector:
    """
    轻量级采集器 - 非阻塞设计
    
    关键设计:
    1. 使用 psutil.cpu_percent(interval=None) 非阻塞模式
    2. Gateway 检查使用端口探测而非进程遍历
    3. 缓存 Gateway 状态避免重复检查
    """
    
    def __init__(self, gateway_port: int = 18789, gateway_check_ttl: int = 30):
        self.gateway_port = gateway_port
        self.gateway_check_ttl = gateway_check_ttl
        
        # Gateway 状态缓存
        self._gateway_running: bool = False
        self._last_gateway_check: float = 0
        
        # 初始化 CPU 采集（第一次调用返回 0.0，需要预热）
        psutil.cpu_percent(interval=None)
    
    async def collect(self) -> MetricSnapshot:
        """
        非阻塞采集
        
        性能目标:
        - 采集时间 < 100ms
        - 不阻塞事件循环
        """
        # CPU - 非阻塞模式（返回上次调用以来的平均值）
        cpu = psutil.cpu_percent(interval=None)
        
        # 内存 - 快速读取
        memory = psutil.virtual_memory().percent
        
        # 磁盘 - 快速读取
        disk = psutil.disk_usage('/').percent
        
        # Gateway 状态 - 带缓存
        gateway_status = await self._check_gateway_cached()
        
        return MetricSnapshot(
            cpu=cpu,
            memory=memory,
            disk=disk,
            gateway_status=gateway_status,
            timestamp=time.time()
        )
    
    async def _check_gateway_cached(self) -> bool:
        """
        带缓存的 Gateway 检查
        
        避免频繁的端口探测
        """
        now = time.time()
        
        # 缓存未过期
        if now - self._last_gateway_check < self.gateway_check_ttl:
            return self._gateway_running
        
        # 检查并更新缓存
        self._gateway_running = self._check_gateway_port()
        self._last_gateway_check = now
        
        return self._gateway_running
    
    def _check_gateway_port(self) -> bool:
        """
        快速端口探测
        
        比 psutil.process_iter() 快 100 倍
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', self.gateway_port))
            sock.close()
            return result == 0
        except Exception:
            return False


class AdaptiveScheduler:
    """
    自适应调度器
    
    根据系统负载动态调整采集频率:
    - CPU < 50%: 60 秒间隔（省资源）
    - CPU 50-80%: 30 秒间隔（正常）
    - CPU > 80%: 5 秒间隔（告警模式，快速响应）
    """
    
    def __init__(self, collector: LightweightCollector):
        self.collector = collector
        self.interval = 60  # 默认 60 秒
        
        # 采集频率范围
        self.min_interval = 5   # 高负载时
        self.normal_interval = 30  # 中负载时
        self.max_interval = 60  # 低负载时
        
        # 阈值
        self.high_load_threshold = 80
        self.medium_load_threshold = 50
    
    async def run(self, callback=None):
        """
        主循环
        
        Args:
            callback: 可选的回调函数，接收 MetricSnapshot
        """
        while True:
            # 采集数据
            snapshot = await self.collector.collect()
            
            # 调用回调
            if callback:
                await callback(snapshot)
            
            # 自适应调整间隔
            self._adjust_interval(snapshot)
            
            # 等待
            await asyncio.sleep(self.interval)
    
    def _adjust_interval(self, snapshot: MetricSnapshot):
        """根据 CPU 负载调整采集间隔"""
        if snapshot.cpu > self.high_load_threshold:
            self.interval = self.min_interval
        elif snapshot.cpu > self.medium_load_threshold:
            self.interval = self.normal_interval
        else:
            self.interval = self.max_interval
    
    def get_interval(self) -> int:
        """获取当前间隔"""
        return self.interval


# 测试代码
if __name__ == "__main__":
    async def test():
        collector = LightweightCollector()
        scheduler = AdaptiveScheduler(collector)
        
        print("测试采集器...")
        
        # 测试 10 次
        for i in range(10):
            start = time.time()
            snapshot = await collector.collect()
            elapsed = (time.time() - start) * 1000  # ms
            
            print(f"[{i+1}] CPU: {snapshot.cpu:.1f}%, "
                  f"内存: {snapshot.memory:.1f}%, "
                  f"磁盘: {snapshot.disk:.1f}%, "
                  f"Gateway: {snapshot.gateway_status}, "
                  f"耗时: {elapsed:.2f}ms, "
                  f"间隔: {scheduler.get_interval()}s")
            
            scheduler._adjust_interval(snapshot)
            await asyncio.sleep(1)
    
    asyncio.run(test())
