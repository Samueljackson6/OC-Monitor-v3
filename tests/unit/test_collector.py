"""
OC-Monitor v3.0 - 单元测试
测试目标: 采集器核心功能
"""
import pytest
import asyncio
import time
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent"))

from collector import LightweightCollector, AdaptiveScheduler, MetricSnapshot


class TestLightweightCollector:
    """轻量级采集器测试"""
    
    @pytest.mark.asyncio
    async def test_collect_non_blocking(self):
        """测试采集是非阻塞的（< 100ms）"""
        collector = LightweightCollector()
        
        start = time.time()
        snapshot = await collector.collect()
        elapsed = (time.time() - start) * 1000  # ms
        
        # 非阻塞采集应在 100ms 内完成
        assert elapsed < 100, f"采集耗时 {elapsed:.2f}ms，超过 100ms"
        
        # 验证数据范围
        assert 0 <= snapshot.cpu <= 100, f"CPU 值 {snapshot.cpu} 不在 0-100 范围内"
        assert 0 <= snapshot.memory <= 100, f"内存值 {snapshot.memory} 不在 0-100 范围内"
        assert 0 <= snapshot.disk <= 100, f"磁盘值 {snapshot.disk} 不在 0-100 范围内"
        assert isinstance(snapshot.gateway_status, bool)
    
    @pytest.mark.asyncio
    async def test_gateway_check_cached(self):
        """测试 Gateway 检查有缓存"""
        collector = LightweightCollector(gateway_check_ttl=5)
        
        # 第一次检查
        start1 = time.time()
        result1 = await collector._check_gateway_cached()
        elapsed1 = (time.time() - start1) * 1000
        
        # 第二次检查（应使用缓存）
        start2 = time.time()
        result2 = await collector._check_gateway_cached()
        elapsed2 = (time.time() - start2) * 1000
        
        # 缓存检查应立即返回（< 10ms）
        assert elapsed2 < 10, f"缓存检查耗时 {elapsed2:.2f}ms，超过 10ms"
        
        # 结果应一致
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_gateway_port_check(self):
        """测试 Gateway 端口检查"""
        collector = LightweightCollector(gateway_port=18789)
        
        # 直接调用端口检查
        result = collector._check_gateway_port()
        
        # 结果应为布尔值
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_multiple_collects(self):
        """测试多次采集稳定性"""
        collector = LightweightCollector()
        
        # 连续采集 100 次
        for i in range(100):
            snapshot = await collector.collect()
            assert snapshot is not None
        
        print("✅ 100 次采集全部成功")
    
    @pytest.mark.asyncio
    async def test_snapshot_to_dict(self):
        """测试快照序列化"""
        collector = LightweightCollector()
        snapshot = await collector.collect()
        
        data = snapshot.to_dict()
        
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data
        assert "gateway_status" in data
        assert "timestamp" in data


class TestAdaptiveScheduler:
    """自适应调度器测试"""
    
    @pytest.mark.asyncio
    async def test_adjust_interval_high_load(self):
        """测试高负载时降低间隔"""
        collector = LightweightCollector()
        scheduler = AdaptiveScheduler(collector)
        
        # 模拟高 CPU 负载
        snapshot = MetricSnapshot(
            cpu=85.0,
            memory=50.0,
            disk=50.0,
            gateway_status=True,
            timestamp=time.time()
        )
        
        scheduler._adjust_interval(snapshot)
        
        assert scheduler.get_interval() == 5, "高负载时间隔应为 5 秒"
    
    @pytest.mark.asyncio
    async def test_adjust_interval_medium_load(self):
        """测试中等负载时使用正常间隔"""
        collector = LightweightCollector()
        scheduler = AdaptiveScheduler(collector)
        
        # 模拟中等 CPU 负载
        snapshot = MetricSnapshot(
            cpu=65.0,
            memory=50.0,
            disk=50.0,
            gateway_status=True,
            timestamp=time.time()
        )
        
        scheduler._adjust_interval(snapshot)
        
        assert scheduler.get_interval() == 30, "中等负载时间隔应为 30 秒"
    
    @pytest.mark.asyncio
    async def test_adjust_interval_low_load(self):
        """测试低负载时使用最大间隔"""
        collector = LightweightCollector()
        scheduler = AdaptiveScheduler(collector)
        
        # 模拟低 CPU 负载
        snapshot = MetricSnapshot(
            cpu=30.0,
            memory=50.0,
            disk=50.0,
            gateway_status=True,
            timestamp=time.time()
        )
        
        scheduler._adjust_interval(snapshot)
        
        assert scheduler.get_interval() == 60, "低负载时间隔应为 60 秒"
    
    def test_scheduler_interval_adjustment(self):
        """测试调度器间隔调整逻辑"""
        collector = LightweightCollector()
        scheduler = AdaptiveScheduler(collector)
        
        # 测试高负载
        scheduler._adjust_interval(MetricSnapshot(
            cpu=85.0, memory=50.0, disk=50.0,
            gateway_status=True, timestamp=time.time()
        ))
        assert scheduler.get_interval() == 5
        
        # 测试中等负载
        scheduler._adjust_interval(MetricSnapshot(
            cpu=65.0, memory=50.0, disk=50.0,
            gateway_status=True, timestamp=time.time()
        ))
        assert scheduler.get_interval() == 30
        
        # 测试低负载
        scheduler._adjust_interval(MetricSnapshot(
            cpu=30.0, memory=50.0, disk=50.0,
            gateway_status=True, timestamp=time.time()
        ))
        assert scheduler.get_interval() == 60
        
        print("✅ 调度器间隔调整逻辑正确")


class TestMetricSnapshot:
    """指标快照测试"""
    
    def test_snapshot_creation(self):
        """测试快照创建"""
        snapshot = MetricSnapshot(
            cpu=50.0,
            memory=60.0,
            disk=70.0,
            gateway_status=True,
            timestamp=1234567890.0
        )
        
        assert snapshot.cpu == 50.0
        assert snapshot.memory == 60.0
        assert snapshot.disk == 70.0
        assert snapshot.gateway_status is True
        assert snapshot.timestamp == 1234567890.0
    
    def test_snapshot_to_dict(self):
        """测试快照序列化"""
        snapshot = MetricSnapshot(
            cpu=50.0,
            memory=60.0,
            disk=70.0,
            gateway_status=True,
            timestamp=1234567890.0
        )
        
        data = snapshot.to_dict()
        
        assert data == {
            "cpu": 50.0,
            "memory": 60.0,
            "disk": 70.0,
            "gateway_status": True,
            "timestamp": 1234567890.0
        }


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
