# cfmgr - Cloudflare Worker D1 & R2 管理器

[![Python](https://img.shields.io/badge/Python-3.13.7-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-77%20Passed-success.svg)](./tests/)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg)](https://github.com/psf/black)

Cloudflare Worker 项目，提供完整的 D1 数据库和 R2 对象存储管理功能，支持 RESTful API 和多数据库/多 bucket 操作。

## ✨ 特性

### D1 数据库管理
- ✅ **查询操作**: SELECT 查询、参数化查询、分页支持
- ✅ **执行操作**: INSERT、UPDATE、DELETE、DDL 语句
- ✅ **批量操作**: 事务支持、批量查询/执行
- ✅ **表管理**: 创建表、删除表、查看表结构和索引
- ✅ **数据导入导出**: JSON/CSV 格式支持
- ✅ **SQL 注入防护**: 完整的参数化查询支持

### R2 对象存储管理
- ✅ **对象操作**: 上传、下载、删除、复制
- ✅ **元数据管理**: 自定义元数据、HTTP 头控制
- ✅ **列表操作**: 前缀过滤、分页、目录结构模拟
- ✅ **分片上传**: 大文件上传支持（>5MB）
- ✅ **预签名 URL**: HMAC-SHA256 签名、时间限制
- ✅ **MD5 校验**: 数据完整性验证

### 通用特性
- 🔒 **安全**: API Key 认证、参数验证、错误处理
- 📊 **标准化响应**: 统一的 JSON 格式（success, data, meta, error）
- 🚀 **高性能**: 异步操作、连接复用
- 📝 **完整文档**: API 规范、测试报告、代码注释
- ✅ **测试覆盖**: 77 个单元测试，100% 通过率

## 📦 环境要求

### Python 环境 (pyenv)

```bash
# 安装 pyenv (如果尚未安装)
curl https://pyenv.run | bash

# 安装 Python 3.13
pyenv install 3.13

# 项目会自动使用 .python-version 指定的版本
pyenv local 3.13
```

### Node.js 环境 (nvm)

```bash
# 安装 nvm (如果尚未安装)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# 安装 Node.js 18
nvm install 18

# 项目会自动使用 .nvmrc 指定的版本
nvm use
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/tsaitang404/cfmgr.git
cd cfmgr
```

### 2. 设置环境

```bash
# 使用正确的 Python 版本
pyenv local 3.13

# 使用正确的 Node.js 版本
nvm use

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 安装 Wrangler
npm install -g wrangler

# 安装 Python 开发依赖
pip install pytest pytest-asyncio black ruff
```

### 4. 配置 Cloudflare

```bash
# 登录 Cloudflare
wrangler login

# 配置 wrangler.toml（参考示例配置）
```

### 5. 本地开发

```bash
# 启动开发服务器
wrangler dev

# 或使用 VS Code 任务
# Run Task -> Wrangler Dev
```

### 6. 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行 D1 测试
pytest tests/test_d1_manager.py -v

# 运行 R2 测试
pytest tests/test_r2_manager.py -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 7. 部署

```bash
# 部署到生产环境
wrangler deploy

# 或使用 VS Code 任务
# Run Task -> Deploy Worker
```

## 📂 项目结构

```
cfmgr/
├── .github/                # GitHub 配置
│   ├── copilot-instructions.md  # Copilot 工作指导
│   └── PROJECT.md         # 项目详细说明
├── config/                # 配置文件目录
├── docs/                  # 文档目录
│   ├── api/              # API 规范文档
│   │   ├── d1-api.md    # D1 API 规范
│   │   ├── r2-api.md    # R2 API 规范
│   │   └── README.md    # API 文档说明
│   └── database/         # 数据库文档
│       └── schema.md    # 数据库结构
├── src/                  # 源代码
│   ├── __init__.py
│   ├── config.py        # 配置管理
│   ├── d1_manager.py    # D1 数据库管理器
│   ├── r2_manager.py    # R2 对象存储管理器
│   ├── router.py        # 请求路由
│   └── index.py         # Worker 入口点
├── tests/                # 测试文件
│   ├── __init__.py
│   ├── test_d1_manager.py      # D1 测试套件（37 测试）
│   ├── test_r2_manager.py      # R2 测试套件（40 测试）
│   ├── TEST_REPORT.md          # D1 测试报告
│   └── R2_TEST_REPORT.md       # R2 测试报告
├── .python-version       # Python 版本 (3.13.7)
├── .nvmrc               # Node.js 版本
├── pyproject.toml       # Python 项目配置
├── wrangler.toml        # Wrangler 配置
├── README.md            # 本文件
└── SETUP.md             # 详细设置指南
```

## 📚 API 文档

完整的 API 规范文档位于 `docs/api/` 目录：

- **[D1 API 规范](./docs/api/d1-api.md)**: 数据库管理的所有 API 接口
- **[R2 API 规范](./docs/api/r2-api.md)**: 对象存储管理的所有 API 接口

### D1 API 示例

```bash
# 查询数据
curl "https://your-worker.workers.dev/api/v1/d1/production/query" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users WHERE age > ?", "params": [18]}'

# 执行写操作
curl "https://your-worker.workers.dev/api/v1/d1/production/execute" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"sql": "INSERT INTO users (name, email) VALUES (?, ?)", "params": ["张三", "zhangsan@example.com"]}'
```

### R2 API 示例

```bash
# 上传文件
curl -X PUT "https://your-worker.workers.dev/api/v1/r2/media/objects/photo.jpg" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: image/jpeg" \
  --data-binary @photo.jpg

# 下载文件
curl "https://your-worker.workers.dev/api/v1/r2/media/objects/photo.jpg" \
  -H "X-API-Key: your-api-key" \
  -o photo.jpg

# 列出对象
curl "https://your-worker.workers.dev/api/v1/r2/media/objects?prefix=photos/" \
  -H "X-API-Key: your-api-key"
```

## 🧪 测试报告

项目包含完整的单元测试套件，覆盖所有核心功能：

| 模块 | 测试数量 | 通过率 | 执行时间 | 报告 |
|------|---------|-------|---------|------|
| **D1 Manager** | 37 | 100% | 0.15s | [查看报告](./tests/TEST_REPORT.md) |
| **R2 Manager** | 40 | 100% | 0.37s | [查看报告](./tests/R2_TEST_REPORT.md) |
| **总计** | **77** | **100%** | **0.52s** | - |

### D1 Manager 测试覆盖
- ✅ 数据库管理（3 测试）
- ✅ 查询操作（8 测试）
- ✅ 执行操作（7 测试）
- ✅ 批量操作（4 测试）
- ✅ 表管理（6 测试）
- ✅ 数据导入导出（9 测试）

### R2 Manager 测试覆盖
- ✅ Bucket 管理（3 测试）
- ✅ 对象上传（8 测试）
- ✅ 对象下载（4 测试）
- ✅ 对象元数据（2 测试）
- ✅ 对象删除（2 测试）
- ✅ 对象复制（5 测试）
- ✅ 对象列表（6 测试）
- ✅ 分片上传（6 测试）
- ✅ 辅助方法（4 测试）

## 🛠️ 开发工具

### VS Code 任务

项目配置了以下 VS Code 任务（`Ctrl/Cmd + Shift + P` → `Run Task`）：

- **Wrangler Dev**: 启动本地开发服务器
- **Install Dependencies**: 安装 Python 依赖
- **Run Tests**: 运行所有测试
- **Format Code**: 格式化代码（Black）
- **Type Check**: 类型检查（MyPy）
- **Deploy Worker**: 部署到生产环境

### 代码质量工具

```bash
# 格式化代码
black src/ tests/

# 代码检查（自动修复）
ruff check src/ --fix

# 类型检查
mypy src/
```

### Git Pre-commit 钩子

项目已配置 Git pre-commit 钩子，会在提交前自动执行：

1. **Black 格式化**: 自动格式化代码
2. **Ruff 检查**: 自动修复代码质量问题
3. **MyPy 类型检查**: 类型检查（非阻塞）

**安装钩子**:
```bash
# 钩子已自动配置在 .git/hooks/pre-commit
# 确保有执行权限
chmod +x .git/hooks/pre-commit

# 或运行安装脚本
./scripts/install-hooks.sh
```

**使用说明**:
```bash
# 正常提交（自动运行检查）
git commit -m "your message"

# 跳过钩子检查
git commit --no-verify -m "skip checks"

# 手动运行检查
.git/hooks/pre-commit
```

**配置文件**:
- `.pre-commit-config`: Pre-commit 行为配置
- `pyproject.toml`: Black、Ruff、MyPy 工具配置

## 📋 配置示例

### wrangler.toml

```toml
name = "cfmgr"
main = "src/index.py"
compatibility_date = "2024-12-01"

[[d1_databases]]
binding = "DB"
database_name = "cfmgr_db"
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

[[r2_buckets]]
binding = "R2"
bucket_name = "cfmgr-bucket"

# 认证配置（可选）
# 开发环境：使用 vars
[vars]
API_KEY = "dev-test-key-12345"

# 生产环境：使用 secrets（推荐）
# 运行: wrangler secret put API_KEY
# 然后输入您的密钥
```

### API 认证

**认证机制说明**：

```bash
# 如果配置了 API_KEY，所有 API 端点都需要认证
# 公开路由（无需认证）：
#   GET /              - 服务信息
#   GET /health        - 健康检查
#   GET /docs          - API 文档
#   GET /docs/d1       - D1 文档
#   GET /docs/r2       - R2 文档

# 受保护路由（需要认证）：
#   POST /d1/query     - D1 查询
#   POST /d1/execute   - D1 执行
#   GET  /d1/tables    - 表列表
#   GET  /r2/list      - R2 列表
#   ... 其他所有 API 端点
```

**使用示例**：

```bash
# 不带认证（如果未配置 API_KEY）
curl http://localhost:8787/d1/tables

# 带认证（如果配置了 API_KEY）
curl http://localhost:8787/d1/tables \
  -H "X-API-Key: your-api-key-here"

# 查询数据
curl -X POST http://localhost:8787/d1/query \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users LIMIT 10"}'
```

**配置 API Key**：

```bash
# 开发环境：在 wrangler.toml 中配置
[vars]
API_KEY = "dev-test-key-12345"

# 生产环境：使用 Wrangler secrets（更安全）
wrangler secret put API_KEY
# 输入密钥: your-production-api-key

# 验证 secrets
wrangler secret list
```

### 环境变量

创建 `.env` 文件（不要提交到 Git）：

```bash
# API Keys
API_KEY=your-secret-api-key-here

# D1 Database IDs
D1_DATABASE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# R2 Bucket Names
R2_BUCKET_NAME=cfmgr-bucket
```

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

### 代码规范

- Python 代码遵循 PEP 8
- 使用 Black 格式化
- 所有函数需要类型注解和 docstring
- 新功能必须包含测试

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🔗 相关链接

- [Cloudflare Workers 文档](https://developers.cloudflare.com/workers/)
- [D1 数据库文档](https://developers.cloudflare.com/d1/)
- [R2 存储文档](https://developers.cloudflare.com/r2/)
- [Wrangler CLI 文档](https://developers.cloudflare.com/workers/wrangler/)

## 📞 联系方式

- **项目主页**: https://github.com/tsaitang404/cfmgr
- **问题反馈**: https://github.com/tsaitang404/cfmgr/issues

---

**开发状态**: ✅ 生产就绪  
**最后更新**: 2025年12月9日  
**维护者**: [@tsaitang404](https://github.com/tsaitang404)
