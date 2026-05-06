# OC-Monitor 接管任务清单

更新时间：2026-05-06

## P0：接管前冻结

- [ ] 备份本地 `/home/samuel/.openclaw/workspace/dev_agent/oc-monitor-v3`
- [ ] 备份阿里云 `/opt/oc-monitor`
- [ ] 导出阿里云 PostgreSQL `ocmonitor` 数据库
- [ ] 记录阿里云 systemd、Nginx、PostgreSQL、Redis 当前状态
- [ ] 记录当前线上可用入口：`8000`、`8443`、`8500`、`8080`、`8081`
- [ ] 确认本地 `master` 与 GitHub `origin/master` 是否一致
- [ ] 标记当前线上版本和 Git commit

## P1：仓库救援

- [ ] 新建接管分支，例如 `rescue/repo-cleanup`
- [ ] 新增 `.gitignore`
- [ ] 从 Git 跟踪中移除 `.api.pid`
- [ ] 从 Git 跟踪中移除 `venv/`
- [ ] 从 Git 跟踪中移除 `data/monitor.db`
- [ ] 从 Git 跟踪中移除 `logs/`
- [ ] 从 Git 跟踪中移除 `__pycache__/`
- [ ] 清理本地工作区中的 `node_modules`、`dist`、日志、pid、数据库文件
- [ ] 新增 GitHub Actions：后端测试、前端构建、仓库污染检查
- [ ] 设置 PR 验收规则，禁止直接在 `master` 上补丁式开发

## P2：安全基线

- [ ] 移除硬编码 JWT Secret
- [ ] 移除内置明文账号
- [ ] 新增用户表和密码哈希
- [ ] 所有写接口加认证
- [ ] Agent、模型、配置、任务、审计接口加认证
- [ ] 敏感配置迁移到环境变量或 secrets 文件
- [ ] 轮换当前 GitHub Token，并收窄权限范围
- [ ] API 只监听 `127.0.0.1`，由 Nginx 统一对外暴露

## P3：v3 监控底座修正

- [ ] 修复 `/api/v1/agents/list` 500
- [ ] 修正 `agent_metrics` 代码模型与 PostgreSQL 表结构不一致
- [ ] 数据清理任务从 SQLite 改为 PostgreSQL
- [ ] Redis 配置从环境变量读取
- [ ] 增加 Alembic 数据库迁移
- [ ] 补齐 API/DB/Redis/collector/Nginx 健康检查
- [ ] 明确 v3 只负责 Telemetry，不承担 Openclaw 控制面
- [ ] 统一 `/etc/systemd/system` 与仓库 `deploy/` 中的服务文件
- [ ] 确认旧 `oc-webmonitor.service` 的保留或下线策略

## P4：Openclaw 控制面

- [ ] 本地 Runtime Probe 读取 `openclaw.json`
- [ ] 上报真实 Agent 列表
- [ ] 上报真实模型供应商和模型列表
- [ ] 支持 Agent 模型和思考模式配置版本化
- [ ] 支持配置应用、回执和回滚
- [ ] 增加任务统计和执行链路
