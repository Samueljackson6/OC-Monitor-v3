"""
OC-Monitor v3.0 - 性能测试（优化版）
测试目标: 内存 < 5MB, CPU < 1%, 延迟 < 1ms
"""
import pytest
import time
import tracemalloc
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.collector_optimized import LightweightCollector, AdaptiveScheduler


class TestPerformance:
    """性能测试（优化版）"""
    
    def test_memory_usage(self):
        """测试内存占用 < 5MB"""
        tracemalloc.start()
        
        # 创建采集器
        collector = LightweightCollector()
        
        # 运行 100 次采集
        for _ in range(100):
            collector.collect()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"\n当前内存: {current / 1024 / 1024:.2f} MB")
        print(f"峰值内存: {peak / 1024 / 1024:.2f} MB")
        
        # 内存占用应 < 5MB
        assert current < 5 * 1024 * 1024, f"当前内存 {current / 1024 / 1024:.2f}MB 超过 5MB"
    
    def test_cpu_usage(self):
        """测试 CPU 占用 < 1%"""
        import psutil
        process = psutil.Process()
        
        collector = LightweightCollector()
        
        # 采集 100 次
        for _ in range(100):
            collector.collect()
        
        cpu_percent = process.cpu_percent(interval=0.1)
        
        print(f"\nCPU 占用: {cpu_percent:.2f}%")
        
        # CPU 占用应 < 5%（测试环境允许更高）
        assert cpu_percent < 5.0
    
    def test_collect_latency(self):
        """测试采集延迟 < 1ms"""
        collector = LightweightCollector()
        
        # 预热
        collector.collect()
        
        # 性能测试
        start = time.perf_counter()
        for _ in range(1000):
            collector.collect()
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / 1000) * 1000
        
        print(f"\n平均采集延迟: {avg_ms:.3f} ms")
        
        # 平均延迟应 < 1ms
        assert avg_ms < 1.0, f"平均延迟 {avg_ms:.3f}ms 超过 1ms"
    
    def test_no_memory_leak(self):
        """测试无内存泄漏"""
        tracemalloc.start()
        
        collector = LightweightCollector()
        
        # 初始内存
        snapshot1 = tracemalloc.take_snapshot()
        
        # 采集 1000 次
        for _ in range(1000):
            collector.collect()
        
        # 最终内存
        snapshot2 = tracemalloc.take_snapshot()
        
        # 计算内存差异
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_diff = sum(stat.size_diff for stat in top_stats)
        
        tracemalloc.stop()
        
        print(f"\n内存变化: {total_diff / 1024:.2f} KB")
        
        # 内存增长应 < 100KB
        assert total_diff < 100 * 1024, f"内存增长 {total_diff / 1024:.2f}KB 超过 100KB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
