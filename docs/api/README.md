# cfmgr REST API 规范

## 概述

cfmgr 为 Cloudflare R2 对象存储和 D1 数据库提供标准化的 RESTful API 接口，支持多 bucket/database 管理、公网访问和细粒度权限控制。

**Base URL**: `https://cfmgr.workers.dev`

**API 版本**: v1

**认证方式**: 
- API Key (Header: `X-API-Key`)
- 预签名 URL (Query: `signature`)

## 快速开始

### 设置环境变量

```bash
# 设置 API Key
export API_KEY="your-api-key"
export BASE_URL="https://cfmgr.workers.dev"
```

### D1 数据库操作

```bash
# 列出所有可访问的数据库
curl "$BASE_URL/api/v1/d1/databases" \
  -H "X-API-Key: $API_KEY"

# 查询指定数据库
curl -X POST "$BASE_URL/api/v1/d1/production-db/query" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM users WHERE status = ?status LIMIT 10",
    "params": {"status": "active"}
  }'

# 执行写操作
curl -X POST "$BASE_URL/api/v1/d1/production-db/execute" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "INSERT INTO users (name, email) VALUES (?name, ?email)",
    "params": {"name": "张三", "email": "zhangsan@example.com"}
  }'
```

### R2 对象存储操作

```bash
# 列出所有可访问的 buckets
curl "$BASE_URL/api/v1/r2/buckets" \
  -H "X-API-Key: $API_KEY"

# 上传文件到指定 bucket
curl -X PUT "$BASE_URL/api/v1/r2/media-storage/objects/images/photo.jpg" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: image/jpeg" \
  --data-binary @photo.jpg

# 下载文件
curl "$BASE_URL/api/v1/r2/media-storage/objects/images/photo.jpg" \
  -H "X-API-Key: $API_KEY" \
  -o photo.jpg

# 列出 bucket 中的对象
curl "$BASE_URL/api/v1/r2/media-storage/objects?prefix=images/&limit=50" \
  -H "X-API-Key: $API_KEY"
```

### 公网访问（无需认证）

```bash
# 直接访问公开的 R2 对象
curl "$BASE_URL/public/media-storage/images/photo.jpg" \
  -o photo.jpg

# 或在浏览器中直接访问
# https://cfmgr.workers.dev/public/media-storage/images/photo.jpg
```

## API 模块

### 核心 API
- [D1 数据库 API](./d1-api.md) - 多数据库管理、查询、执行和表操作
- [R2 对象存储 API](./r2-api.md) - 多 bucket 管理、对象操作和公网访问
- [认证 API](./authentication.md) - API 认证、权限管理和预签名 URL
- [错误处理](./errors.md) - 错误代码、处理和最佳实践

### 功能特性
- **多资源支持**: 用户可指定操作的 bucket 或 database
- **细粒度权限**: 基于 API Key 的资源级权限控制
- **公网访问**: R2 对象支持无认证的公网 URL
- **预签名 URL**: 生成临时访问链接
- **分片上传**: 支持大文件的分片上传（类似 S3 Multipart）
- **MinIO 兼容**: R2 API 参考 MinIO/S3 设计

## 通用规范

### 请求头

| Header | 必需 | 说明 |
|--------|------|------|
| `X-API-Key` | 是* | API 认证密钥（公网访问和预签名 URL 除外） |
| `Content-Type` | 视情况 | 请求体类型，如 `application/json`、`image/jpeg` |
| `Accept` | 否 | 响应类型，默认 `application/json` |
| `Range` | 否 | 部分内容请求（R2 下载），如 `bytes=0-1023` |
| `Content-MD5` | 否 | MD5 校验和（R2 上传） |
| `X-Custom-Metadata-*` | 否 | 自定义元数据（R2 上传） |

### URL 结构

#### D1 数据库 API
```
/api/v1/d1/databases                      # 列出所有数据库
/api/v1/d1/databases/:database           # 获取数据库信息
/api/v1/d1/:database/query               # 查询数据
/api/v1/d1/:database/execute             # 执行写操作
/api/v1/d1/:database/batch               # 批量操作
/api/v1/d1/:database/tables              # 表管理
```

#### R2 对象存储 API
```
/api/v1/r2/buckets                       # 列出所有 buckets
/api/v1/r2/buckets/:bucket               # 获取 bucket 信息
/api/v1/r2/:bucket/objects               # 列出对象
/api/v1/r2/:bucket/objects/:key          # 对象操作（GET/PUT/DELETE）
/api/v1/r2/:bucket/objects/:key/copy     # 复制对象
/api/v1/r2/:bucket/objects/:key/presigned-url  # 生成预签名 URL
/api/v1/r2/:bucket/objects/:key/multipart      # 分片上传
```

#### 公网访问
```
/public/:bucket/:key                     # 公网访问 R2 对象
```

### 响应格式

#### 成功响应

```json
{
  "success": true,
  "data": {
    // 实际数据
  },
  "meta": {
    "timestamp": "2024-01-20T10:00:00.000Z",
    "duration_ms": 42,
    "request_id": "req_abc123"
  }
}
```

#### 列表响应（带分页）

```json
{
  "success": true,
  "data": {
    "items": [...],
    "truncated": false,
    "cursor": null
  },
  "meta": {
    "count": 10,
    "timestamp": "2024-01-20T10:00:00.000Z"
  }
}
```

#### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "DATABASE_NOT_FOUND",
    "message": "数据库 'production-db' 不存在或无权限访问",
    "details": {
      "database": "production-db"
    }
  },
  "meta": {
    "timestamp": "2024-01-20T10:00:00.000Z",
    "request_id": "req_abc123"
  }
}
```

### HTTP 状态码

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 200 | 成功 | GET、POST 请求成功 |
| 201 | 创建成功 | 资源创建（如创建表） |
| 204 | 成功，无内容 | DELETE 成功 |
| 206 | 部分内容 | Range 请求（R2 断点续传） |
| 304 | 未修改 | 条件请求缓存命中 |
| 400 | 请求错误 | 参数错误、SQL 语法错误等 |
| 401 | 未授权 | API Key 缺失或无效 |
| 403 | 禁止访问 | 权限不足 |
| 404 | 资源不存在 | Database/Bucket/Object 不存在 |
| 408 | 请求超时 | 查询超时 |
| 409 | 资源冲突 | 唯一键冲突、资源已存在 |
| 413 | 请求实体过大 | 文件超过大小限制 |
| 429 | 请求过多 | 超出速率限制 |
| 500 | 服务器错误 | 内部错误 |
| 503 | 服务不可用 | 服务暂时不可用 |

### 分页

使用 cursor-based 分页（适用于大数据集）:

**请求参数**:
- `limit`: 每页数量（默认 100，最大 1000）
- `cursor`: 分页游标（从上次响应的 `cursor` 字段获取）

**响应示例**:
```json
{
  "success": true,
  "data": {
    "objects": [...],
    "truncated": true,
    "cursor": "eyJrZXkiOiJpbWFnZXMvcGhvdG81MC5qcGcifQ"
  },
  "meta": {
    "count": 100
  }
}
```

**分页请求**:
```bash
# 第一页
curl "$BASE_URL/api/v1/r2/media-storage/objects?limit=100"

# 下一页
curl "$BASE_URL/api/v1/r2/media-storage/objects?limit=100&cursor=eyJrZXkiOi..."
```

### 速率限制

基于 API Key 的速率限制:

- **默认限制**: 1000 请求/分钟
- **可配置**: 不同 API Key 可设置不同限制
- **超出处理**: 返回 429 状态码

**响应头**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1705751234
```

**超出限制响应**:
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "超出速率限制，请稍后重试",
    "details": {
      "limit": 1000,
      "reset_at": "2024-01-20T10:01:00.000Z"
    }
  }
}
```

## 权限系统

### 权限级别

#### D1 权限
- `query` - 查询权限（SELECT）
- `execute` - 执行权限（INSERT, UPDATE, DELETE）
- `admin` - 管理权限（CREATE TABLE, DROP TABLE, ALTER）

#### R2 权限
- `read` - 读取权限（GET, HEAD, LIST）
- `write` - 写入权限（PUT, POST）
- `delete` - 删除权限（DELETE）
- `admin` - 管理权限（所有操作）

### 权限检查

每个请求都会验证：
1. API Key 是否有效
2. API Key 是否有访问指定资源（bucket/database）的权限
3. API Key 是否有执行该操作的权限级别

### 权限不足响应

```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "当前 API Key 没有 bucket 'media-storage' 的写入权限",
    "details": {
      "bucket": "media-storage",
      "required_permission": "write",
      "current_permissions": ["read"]
    }
  }
}
```

## 版本控制

API 使用 URL 路径版本控制：

- **当前版本**: `/api/v1/`
- **版本策略**: 
  - 新增功能：不影响现有 API，直接添加
  - 不兼容变更：发布新版本（如 `/api/v2/`）
  - 旧版本保留至少 6 个月
  - 提前 3 个月通知废弃

## 最佳实践

### 1. 错误处理

```javascript
async function apiRequest(url, options) {
  try {
    const response = await fetch(url, options);
    const data = await response.json();
    
    if (!data.success) {
      // 根据错误代码处理
      switch (data.error.code) {
        case 'DATABASE_NOT_FOUND':
          console.error('数据库不存在');
          break;
        case 'PERMISSION_DENIED':
          console.error('权限不足');
          break;
        case 'RATE_LIMIT_EXCEEDED':
          // 等待后重试
          await sleep(60000);
          return apiRequest(url, options);
        default:
          console.error('未知错误:', data.error.message);
      }
    }
    
    return data;
  } catch (error) {
    console.error('网络错误:', error);
    throw error;
  }
}
```

### 2. 使用参数化查询

```bash
# ✅ 推荐：参数化查询（防 SQL 注入）
curl -X POST "$BASE_URL/api/v1/d1/production-db/query" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM users WHERE email = ?email",
    "params": {"email": "user@example.com"}
  }'

# ❌ 不推荐：拼接 SQL（安全风险）
curl -X POST "$BASE_URL/api/v1/d1/production-db/query" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"sql\": \"SELECT * FROM users WHERE email = 'user@example.com'\"
  }"
```

### 3. 大文件使用分片上传

```bash
# ✅ 大于 100 MB 使用分片上传
# 支持断点续传、并发上传、更可靠

# ❌ 避免直接上传超大文件
# 可能超时或失败
```

### 4. 使用预签名 URL 分享文件

```bash
# ✅ 生成临时 URL（安全）
curl -X POST "$BASE_URL/api/v1/r2/media-storage/objects/photo.jpg/presigned-url" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"expires_in": 3600}'

# 获得临时 URL，可安全分享
# https://cfmgr.workers.dev/api/v1/r2/media-storage/objects/photo.jpg?signature=...

# ❌ 不要直接分享 API Key
```

### 5. 监控速率限制

```bash
# 检查响应头
curl -I "$BASE_URL/api/v1/d1/databases" \
  -H "X-API-Key: $API_KEY"

# X-RateLimit-Remaining: 900
# 如果接近 0，需要减缓请求频率
```

## 变更日志

### v1.0.0 (2024-01-20)
- ✨ 初始版本发布
- ✨ 多 D1 数据库管理 API
- ✨ 多 R2 Bucket 管理 API
- ✨ 公网访问支持
- ✨ 预签名 URL
- ✨ 分片上传
- ✨ 细粒度权限控制
- ✨ MinIO/S3 兼容 API

## 相关资源

- [D1 API 详细文档](./d1-api.md)
- [R2 API 详细文档](./r2-api.md)
- [认证和授权](./authentication.md)
- [错误代码参考](./errors.md)
- [项目 GitHub](https://github.com/your-org/cfmgr)
- [Cloudflare Workers 文档](https://developers.cloudflare.com/workers/)
- [Cloudflare D1 文档](https://developers.cloudflare.com/d1/)
- [Cloudflare R2 文档](https://developers.cloudflare.com/r2/)

## 支持

如有问题或建议，请：
- 查看 [FAQ](./faq.md)
- 提交 [Issue](https://github.com/your-org/cfmgr/issues)
- 发送邮件至: support@example.com
