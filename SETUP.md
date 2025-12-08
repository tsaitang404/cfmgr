# Cloudflare Worker Python 项目设置指南

这是一个完全基于 Python 的 Cloudflare Worker 项目，用于管理 D1 数据库和 R2 对象存储。

## 项目架构

### 核心技术栈
- **语言**：Python 3.11+
- **运行环境**：Cloudflare Workers（Python Workers 支持）
- **包管理器**：`uv`（推荐）或 `pip`
- **CLI 工具**：`pywrangler`（Python Workers 专用 CLI）

### 项目结构

```
cfmgr/
├── src/
│   ├── __init__.py              # 包初始化
│   ├── index.py                 # Worker 入口点 (Default 类)
│   ├── config.py                # 配置管理 (Pydantic BaseModel)
│   ├── d1_manager.py            # D1 数据库管理
│   ├── r2_manager.py            # R2 存储管理
│   └── router.py                # HTTP 请求路由
├── tests/                       # 测试文件
├── wrangler.toml               # Wrangler 配置（包含 python_workers 标志）
├── pyproject.toml              # Python 项目配置（uv + hatchling）
├── .env.example                # 环境变量示例
└── README.md                   # 项目文档
```

## 关键配置说明

### 1. `wrangler.toml`

```toml
type = "python"
compatibility_date = "2024-12-08"
compatibility_flags = ["python_workers"]  # 必须！启用 Python Workers Beta
main = "src/index.py"                     # Python 入口点
```

### 2. `pyproject.toml`

- 使用 `hatchling` 作为构建后端（轻量级，适合 Workers）
- 核心依赖：
  - `workers-py>=1.0.0` - Cloudflare Workers Python SDK
  - `pydantic>=2.0.0` - 配置和数据验证
  - `httpx` - HTTP 客户端（可选）

### 3. Worker 入口点

```python
from workers import WorkerEntrypoint, Response

class Default(WorkerEntrypoint):
    async def fetch(self, request) -> Response:
        # 处理请求
        pass
```

**重要**：必须使用 `WorkerEntrypoint` 类，而不是函数式 API。

### 4. 绑定（Bindings）

在 `wrangler.toml` 中配置的绑定会自动注入到 Worker 环境中：

```toml
[[d1_databases]]
binding = "DB"
database_name = "cfmgr_db"
database_id = "YOUR_ID"

[[r2_buckets]]
binding = "R2"
bucket_name = "cfmgr-bucket"
```

## 开发工作流

### 第 1 步：环境设置

```bash
# 安装 uv（推荐）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 初始化项目
cd cfmgr
uv init
uv tool install workers-py
```

### 第 2 步：创建 D1 数据库

```bash
# 创建 D1 数据库
uv run pywrangler d1 create cfmgr_db

# 输出会显示 database_id，复制到 wrangler.toml
```

### 第 3 步：配置环境变量

```bash
cp .env.example .env
# 编辑 .env 并填入配置
```

### 第 4 步：本地开发

```bash
# 启动本地开发服务器
uv run pywrangler dev

# 会在 http://localhost:8787 启动
```

### 第 5 步：测试

```bash
# 测试健康检查
curl http://localhost:8787/health

# 测试 D1 路由
curl http://localhost:8787/api/d1/tables

# 测试 R2 路由
curl http://localhost:8787/api/r2/objects
```

### 第 6 步：部署

```bash
uv run pywrangler deploy
```

## 依赖管理

### 使用 `uv`（推荐）

```bash
# 添加依赖
uv add requests

# 移除依赖
uv remove requests

# 安装所有依赖
uv sync
```

### 使用 `pip`

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -e ".[dev]"
```

## 支持的 Python 标准库

Cloudflare Workers Python 支持大部分标准库，但有些模块不可用：

- ✅ `json`, `re`, `datetime`, `asyncio`
- ❌ `socket`, `ssl`, `subprocess`, `threading`（受限）

详见：https://developers.cloudflare.com/workers/languages/python/stdlib/

## FFI 和绑定

通过 FFI（Foreign Function Interface），可以直接使用 JavaScript 对象：

```python
from js import fetch, Response as JSResponse
import json

# 使用 JavaScript fetch
result = await fetch("https://api.example.com")
```

详见：https://developers.cloudflare.com/workers/languages/python/ffi/

## 常见问题

**Q: 为什么需要 `python_workers` 兼容性标志？**
A: 这是因为 Python Workers 仍处于 Beta 阶段，需要显式启用。

**Q: 可以使用 FastAPI 吗？**
A: 可以！`workers-py` 支持 FastAPI：
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello"}

# 在 wrangler.toml 中配置 main = "main:app"
```

**Q: 性能如何？**
A: Python Workers 使用 Pyodide（WASM 中的 Python），冷启动约 100-200ms，速度接近 JavaScript Workers。

## 资源

- 官方文档：https://developers.cloudflare.com/workers/languages/python/
- 示例代码：https://github.com/cloudflare/python-workers-examples
- Discord 社区：https://discord.cloudflare.com/

## 下一步

1. ✅ 项目已完全 Python 化
2. 📋 根据需要添加更多 API 路由
3. 🔗 实现 D1 和 R2 的实际业务逻辑
4. 🧪 编写单元测试
5. 🚀 部署到 Cloudflare
