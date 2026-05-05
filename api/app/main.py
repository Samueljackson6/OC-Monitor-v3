"""
OC-Monitor v3.0 - FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.config import settings
from app.database import init_db
from app.api.metrics import router as metrics_router

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    # 启动时
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    
    # 初始化数据库
    await init_db()
    logger.info("✅ 数据库初始化完成")
    
    # 创建数据目录
    data_dir = Path("./data")
    data_dir.mkdir(exist_ok=True)
    
    logger.info(f"🌐 API 前缀: /{settings.API_PREFIX}")
    logger.info(f"✅ {settings.APP_NAME} 启动完成")
    
    yield
    
    # 关闭时
    logger.info(f"👋 {settings.APP_NAME} 关闭中...")


# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## OC-Monitor v3.0 API

轻量级、高性能的 OpenClaw 监控系统 API

### 功能模块
- 📊 **指标接收**: 接收采集端推送的监控数据
- 📈 **实时数据**: 获取最新监控数据
- 📉 **历史趋势**: 获取历史数据趋势

### 采集端接入
```bash
POST /api/v1/metrics/batch
{
  "metrics": [
    {"cpu": 50.0, "memory": 60.0, "disk": 70.0, "gateway_status": true, "timestamp": 1234567890.0}
  ]
}
```
""",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(metrics_router, prefix=f"/{settings.API_PREFIX}")


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": f"/{settings.API_PREFIX}"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
