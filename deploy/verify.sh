#!/bin/bash
# OC-Monitor v3.0 验证脚本

echo "=== OC-Monitor v3.0 部署验证 ==="
echo ""

# 测试 API
echo "[1/2] 测试 API..."
if curl -sf http://localhost:8000/api/v1/metrics/health > /dev/null 2>&1; then
    echo "✅ API 健康检查通过"
else
    echo "❌ API 健康检查失败"
fi

# 测试 API 文档
echo ""
echo "[2/2] 测试 API 文档..."
if curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✅ API 文档可访问"
else
    echo "❌ API 文档不可访问"
fi

echo ""
echo "=== 验证完成 ==="
