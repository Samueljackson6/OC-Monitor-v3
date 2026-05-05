#!/bin/bash
# OC-Monitor v3.0 本地快速启动脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== OC-Monitor v3.0 本地启动 ==="
echo ""

# 检查虚拟环境
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "创建虚拟环境..."
    cd $PROJECT_ROOT
    python3 -m venv venv
    source venv/bin/activate
    pip install -e ".[dev]"
    cd api && pip install -r requirements.txt
else
    source $PROJECT_ROOT/venv/bin/activate
fi

# 创建数据和日志目录
mkdir -p $PROJECT_ROOT/data
mkdir -p $PROJECT_ROOT/logs

# 启动 API 服务（后台）
echo "启动 API 服务..."
cd $PROJECT_ROOT/api
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > ../logs/api.log 2>&1 &
API_PID=$!
echo "API 服务已启动 (PID: $API_PID)"

# 等待 API 启动
sleep 2

echo ""
echo "=== 启动完成 ==="
echo ""
echo "API 地址: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "日志位置:"
echo "  API: $PROJECT_ROOT/logs/api.log"
echo ""
echo "停止服务:"
echo "  kill $API_PID"
echo ""

# 保存 PID
echo "$API_PID" > $PROJECT_ROOT/.api.pid
