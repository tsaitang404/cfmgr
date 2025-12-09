# cfmgr - Cloudflare R2 & D1 对外服务接口

## 项目概述

为 Cloudflare R2 对象存储和 D1 数据库提供标准化的对外操作接口。通过 Cloudflare Workers 运行时，提供类似 MinIO 的对象存储 API 和完整的数据库操作接口，支持多 bucket/database 管理和独立的权限认证。

**核心特性**：
- 🗄️ 多 R2 Bucket 管理 - 用户可指定操作的 bucket
- 🗃️ 多 D1 Database 管理 - 用户可指定操作的 database
- 🔐 独立权限认证系统 - 使用 D1/R2 自身进行权限验证
- 🌐 公网访问支持 - R2 对象可通过公网 URL 访问
- 📦 S3 兼容 API - R2 接口兼容 S3 协议（参考 MinIO）

## 功能需求

### R2 对象存储接口

提供类似 MinIO 的对象存储服务，支持 S3 兼容 API。

#### Bucket 管理
- `GET /api/v1/r2/buckets` - 列出所有可访问的 buckets
- `GET /api/v1/r2/buckets/:bucket` - 获取 bucket 信息
- `HEAD /api/v1/r2/buckets/:bucket` - 检查 bucket 是否存在

#### 对象操作（需指定 bucket）
- `GET /api/v1/r2/:bucket/objects/:key` - 下载对象
  - 支持 Range 请求（断点续传）
  - 自动识别 Content-Type
  - 支持预签名 URL（临时访问）
- `PUT /api/v1/r2/:bucket/objects/:key` - 上传对象
  - 支持分片上传
  - 自动 MD5/SHA256 校验
  - 支持自定义元数据
- `DELETE /api/v1/r2/:bucket/objects/:key` - 删除对象
- `HEAD /api/v1/r2/:bucket/objects/:key` - 获取对象元数据
- `POST /api/v1/r2/:bucket/objects/:key/copy` - 复制对象

#### 对象列表（需指定 bucket）
- `GET /api/v1/r2/:bucket/objects` - 列出对象
  - 支持前缀过滤（prefix）
  - 支持分隔符（delimiter）模拟目录结构
  - 支持分页（cursor-based）
  - 返回对象元数据和 URL

#### 公网访问
- `GET /public/:bucket/:key` - 公网访问对象
  - 可配置的访问控制
  - 支持 CDN 缓存头
  - 可选的防盗链
- `GET /api/v1/r2/:bucket/objects/:key/url` - 生成预签名 URL
  - 可设置过期时间
  - 支持下载和上传 URL

#### 多部分上传
- `POST /api/v1/r2/:bucket/objects/:key/multipart` - 初始化分片上传
- `PUT /api/v1/r2/:bucket/objects/:key/multipart/:uploadId/:partNumber` - 上传分片
- `POST /api/v1/r2/:bucket/objects/:key/multipart/:uploadId/complete` - 完成上传
- `DELETE /api/v1/r2/:bucket/objects/:key/multipart/:uploadId` - 取消上传

### D1 数据库接口

提供完整的数据库操作接口，支持多数据库管理。

#### Database 管理
- `GET /api/v1/d1/databases` - 列出所有可访问的 databases
- `GET /api/v1/d1/databases/:database` - 获取 database 信息
- `GET /api/v1/d1/databases/:database/stats` - 获取数据库统计信息

#### 查询操作（需指定 database）
- `POST /api/v1/d1/:database/query` - 执行 SELECT 查询
  - 支持参数化查询（防 SQL 注入）
  - 返回 JSON 格式结果
  - 支持分页（limit/offset）
  - 查询超时控制

#### 执行操作（需指定 database）
- `POST /api/v1/d1/:database/execute` - 执行写操作
  - INSERT/UPDATE/DELETE
  - 支持事务处理
  - 返回影响的行数
  - 自动回滚失败操作

#### 批量操作（需指定 database）
- `POST /api/v1/d1/:database/batch` - 批量执行 SQL
  - 单个事务中执行多条语句
  - 原子性保证（全部成功或全部失败）
  - 支持参数化查询

#### 表管理（需指定 database）
- `GET /api/v1/d1/:database/tables` - 列出所有表
- `POST /api/v1/d1/:database/tables` - 创建新表
- `GET /api/v1/d1/:database/tables/:name` - 获取表结构
- `GET /api/v1/d1/:database/tables/:name/indexes` - 获取表索引
- `DELETE /api/v1/d1/:database/tables/:name` - 删除表

#### 数据导入导出（需指定 database）
- `POST /api/v1/d1/:database/export` - 导出数据（SQL/CSV/JSON）
- `POST /api/v1/d1/:database/import` - 导入数据

### 权限认证系统

使用 D1 数据库存储权限信息，R2 存储认证相关配置。

#### 认证方式
- **API Key 认证**（Header: `X-API-Key`）
  - 存储在 D1 的 `api_keys` 表
  - 支持多个 API Key
  - 可设置过期时间
- **预签名 URL**（Query: `signature`）
  - 基于 HMAC-SHA256
  - 可配置有效期
  - 用于临时访问

#### 权限模型
```json
{
  "api_key": "ak_xxxxx",
  "permissions": {
    "r2": {
      "buckets": ["bucket1", "bucket2"],
      "operations": ["read", "write", "delete"]
    },
    "d1": {
      "databases": ["db1", "db2"],
      "operations": ["query", "execute", "admin"]
    }
  }
}
```

#### 权限级别
**R2 权限**：
- `read` - 读取对象（GET, HEAD, LIST）
- `write` - 写入对象（PUT, POST）
- `delete` - 删除对象（DELETE）
- `admin` - 管理 bucket（所有操作）

**D1 权限**：
- `query` - 执行查询（SELECT）
- `execute` - 执行写操作（INSERT, UPDATE, DELETE）
- `admin` - 管理数据库（CREATE TABLE, DROP TABLE, ALTER）

#### 认证存储
- **D1 表**: `auth_api_keys` - 存储 API Key 和权限
- **D1 表**: `auth_sessions` - 存储会话信息
- **R2 对象**: `auth/config.json` - 存储全局配置

### 通用功能

#### 错误处理
- 统一的错误响应格式
- 详细的错误消息和错误码
- 适当的 HTTP 状态码
- 错误日志记录

#### 速率限制
- 基于 API Key 的限流
- 可配置的限流规则
- 限流信息存储在 D1

#### 访问日志
- 请求/响应日志存储在 D1
- 可选的详细日志（包含请求体）
- 日志查询和导出接口

#### CORS 支持
- 可配置的 CORS 规则
- 支持预检请求（OPTIONS）
- 存储在 R2 的配置文件

## 技术栈

- **运行时**: Cloudflare Workers Python 3.11+
- **数据库**: Cloudflare D1 (SQLite)
- **存储**: Cloudflare R2 (S3-compatible)
- **工具链**: Wrangler CLI
- **认证**: D1 存储 + HMAC 签名

## 核心文件结构

```
cfmgr/
├── src/
│   ├── index.py              # Worker 入口点
│   ├── router.py             # 路由分发
│   ├── middleware/
│   │   ├── auth.py           # 认证中间件
│   │   ├── rate_limit.py     # 限流中间件
│   │   └── cors.py           # CORS 中间件
│   ├── handlers/
│   │   ├── r2_handler.py     # R2 请求处理
│   │   ├── d1_handler.py     # D1 请求处理
│   │   └── public_handler.py # 公网访问处理
│   ├── managers/
│   │   ├── r2_manager.py     # R2 操作管理
│   │   ├── d1_manager.py     # D1 操作管理
│   │   ├── auth_manager.py   # 权限管理
│   │   └── bucket_manager.py # Bucket/Database 管理
│   ├── models/
│   │   ├── response.py       # 响应模型
│   │   ├── error.py          # 错误模型
│   │   └── permission.py     # 权限模型
│   └── utils/
│       ├── signature.py      # 签名工具
│       ├── validator.py      # 输入验证
│       └── logger.py         # 日志工具
├── migrations/
│   ├── 001_init_auth.sql     # 初始化认证表
│   └── 002_init_logs.sql     # 初始化日志表
├── tests/
│   ├── test_r2_handler.py
│   ├── test_d1_handler.py
│   ├── test_auth.py
│   └── test_permissions.py
├── wrangler.toml             # Wrangler 配置
├── pyproject.toml            # Python 项目配置
└── requirements.txt          # Python 依赖（如果需要）
```

## API 响应格式

### 成功响应
```json
{
  "success": true,
  "data": {
    // 实际数据
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00.000Z",
    "duration_ms": 42,
    "request_id": "req_xxxxx"
  }
}
```

### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "BUCKET_NOT_FOUND",
    "message": "指定的 bucket 不存在或无权限访问",
    "details": {
      "bucket": "my-bucket"
    }
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00.000Z",
    "request_id": "req_xxxxx"
  }
}
```

### 对象列表响应（R2）
```json
{
  "success": true,
  "data": {
    "objects": [
      {
        "key": "photos/image.jpg",
        "size": 204800,
        "etag": "d41d8cd98f00b204e9800998ecf8427e",
        "last_modified": "2024-01-01T00:00:00.000Z",
        "content_type": "image/jpeg",
        "url": "https://worker.dev/public/my-bucket/photos/image.jpg"
      }
    ],
    "truncated": false,
    "cursor": null,
    "common_prefixes": ["photos/", "documents/"]
  },
  "meta": {
    "bucket": "my-bucket",
    "prefix": "",
    "count": 1
  }
}
```

## 实现计划

### 阶段 1: 基础架构和认证 (Week 1)
- [x] 项目初始化和环境配置
- [ ] 路由系统实现（支持多 bucket/database 路径参数）
- [ ] D1 认证表初始化（migrations）
- [ ] API Key 认证中间件
- [ ] 权限验证系统
- [ ] 基础错误处理和日志

### 阶段 2: R2 接口实现 (Week 2)
- [ ] Bucket 管理接口
- [ ] 对象基础操作（GET, PUT, DELETE, HEAD）
- [ ] 对象列表和过滤
- [ ] 公网访问接口
- [ ] 预签名 URL 生成
- [ ] 分片上传支持
- [ ] 单元测试

### 阶段 3: D1 接口实现 (Week 3)
- [ ] Database 管理接口
- [ ] 查询接口（参数化查询）
- [ ] 执行接口（事务支持）
- [ ] 批量操作接口
- [ ] 表管理接口
- [ ] 数据导入导出
- [ ] 单元测试

### 阶段 4: 高级功能 (Week 4)
- [ ] 速率限制实现
- [ ] CORS 配置
- [ ] 访问日志系统
- [ ] 性能优化
- [ ] 安全加固
- [ ] 集成测试
- [ ] 文档完善

### 阶段 5: 生产部署 (Week 5)
- [ ] 配置管理优化
- [ ] 监控和告警
- [ ] 备份策略
- [ ] 负载测试
- [ ] 生产环境部署
- [ ] 用户文档和 API 参考

## Wrangler 配置示例

```toml
name = "cfmgr"
main = "src/index.py"
compatibility_date = "2024-01-01"

# R2 Bucket 绑定（支持多个）
[[r2_buckets]]
binding = "BUCKET_1"
bucket_name = "my-bucket-1"

[[r2_buckets]]
binding = "BUCKET_2"
bucket_name = "my-bucket-2"

# D1 Database 绑定（支持多个）
[[d1_databases]]
binding = "DB_1"
database_name = "my-db-1"
database_id = "xxxx-xxxx-xxxx"

[[d1_databases]]
binding = "DB_AUTH"
database_name = "cfmgr-auth"
database_id = "yyyy-yyyy-yyyy"

# 环境变量
[vars]
ENVIRONMENT = "production"
LOG_LEVEL = "info"
```

## 性能目标

- **R2 操作**:
  - 小文件（< 1MB）上传/下载: < 100ms
  - 大文件分片上传: 支持 TB 级
  - 列表操作: < 200ms（1000 个对象）

- **D1 操作**:
  - 简单查询: < 50ms
  - 复杂查询: < 200ms
  - 批量操作: < 500ms（100 条语句）

- **并发能力**:
  - 并发请求: > 1000 req/s
  - 可用性: 99.9%

## 安全要求

### 认证和授权
- 所有 API 必须经过认证（除公网访问接口）
- 基于 API Key 的细粒度权限控制
- 支持 API Key 轮换和过期
- 预签名 URL 防篡改

### 输入验证
- SQL 参数化查询（防注入）
- 对象键名验证（防路径穿越）
- 请求体大小限制
- Content-Type 验证

### 数据保护
- API Key 哈希存储（SHA-256）
- 敏感日志脱敏
- HTTPS 强制
- CORS 白名单

### 速率限制
- 基于 API Key 的限流
- 基于 IP 的限流（可选）
- 渐进式响应延迟

## 监控指标

### R2 指标
- 上传/下载流量
- 对象存储量
- 操作成功率
- 平均响应时间
- 错误率（按类型）

### D1 指标
- 查询执行时间
- 数据库大小
- 活跃连接数
- 慢查询日志
- 错误率（按类型）

### 认证指标
- API Key 使用统计
- 认证失败率
- 权限拒绝统计
- 异常访问模式

## MinIO 兼容性

参考 MinIO S3 API 实现，提供兼容的接口：

- **标准 S3 操作**: GET/PUT/DELETE Object
- **Bucket 操作**: ListObjects, HeadBucket
- **分片上传**: CreateMultipartUpload, UploadPart, CompleteMultipartUpload
- **预签名 URL**: PresignedGetObject, PresignedPutObject
- **元数据**: 自定义 HTTP 头（x-amz-meta-*）

可使用 AWS SDK 或 MinIO 客户端访问（需适配认证方式）。
