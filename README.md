# Cloudflare Worker - D1 & R2 Manager

一个用 Python 编写的 Cloudflare Worker，用于管理 D1 数据库和 R2 对象存储。

## 功能特性

- ✅ D1 数据库查询和执行操作
- ✅ R2 对象存储上传、下载、删除和列表功能
- ✅ RESTful API 路由处理
- ✅ 错误处理和日志
- ✅ 配置管理
- ✅ 异步操作支持

## 项目结构

```
cfmgr/
├── src/
│   ├── __init__.py           # 包初始化
│   ├── index.py              # Worker 入口点
│   ├── config.py             # 配置管理
│   ├── d1_manager.py         # D1 数据库管理
│   ├── r2_manager.py         # R2 存储管理
│   └── router.py             # 请求路由
├── tests/                    # 测试文件
├── config/                   # 配置文件
├── wrangler.toml            # Wrangler 配置
├── pyproject.toml           # Python 项目配置
├── .env.example             # 环境变量示例
└── README.md                # 本文件
```

## 快速开始

### 前置条件

- Python 3.11+
- `uv` 包管理工具
- Node.js 18+（用于 wrangler CLI）
- Cloudflare 账户

### 安装

1. 安装 `uv`（如果还未安装）：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. 初始化项目（使用 pywrangler）：

```bash
uv init
uv tool install workers-py
```

3. 登录 Cloudflare：

```bash
uv run pywrangler login
```

4. 创建 D1 数据库（如果还未创建）：

```bash
uv run pywrangler d1 create cfmgr_db
```

5. 更新 `wrangler.toml` 中的 `database_id`

### 配置

创建 `.env` 文件（基于 `.env.example`）：

```bash
cp .env.example .env
```

编辑 `.env` 并填入您的配置：

```
ENVIRONMENT=development
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_ACCOUNT_ID=your_account_id
```

### API 端点

#### 健康检查

```bash
curl http://localhost:8787/health
```

#### D1 数据库操作

```bash
# 列表所有表
curl http://localhost:8787/api/d1/tables
```

#### R2 存储操作

```bash
# 列表所有对象
curl http://localhost:8787/api/r2/objects
```

## 开发

### 运行本地开发服务器

```bash
uv run pywrangler dev
```

### 运行测试

```bash
uv run pytest
```

### 代码格式化

```bash
uv run black src/
```

### 类型检查

```bash
uv run mypy src/
```

## 部署

```bash
uv run pywrangler deploy
```

## 使用示例

### D1 数据库操作

```python
from src.d1_manager import D1Manager

# 假设 db 是通过 Worker 环境注入的
manager = D1Manager(db)

# 查询
result = await manager.query("SELECT * FROM users WHERE id = ?", [1])

# 执行写操作
result = await manager.execute("INSERT INTO users (name) VALUES (?)", ["John"])

# 创建表
result = await manager.create_table(
    "users",
    "id INTEGER PRIMARY KEY, name TEXT NOT NULL"
)
```

### R2 存储操作

```python
from src.r2_manager import R2Manager

# 假设 r2_bucket 是通过 Worker 环境注入的
manager = R2Manager(r2_bucket)

# 上传文件
result = await manager.upload("path/to/file.txt", b"content", "text/plain")

# 下载文件
result = await manager.download("path/to/file.txt")

# 删除文件
result = await manager.delete("path/to/file.txt")

# 列表对象
result = await manager.list_objects(prefix="uploads/", limit=50)
```

## 环境变量

| 变量名 | 说明 | 必需 |
|------|------|------|
| `ENVIRONMENT` | 环境类型 (development/production) | 否 |
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token | 是 |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare 账户 ID | 是 |

## 许可证

MIT
