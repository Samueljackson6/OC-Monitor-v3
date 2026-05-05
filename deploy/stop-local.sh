#!/bin/bash
# OC-Monitor v3.0 停止脚本

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== 停止 OC-Monitor 服务 ==="

# 读取 PID
if [ -f "$PROJECT_ROOT/.api.pid" ]; then
    API_PID=$(cat $PROJECT_ROOT/.api.pid)
    kill $API_PID 2>/dev/null && echo "API 服务已停止 (PID: $API_PID)" || echo "API 服务未运行"
    rm $PROJECT_ROOT/.api.pid
fi

echo "完成"
