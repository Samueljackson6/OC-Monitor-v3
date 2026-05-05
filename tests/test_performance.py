"""
OC-Monitor v3.0 - 性能测试
测试目标: 内存 < 50MB, CPU < 1%
"""
import pytest
import asyncio
import time
import psutil
import sys
from pathlib import Path

# 添加项目路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "agent"))

from collector import LightweightCollector, AdaptiveScheduler


class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """测试内存占用 < 50MB"""
        process = psutil.Process()
        
        # 初始内存
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # 创建采集器
        collector = LightweightCollector()
        
        # 运行 60 次采集（模拟 1 分钟）
        for _ in range(60):
            await collector.collect()
        
        # 最终内存
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        print(f"\n初始内存: {initial_memory:.2f} MB")
        print(f"最终内存: {final_memory:.2f} MB")
        print(f"内存增长: {memory_growth:.2f} MB")
        
        # 内存增长应 < 10MB
        assert memory_growth < 10, f"内存增长 {memory_growth:.2f}MB 超过 10MB"
        
        # 总内存应 < 50MB
        assert final_memory < 50, f"总内存 {final_memory:.2f}MB 超过 50MB"
    
    @pytest.mark.asyncio
    async def test_cpu_usage(self):
        """测试 CPU 占用 < 1%"""
        process = psutil.Process()
        
        # 创建采集器
        collector = LightweightCollector()
        
        # 预热
        for _ in range(5):
            await collector.collect()
        
        # 重置 CPU 统计
        process.cpu_percent(interval=None)
        
        # 运行 30 秒
        start_time = time.time()
        collect_count = 0
        
        while time.time() - start_time < 30:
            await collector.collect()
            collect_count += 1
            await asyncio.sleep(1)
        
        # 获取 CPU 占用
        cpu_percent = process.cpu_percent(interval=1)
        
        print(f"\n采集次数: {collect_count}")
        print(f"CPU 占用: {cpu_percent:.2f}%")
        
        assert cpu_percent < 1, f"CPU 占用 {cpu_percent:.2f}% 超过 1%"
    
    @pytest.mark.asyncio
    async def test_collect_latency(self):
        """测试采集延迟 < 100ms"""
        collector = LightweightCollector()
        
        # 预热
        await collector.collect()
        
        # 测试 100 次采集延迟
        latencies = []
        
        for _ in range(100):
            start = time.time()
            await collector.collect()
            elapsed = (time.time() - start) * 1000  # ms
            latencies.append(elapsed)
        
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        print(f"\n采集延迟统计:")
        print(f"  平均: {avg_latency:.2f} ms")
        print(f"  最大: {max_latency:.2f} ms")
        print(f"  最小: {min_latency:.2f} ms")
        
        # 平均延迟应 < 10ms
        assert avg_latency < 10, f"平均延迟 {avg_latency:.2f}ms 超过 10ms"
        
        # 最大延迟应 < 100ms
        assert max_latency < 100, f"最大延迟 {max_latency:.2f}ms 超过 100ms"
    
    @pytest.mark.asyncio
    async def test_no_memory_leak(self):
        """测试无内存泄漏（运行 5 分钟）"""
        process = psutil.Process()
        
        # 创建采集器
        collector = LightweightCollector()
        
        # 记录内存增长
        memory_samples = []
        
        # 运行 300 次（模拟 5 分钟，加速测试）
        for i in range(300):
            await collector.collect()
            
            # 每 50 次采样一次
            if i % 50 == 0:
                memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory)
        
        print(f"\n内存采样:")
        for i, mem in enumerate(memory_samples):
            print(f"  {i*50} 次: {mem:.2f} MB")
        
        # 计算内存增长趋势
        if len(memory_samples) >= 2:
            growth_rate = (memory_samples[-1] - memory_samples[0]) / len(memory_samples)
            print(f"  增长率: {growth_rate:.4f} MB/采样")
            
            # 增长率应接近 0
            assert growth_rate < 0.1, f"内存增长率 {growth_rate:.4f} MB/采样，可能存在泄漏"


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__, "-v", "-s", "--tb=short"])
