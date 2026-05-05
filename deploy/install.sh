#!/bin/bash
# OC-Monitor v3.0 部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="/opt/oc-monitor"

echo -e "${GREEN}=== OC-Monitor v3.0 部署脚本 ===${NC}"
echo ""

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 1. 安装依赖
echo -e "${YELLOW}[1/6] 安装系统依赖...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib

# 2. 创建部署目录
echo -e "${YELLOW}[2/6] 创建部署目录...${NC}"
mkdir -p $DEPLOY_DIR
mkdir -p /var/log/oc-monitor
mkdir -p /var/lib/oc-monitor

# 3. 复制项目文件
echo -e "${YELLOW}[3/6] 复制项目文件...${NC}"
cp -r $PROJECT_ROOT/agent $DEPLOY_DIR/
cp -r $PROJECT_ROOT/api $DEPLOY_DIR/
cp -r $PROJECT_ROOT/ui $DEPLOY_DIR/
cp $PROJECT_ROOT/pyproject.toml $DEPLOY_DIR/
cp $PROJECT_ROOT/README.md $DEPLOY_DIR/

# 4. 配置 Python 环境
echo -e "${YELLOW}[4/6] 配置 Python 环境...${NC}"
cd $DEPLOY_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
cd api && pip install -r requirements.txt

# 5. 配置数据库
echo -e "${YELLOW}[5/6] 配置 PostgreSQL 数据库...${NC}"
sudo -u postgres psql -c "CREATE USER ocmonitor WITH PASSWORD 'password';" || true
sudo -u postgres psql -c "CREATE DATABASE ocmonitor OWNER ocmonitor;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ocmonitor TO ocmonitor;" || true

# 6. 安装 Systemd 服务
echo -e "${YELLOW}[6/6] 安装 Systemd 服务...${NC}"
cp $PROJECT_ROOT/deploy/oc-monitor-api.service /etc/systemd/system/
cp $PROJECT_ROOT/deploy/oc-monitor-collector.service /etc/systemd/system/

systemctl daemon-reload
systemctl enable oc-monitor-api
systemctl enable oc-monitor-collector

# 7. 配置 Nginx
echo -e "${YELLOW}[7/6] 配置 Nginx...${NC}"
cp $PROJECT_ROOT/deploy/nginx.conf /etc/nginx/sites-available/oc-monitor
ln -sf /etc/nginx/sites-available/oc-monitor /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 8. 设置权限
echo -e "${YELLOW}[8/6] 设置权限...${NC}"
chown -R www-data:www-data $DEPLOY_DIR
chown -R www-data:www-data /var/log/oc-monitor
chown -R www-data:www-data /var/lib/oc-monitor
chmod 600 $DEPLOY_DIR/deploy/.env.production

echo ""
echo -e "${GREEN}=== 部署完成 ===${NC}"
echo ""
echo "启动服务:"
echo "  sudo systemctl start oc-monitor-api"
echo "  sudo systemctl start oc-monitor-collector"
echo ""
echo "查看状态:"
echo "  sudo systemctl status oc-monitor-api"
echo "  sudo systemctl status oc-monitor-collector"
echo ""
echo "访问地址:"
echo "  http://your-server-ip"
echo ""
echo "API 文档:"
echo "  http://your-server-ip/api/docs"
