# OC-Monitor v3.0 - 部署文档

## 部署方式

### 方式一：本地开发环境

```bash
# 启动服务
./deploy/start-local.sh

# 验证服务
./deploy/verify.sh

# 停止服务
./deploy/stop-local.sh
```

### 方式二：Docker Compose

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 方式三：生产环境部署

```bash
# 运行部署脚本
sudo ./deploy/install.sh

# 启动服务
sudo systemctl start oc-monitor-api
sudo systemctl start oc-monitor-collector

# 查看状态
sudo systemctl status oc-monitor-api

# 验证部署
sudo ./deploy/verify.sh
```

## 生产环境配置

### 1. 数据库配置

```bash
# PostgreSQL
sudo -u postgres psql
CREATE USER ocmonitor WITH PASSWORD 'your-password';
CREATE DATABASE ocmonitor OWNER ocmonitor;
GRANT ALL PRIVILEGES ON DATABASE ocmonitor TO ocmonitor;
```

### 2. 环境变量

编辑 `deploy/.env.production`：

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://ocmonitor:password@localhost:5432/ocmonitor

# JWT 密钥（使用 openssl rand -hex 32 生成）
SECRET_KEY=your-secret-key-here

# 管理员账户
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_PASSWORD=your-password
```

### 3. Nginx 配置

```bash
# 复制配置
sudo cp deploy/nginx.conf /etc/nginx/sites-available/oc-monitor
sudo ln -s /etc/nginx/sites-available/oc-monitor /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

### 4. HTTPS 配置（推荐）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

## 监控与日志

### 日志位置

- API 日志: `/var/log/oc-monitor/api.log`
- 采集器日志: `/var/log/oc-monitor/collector.log`
- Nginx 日志: `/var/log/nginx/oc-monitor-*.log`

### 查看日志

```bash
# API 日志
sudo journalctl -u oc-monitor-api -f

# 采集器日志
sudo journalctl -u oc-monitor-collector -f

# Nginx 日志
sudo tail -f /var/log/nginx/oc-monitor-access.log
```

### 监控自身

访问监控界面：
- http://your-server-ip

API 文档：
- http://your-server-ip/docs

## 性能调优

### API Workers

编辑 systemd 服务：
```bash
sudo systemctl edit oc-monitor-api
```

添加：
```ini
[Service]
ExecStart=
ExecStart=/opt/oc-monitor/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 8
```

### 数据库连接池

编辑 `.env.production`：
```bash
DATABASE_URL=postgresql+asyncpg://ocmonitor:password@localhost:5432/ocmonitor?min_size=10&max_size=20
```

### Nginx 缓存

编辑 `nginx.conf`：
```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=100m inactive=60m;

location /api/v1/metrics/history {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    # ...
}
```

## 故障排查

### 服务无法启动

```bash
# 检查端口占用
sudo netstat -tlnp | grep 8000

# 检查日志
sudo journalctl -u oc-monitor-api -n 50

# 检查权限
ls -la /opt/oc-monitor
ls -la /var/log/oc-monitor
```

### 数据库连接失败

```bash
# 测试连接
psql -U ocmonitor -d ocmonitor -h localhost

# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 查看日志
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### 内存占用高

```bash
# 查看进程内存
ps aux | grep -E "uvicorn|collector"

# 重启服务
sudo systemctl restart oc-monitor-api
sudo systemctl restart oc-monitor-collector
```

## 备份与恢复

### 数据库备份

```bash
# 备份
pg_dump -U ocmonitor ocmonitor > backup_$(date +%Y%m%d).sql

# 恢复
psql -U ocmonitor ocmonitor < backup_20260505.sql
```

### 配置备份

```bash
# 备份配置
tar -czf oc-monitor-config-$(date +%Y%m%d).tar.gz \
  /opt/oc-monitor/deploy/.env.production \
  /etc/nginx/sites-available/oc-monitor \
  /etc/systemd/system/oc-monitor-*.service
```

## 升级

```bash
# 1. 备份数据
pg_dump -U ocmonitor ocmonitor > backup_before_upgrade.sql

# 2. 停止服务
sudo systemctl stop oc-monitor-api oc-monitor-collector

# 3. 更新代码
cd /opt/oc-monitor
git pull

# 4. 更新依赖
source venv/bin/activate
pip install -e ".[dev]"
cd api && pip install -r requirements.txt

# 5. 启动服务
sudo systemctl start oc-monitor-api oc-monitor-collector

# 6. 验证
sudo ./deploy/verify.sh
```

## 安全建议

1. **修改默认密码**: 修改管理员密码和数据库密码
2. **启用 HTTPS**: 使用 Let's Encrypt 证书
3. **防火墙配置**: 只开放必要端口
4. **定期备份**: 设置自动备份计划任务
5. **日志监控**: 设置日志告警
6. **定期更新**: 保持系统和依赖更新

## 支持

- 文档: `README.md`, `PROJECT_SUMMARY.md`
- API 文档: http://localhost:8000/docs
- 问题反馈: GitHub Issues
