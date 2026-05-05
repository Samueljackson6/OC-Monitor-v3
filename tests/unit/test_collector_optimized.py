"""
OC-Monitor v3.0 - 优化版采集器测试
"""
import pytest
import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.collector_optimized import LightweightCollector, AdaptiveScheduler, MetricSnapshot


class TestOptimizedCollector:
    """优化版采集器测试"""
    
    def test_singleton(self):
        """测试单例模式"""
        collector1 = LightweightCollector()
        collector2 = LightweightCollector()
        
        assert collector1 is collector2
    
    def test_collect_non_blocking(self):
        """测试非阻塞采集"""
        collector = LightweightCollector()
        
        start = time.perf_counter()
        snapshot = collector.collect()
        elapsed = time.perf_counter() - start
        
        assert elapsed < 0.1  # < 100ms
        assert 0 <= snapshot.cpu <= 100
        assert 0 <= snapshot.memory <= 100
        assert 0 <= snapshot.disk <= 100
        assert isinstance(snapshot.gateway_status, bool)
    
    def test_snapshot_to_dict(self):
        """测试快照转字典"""
        snapshot = MetricSnapshot(
            cpu=50.0,
            memory=60.0,
            disk=70.0,
            gateway_status=True,
            timestamp=time.time()
        )
        
        data = snapshot.to_dict()
        
        assert data['cpu'] == 50.0
        assert data['memory'] == 60.0
        assert data['disk'] == 70.0
        assert data['gateway_status'] == True
    
    def test_memory_usage(self):
        """测试内存占用（优化后）"""
        tracemalloc.start()
        
        collector = LightweightCollector()
        
        # 采集 100 次
        for _ in range(100):
            collector.collect()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 验证内存占用 < 5MB（优化目标）
        assert current < 5 * 1024 * 1024, f"当前内存 {current / 1024 / 1024:.2f}MB 超过 5MB"
        print(f"\n当前内存: {current / 1024 / 1024:.2f} MB")
        print(f"峰值内存: {peak / 1024 / 1024:.2f} MB")
    
    def test_collect_speed(self):
        """测试采集速度"""
        collector = LightweightCollector()
        
        # 预热
        collector.collect()
        
        # 性能测试
        start = time.perf_counter()
        for _ in range(1000):
            collector.collect()
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / 1000) * 1000
        
        # 验证平均延迟 < 1ms
        assert avg_ms < 1.0, f"平均延迟 {avg_ms:.3f}ms 超过 1ms"
        print(f"\n平均采集延迟: {avg_ms:.3f} ms")


class TestAdaptiveScheduler:
    """自适应调度器测试"""
    
    def test_adjust_interval_high_load(self):
        """测试高负载调整"""
        scheduler = AdaptiveScheduler(min_interval=5.0, max_interval=60.0)
        
        interval = scheduler.adjust(cpu=85.0)
        
        assert interval == 5.0
    
    def test_adjust_interval_medium_load(self):
        """测试中等负载调整"""
        scheduler = AdaptiveScheduler(min_interval=5.0, max_interval=60.0)
        
        interval = scheduler.adjust(cpu=65.0)
        
        assert 5.0 < interval < 60.0
    
    def test_adjust_interval_low_load(self):
        """测试低负载调整"""
        scheduler = AdaptiveScheduler(min_interval=5.0, max_interval=60.0)
        
        interval = scheduler.adjust(cpu=30.0)
        
        assert interval == 60.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
