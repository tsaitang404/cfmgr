# R2 对象存储 API

管理 Cloudflare R2 对象存储的 RESTful API，提供类似 MinIO 的 S3 兼容接口，支持多 bucket 操作和公网访问。

## 基础信息

**Base URL**: `/api/v1/r2`

**认证方式**: 
- API Key (Header: `X-API-Key`)
- 预签名 URL (Query: `signature`)

**权限级别**:
- `read` - 读取对象（GET, HEAD, LIST）
- `write` - 写入对象（PUT, POST）
- `delete` - 删除对象（DELETE）
- `admin` - 管理 bucket（所有操作）

---

## 目录

- [Bucket 管理](#bucket-管理)
- [对象操作](#对象操作)
- [对象列表](#对象列表)
- [公网访问](#公网访问)
- [预签名 URL](#预签名-url)
- [分片上传](#分片上传)
- [错误代码](#错误代码)

---

## Bucket 管理

### 列出所有 Buckets

列出当前 API Key 有权限访问的所有 buckets。

**请求**

```http
GET /api/v1/r2/buckets
```

**权限**: 任意（仅返回有权限的 buckets）

**响应**

```json
{
  "success": true,
  "data": {
    "buckets": [
      {
        "name": "media-storage",
        "id": "bucket_xxxxxx",
        "region": "auto",
        "created_at": "2024-01-01T00:00:00.000Z",
        "object_count": 1250,
        "size_bytes": 524288000,
        "size_human": "500 MB",
        "permissions": ["read", "write", "delete"]
      },
      {
        "name": "backup-data",
        "id": "bucket_yyyyyy",
        "region": "auto",
        "created_at": "2024-01-15T00:00:00.000Z",
        "object_count": 85,
        "size_bytes": 10737418240,
        "size_human": "10 GB",
        "permissions": ["read"]
      }
    ]
  },
  "meta": {
    "count": 2,
    "timestamp": "2024-01-20T10:00:00.000Z"
  }
}
```

**示例**

```bash
curl "https://your-worker.workers.dev/api/v1/r2/buckets" \
  -H "X-API-Key: your-api-key"
```

---

### 获取 Bucket 信息

获取指定 bucket 的详细信息。

**请求**

```http
GET /api/v1/r2/buckets/:bucket
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |

**权限**: 任意（至少需要对该 bucket 的读权限）

**响应**

```json
{
  "success": true,
  "data": {
    "name": "media-storage",
    "id": "bucket_xxxxxx",
    "region": "auto",
    "created_at": "2024-01-01T00:00:00.000Z",
    "object_count": 1250,
    "size_bytes": 524288000,
    "size_human": "500 MB",
    "permissions": ["read", "write", "delete"],
    "cors_enabled": true,
    "public_access": false
  }
}
```

**示例**

```bash
curl "https://your-worker.workers.dev/api/v1/r2/buckets/media-storage" \
  -H "X-API-Key: your-api-key"
```

---

### 检查 Bucket 是否存在

检查指定 bucket 是否存在且有权限访问。

**请求**

```http
HEAD /api/v1/r2/buckets/:bucket
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |

**权限**: 任意

**响应**

```http
HTTP/1.1 200 OK
X-Bucket-Object-Count: 1250
X-Bucket-Size-Bytes: 524288000
X-Bucket-Region: auto
```

**示例**

```bash
curl -I "https://your-worker.workers.dev/api/v1/r2/buckets/media-storage" \
  -H "X-API-Key: your-api-key"
```

---

## 对象操作

### 下载对象

下载指定 bucket 中的对象。

**请求**

```http
GET /api/v1/r2/:bucket/objects/:key
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键（可包含 `/` 路径分隔符） |

**请求头**

| Header | 说明 |
|--------|------|
| `Range` | 部分内容请求（如 `bytes=0-1023`），支持断点续传 |
| `If-None-Match` | 条件请求（ETag），304 缓存 |
| `If-Modified-Since` | 条件请求（时间），304 缓存 |

**权限**: `read` 或更高

**响应**

```http
HTTP/1.1 200 OK
Content-Type: image/jpeg
Content-Length: 204800
ETag: "d41d8cd98f00b204e9800998ecf8427e"
Last-Modified: Mon, 01 Jan 2024 00:00:00 GMT
Cache-Control: public, max-age=3600
X-Custom-Metadata-User-Id: 123
X-Custom-Metadata-Description: 示例图片

[二进制数据]
```

**部分内容响应（Range）**

```http
HTTP/1.1 206 Partial Content
Content-Type: image/jpeg
Content-Length: 1024
Content-Range: bytes 0-1023/204800
ETag: "d41d8cd98f00b204e9800998ecf8427e"

[部分二进制数据]
```

**示例**

```bash
# 下载完整文件
curl "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo1.jpg" \
  -H "X-API-Key: your-api-key" \
  -o photo1.jpg

# 断点续传（下载部分内容）
curl "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/videos/large.mp4" \
  -H "X-API-Key: your-api-key" \
  -H "Range: bytes=0-1048575" \
  -o chunk1.mp4

# 条件下载（缓存验证）
curl "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/data.json" \
  -H "X-API-Key: your-api-key" \
  -H "If-None-Match: \"d41d8cd98f00b204e9800998ecf8427e\"" \
  -o data.json
```

---

### 获取对象元数据

获取对象的元数据信息，不下载内容。

**请求**

```http
HEAD /api/v1/r2/:bucket/objects/:key
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键 |

**权限**: `read` 或更高

**响应**

```http
HTTP/1.1 200 OK
Content-Type: image/jpeg
Content-Length: 204800
ETag: "d41d8cd98f00b204e9800998ecf8427e"
Last-Modified: Mon, 01 Jan 2024 00:00:00 GMT
X-Custom-Metadata-User-Id: 123
X-Custom-Metadata-Description: 示例图片
X-Custom-Metadata-Tags: photo,vacation
```

**示例**

```bash
curl -I "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo1.jpg" \
  -H "X-API-Key: your-api-key"
```

---

### 上传对象

上传新对象或覆盖现有对象到指定 bucket。

**请求**

```http
PUT /api/v1/r2/:bucket/objects/:key
Content-Type: image/jpeg
X-Custom-Metadata-User-Id: 123
X-Custom-Metadata-Description: 我的照片

[二进制数据]
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键 |

**请求头**

| Header | 必需 | 说明 |
|--------|------|------|
| `Content-Type` | 推荐 | MIME 类型（自动检测） |
| `Content-Length` | 推荐 | 内容长度 |
| `Content-MD5` | 否 | MD5 校验和（base64） |
| `Content-SHA256` | 否 | SHA256 校验和（hex） |
| `X-Custom-Metadata-*` | 否 | 自定义元数据（最多 2KB，键名转小写） |
| `Cache-Control` | 否 | 缓存控制（如 `public, max-age=3600`） |

**权限**: `write` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "bucket": "media-storage",
    "key": "images/photo1.jpg",
    "size": 204800,
    "etag": "d41d8cd98f00b204e9800998ecf8427e",
    "content_type": "image/jpeg",
    "uploaded_at": "2024-01-20T10:00:00.000Z",
    "url": "https://your-worker.workers.dev/public/media-storage/images/photo1.jpg"
  }
}
```

**示例**

```bash
# 上传图片文件
curl -X PUT "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo1.jpg" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: image/jpeg" \
  -H "X-Custom-Metadata-User-Id: 123" \
  -H "X-Custom-Metadata-Tags: vacation,2024" \
  --data-binary @photo1.jpg

# 上传文本内容
curl -X PUT "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/notes/readme.txt" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: text/plain; charset=utf-8" \
  -d "Hello, World!"

# 上传 JSON 数据
curl -X PUT "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/config/settings.json" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"theme": "dark", "language": "zh-CN"}'

# 带 MD5 校验的上传
MD5=$(md5sum photo.jpg | cut -d' ' -f1 | xxd -r -p | base64)
curl -X PUT "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo.jpg" \
  -H "X-API-Key: your-api-key" \
  -H "Content-MD5: $MD5" \
  --data-binary @photo.jpg
```

---

### 删除对象

删除指定 bucket 中的对象。

**请求**

```http
DELETE /api/v1/r2/:bucket/objects/:key
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键 |

**权限**: `delete` 或 `admin`

**响应**

```json
{
  "success": true,
  "data": {
    "bucket": "media-storage",
    "key": "images/photo1.jpg",
    "deleted": true,
    "deleted_at": "2024-01-20T10:00:00.000Z"
  }
}
```

**示例**

```bash
curl -X DELETE "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/old-photo.jpg" \
  -H "X-API-Key: your-api-key"
```

---

### 复制对象

在同一 bucket 内或跨 bucket 复制对象。

**请求**

```http
POST /api/v1/r2/:bucket/objects/:key/copy
Content-Type: application/json
```

```json
{
  "destination_bucket": "backup-data",
  "destination_key": "images/photo1-backup.jpg",
  "metadata_directive": "COPY"
}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | 源 bucket 名称 |
| `key` | string | 源对象键 |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `destination_bucket` | string | 否 | 目标 bucket（默认同源 bucket） |
| `destination_key` | string | 是 | 目标对象键 |
| `metadata_directive` | string | 否 | `COPY`（复制元数据）或 `REPLACE`（替换元数据），默认 `COPY` |
| `custom_metadata` | object | 否 | 新的自定义元数据（仅当 `REPLACE` 时） |
| `cache_control` | string | 否 | 新的缓存控制（仅当 `REPLACE` 时） |

**权限**: 
- 源 bucket: `read` 或更高
- 目标 bucket: `write` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "source_bucket": "media-storage",
    "source_key": "images/photo1.jpg",
    "destination_bucket": "backup-data",
    "destination_key": "images/photo1-backup.jpg",
    "copied": true,
    "etag": "d41d8cd98f00b204e9800998ecf8427e",
    "size": 204800,
    "copied_at": "2024-01-20T10:00:00.000Z"
  }
}
```

**示例**

```bash
# 在同一 bucket 内复制
curl -X POST "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo1.jpg/copy" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "destination_key": "images/backup/photo1.jpg"
  }'

# 跨 bucket 复制
curl -X POST "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo1.jpg/copy" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "destination_bucket": "backup-data",
    "destination_key": "media/photo1.jpg"
  }'

# 复制并替换元数据
curl -X POST "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo1.jpg/copy" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "destination_key": "images/photo1-v2.jpg",
    "metadata_directive": "REPLACE",
    "custom_metadata": {
      "version": "2",
      "updated_by": "admin"
    }
  }'
```

---

## 对象列表

### 列出对象

列出指定 bucket 中的对象，支持前缀过滤和目录模拟。

**请求**

```http
GET /api/v1/r2/:bucket/objects?prefix=images/&delimiter=/&limit=100
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |

**查询参数**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `prefix` | string | 否 | 对象键前缀过滤 |
| `delimiter` | string | 否 | 分隔符（通常为 `/`），用于模拟目录结构 |
| `limit` | integer | 否 | 每页数量（默认 100，最大 1000） |
| `cursor` | string | 否 | 分页游标（从上次响应获取） |
| `include_metadata` | boolean | 否 | 是否包含自定义元数据（默认 false） |

**权限**: `read` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "bucket": "media-storage",
    "prefix": "images/",
    "delimiter": "/",
    "objects": [
      {
        "key": "images/photo1.jpg",
        "size": 204800,
        "size_human": "200 KB",
        "uploaded_at": "2024-01-01T00:00:00.000Z",
        "etag": "d41d8cd98f00b204e9800998ecf8427e",
        "content_type": "image/jpeg",
        "custom_metadata": {
          "user_id": "123",
          "description": "示例图片"
        },
        "url": "https://your-worker.workers.dev/public/media-storage/images/photo1.jpg"
      },
      {
        "key": "images/photo2.png",
        "size": 153600,
        "size_human": "150 KB",
        "uploaded_at": "2024-01-02T00:00:00.000Z",
        "etag": "e4d909c290d0fb1ca068ffaddf22cbd0",
        "content_type": "image/png",
        "url": "https://your-worker.workers.dev/public/media-storage/images/photo2.png"
      }
    ],
    "common_prefixes": [
      "images/avatars/",
      "images/backgrounds/"
    ],
    "truncated": false,
    "cursor": null
  },
  "meta": {
    "count": 2,
    "total_size": 358400,
    "common_prefix_count": 2
  }
}
```

**示例**

```bash
# 列出所有对象
curl "https://your-worker.workers.dev/api/v1/r2/media-storage/objects" \
  -H "X-API-Key: your-api-key"

# 按前缀过滤（列出特定目录）
curl "https://your-worker.workers.dev/api/v1/r2/media-storage/objects?prefix=images/avatars/" \
  -H "X-API-Key: your-api-key"

# 模拟目录结构（使用分隔符）
curl "https://your-worker.workers.dev/api/v1/r2/media-storage/objects?prefix=images/&delimiter=/" \
  -H "X-API-Key: your-api-key"

# 分页查询
curl "https://your-worker.workers.dev/api/v1/r2/media-storage/objects?limit=50&cursor=eyJrZXkiOiJpbWFnZXMvcGhvdG81MC5qcGcifQ" \
  -H "X-API-Key: your-api-key"

# 包含完整元数据
curl "https://your-worker.workers.dev/api/v1/r2/media-storage/objects?include_metadata=true" \
  -H "X-API-Key: your-api-key"
```

---

## 公网访问

### 公网下载对象

通过公网 URL 直接访问对象（无需认证，需配置公开权限）。

**请求**

```http
GET /public/:bucket/:key
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键（支持多级路径） |

**权限**: 无需认证（如果 bucket 配置为公开访问）

**响应**

```http
HTTP/1.1 200 OK
Content-Type: image/jpeg
Content-Length: 204800
ETag: "d41d8cd98f00b204e9800998ecf8427e"
Cache-Control: public, max-age=86400
Access-Control-Allow-Origin: *

[二进制数据]
```

**示例**

```bash
# 直接访问公开对象
curl "https://your-worker.workers.dev/public/media-storage/images/photo1.jpg" \
  -o photo1.jpg

# 在浏览器中直接访问
# https://your-worker.workers.dev/public/media-storage/images/photo1.jpg
```

---

## 预签名 URL

### 生成预签名下载 URL

生成临时的预签名 URL，用于在有限时间内下载对象。

**请求**

```http
POST /api/v1/r2/:bucket/objects/:key/presigned-url
Content-Type: application/json
```

```json
{
  "method": "GET",
  "expires_in": 3600
}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键 |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `method` | string | 否 | HTTP 方法：`GET`（下载）或 `PUT`（上传），默认 `GET` |
| `expires_in` | integer | 否 | 过期时间（秒），默认 3600，最大 604800（7天） |
| `content_type` | string | 否 | 指定 Content-Type（仅上传 URL） |

**权限**: 
- 下载 URL: `read` 或更高
- 上传 URL: `write` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "url": "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo1.jpg?signature=abc123&expires=1705751234",
    "method": "GET",
    "expires_at": "2024-01-20T11:00:00.000Z",
    "expires_in": 3600
  }
}
```

**示例**

```bash
# 生成下载 URL
curl -X POST "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo1.jpg/presigned-url" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "GET",
    "expires_in": 7200
  }'

# 生成上传 URL
curl -X POST "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/uploads/newfile.jpg/presigned-url" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "PUT",
    "expires_in": 1800,
    "content_type": "image/jpeg"
  }'

# 使用预签名 URL（无需 API Key）
curl "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/images/photo1.jpg?signature=abc123&expires=1705751234" \
  -o photo1.jpg
```

---

## 分片上传

支持大文件的分片上传（Multipart Upload），类似 S3 API。

### 初始化分片上传

**请求**

```http
POST /api/v1/r2/:bucket/objects/:key/multipart
Content-Type: application/json
```

```json
{
  "content_type": "video/mp4",
  "custom_metadata": {
    "title": "大视频文件"
  }
}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键 |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `content_type` | string | 否 | MIME 类型 |
| `custom_metadata` | object | 否 | 自定义元数据 |

**权限**: `write` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "bucket": "media-storage",
    "key": "videos/large-video.mp4",
    "upload_id": "upload_xxxxxx",
    "created_at": "2024-01-20T10:00:00.000Z"
  }
}
```

---

### 上传分片

**请求**

```http
PUT /api/v1/r2/:bucket/objects/:key/multipart/:uploadId/:partNumber
Content-Type: application/octet-stream

[分片二进制数据]
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键 |
| `uploadId` | string | 上传 ID（从初始化获取） |
| `partNumber` | integer | 分片号（从 1 开始，最大 10000） |

**权限**: `write` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "part_number": 1,
    "etag": "d41d8cd98f00b204e9800998ecf8427e",
    "size": 10485760
  }
}
```

---

### 完成分片上传

**请求**

```http
POST /api/v1/r2/:bucket/objects/:key/multipart/:uploadId/complete
Content-Type: application/json
```

```json
{
  "parts": [
    {"part_number": 1, "etag": "d41d8cd98f00b204e9800998ecf8427e"},
    {"part_number": 2, "etag": "e4d909c290d0fb1ca068ffaddf22cbd0"}
  ]
}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键 |
| `uploadId` | string | 上传 ID |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `parts` | array | 是 | 所有分片信息（按 part_number 排序） |
| `parts[].part_number` | integer | 是 | 分片号 |
| `parts[].etag` | string | 是 | 分片的 ETag |

**权限**: `write` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "bucket": "media-storage",
    "key": "videos/large-video.mp4",
    "etag": "combined-etag-xxxxx",
    "size": 20971520,
    "completed_at": "2024-01-20T10:05:00.000Z",
    "url": "https://your-worker.workers.dev/public/media-storage/videos/large-video.mp4"
  }
}
```

---

### 取消分片上传

**请求**

```http
DELETE /api/v1/r2/:bucket/objects/:key/multipart/:uploadId
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bucket` | string | Bucket 名称 |
| `key` | string | 对象键 |
| `uploadId` | string | 上传 ID |

**权限**: `write` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "upload_id": "upload_xxxxxx",
    "aborted": true
  }
}
```

---

### 分片上传完整示例

```bash
# 1. 初始化上传
UPLOAD_RESPONSE=$(curl -X POST \
  "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/videos/large.mp4/multipart" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"content_type": "video/mp4"}')

UPLOAD_ID=$(echo $UPLOAD_RESPONSE | jq -r '.data.upload_id')

# 2. 上传分片（每片 10MB）
split -b 10485760 large.mp4 part_

PART_NUM=1
for PART in part_*; do
  ETAG=$(curl -X PUT \
    "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/videos/large.mp4/multipart/$UPLOAD_ID/$PART_NUM" \
    -H "X-API-Key: your-api-key" \
    -H "Content-Type: application/octet-stream" \
    --data-binary @$PART \
    | jq -r '.data.etag')
  
  echo "{\"part_number\": $PART_NUM, \"etag\": \"$ETAG\"}" >> parts.json
  PART_NUM=$((PART_NUM + 1))
done

# 3. 完成上传
PARTS=$(jq -s '{"parts": .}' parts.json)
curl -X POST \
  "https://your-worker.workers.dev/api/v1/r2/media-storage/objects/videos/large.mp4/multipart/$UPLOAD_ID/complete" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d "$PARTS"
```

---

## 限制和配额

- **单个对象最大大小**: 5 TB
- **分片上传**:
  - 单个分片: 5 MB - 5 GB
  - 最大分片数: 10,000
  - 最小分片大小: 5 MB（最后一个分片除外）
- **自定义元数据**: 最大 2 KB
- **对象键**: 最大 1024 字符（UTF-8）
- **并发上传**: 建议 < 100 并发连接

---

## 错误代码

| 错误代码 | HTTP 状态 | 说明 |
|----------|-----------|------|
| `BUCKET_NOT_FOUND` | 404 | Bucket 不存在或无权限访问 |
| `BUCKET_ACCESS_DENIED` | 403 | 没有访问该 bucket 的权限 |
| `OBJECT_NOT_FOUND` | 404 | 对象不存在 |
| `OBJECT_ALREADY_EXISTS` | 409 | 对象已存在（某些操作） |
| `INVALID_KEY` | 400 | 无效的对象键（包含非法字符或过长） |
| `INVALID_BUCKET_NAME` | 400 | 无效的 bucket 名称 |
| `FILE_TOO_LARGE` | 413 | 文件超过大小限制 |
| `CHECKSUM_MISMATCH` | 400 | MD5/SHA256 校验失败 |
| `INVALID_PART` | 400 | 分片号无效或分片不完整 |
| `UPLOAD_NOT_FOUND` | 404 | 分片上传 ID 不存在或已过期 |
| `STORAGE_ERROR` | 500 | 存储服务错误 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超出速率限制 |
| `SIGNATURE_INVALID` | 403 | 预签名 URL 签名无效或已过期 |

---

## 错误响应示例

### Bucket 不存在

```json
{
  "success": false,
  "error": {
    "code": "BUCKET_NOT_FOUND",
    "message": "Bucket 'non-existent' 不存在或无权限访问",
    "details": {
      "bucket": "non-existent"
    }
  },
  "meta": {
    "timestamp": "2024-01-20T10:00:00.000Z",
    "request_id": "req_abc123"
  }
}
```

### 对象不存在

```json
{
  "success": false,
  "error": {
    "code": "OBJECT_NOT_FOUND",
    "message": "对象 'images/missing.jpg' 在 bucket 'media-storage' 中不存在",
    "details": {
      "bucket": "media-storage",
      "key": "images/missing.jpg"
    }
  }
}
```

### 权限不足

```json
{
  "success": false,
  "error": {
    "code": "BUCKET_ACCESS_DENIED",
    "message": "当前 API Key 没有 bucket 'media-storage' 的写入权限",
    "details": {
      "bucket": "media-storage",
      "required_permission": "write",
      "current_permissions": ["read"]
    }
  }
}
```

### 校验和不匹配

```json
{
  "success": false,
  "error": {
    "code": "CHECKSUM_MISMATCH",
    "message": "上传文件的 MD5 校验和不匹配",
    "details": {
      "expected": "d41d8cd98f00b204e9800998ecf8427e",
      "actual": "e4d909c290d0fb1ca068ffaddf22cbd0"
    }
  }
}
```

---

## 最佳实践

### 1. 使用分片上传大文件

```bash
# ✅ 推荐：大于 100 MB 的文件使用分片上传
# 优点：支持断点续传、并发上传、更可靠

# ❌ 不推荐：直接上传超大文件
# 可能导致超时或失败
```

### 2. 设置合适的 Content-Type

```bash
# ✅ 明确指定 Content-Type
curl -X PUT "..." \
  -H "Content-Type: image/jpeg"

# ❌ 不指定可能导致浏览器下载而非显示
```

### 3. 使用预签名 URL 分享文件

```bash
# ✅ 生成临时 URL 分享
# 安全、可控、不暴露 API Key

# ❌ 直接分享 API Key
# 安全风险
```

### 4. 利用 Range 请求

```bash
# ✅ 断点续传或流式传输
curl -H "Range: bytes=0-1048575" "..."

# 适用于大文件下载、视频流等场景
```

### 5. 设置缓存策略

```bash
# ✅ 静态资源设置长缓存
curl -X PUT "..." \
  -H "Cache-Control: public, max-age=31536000, immutable"

# ✅ 动态内容短缓存或不缓存
-H "Cache-Control: no-cache"
```

### 6. 使用对象键命名规范

```bash
# ✅ 推荐的命名方式
users/123/avatar.jpg
documents/2024/01/report.pdf
assets/v2/images/logo.png

# ❌ 避免的命名方式
../../../etc/passwd  # 路径穿越
object with spaces   # 包含空格（需 URL 编码）
超长的键名...（1024+ 字符）
```

---

## MinIO 兼容性说明

本 API 设计参考 MinIO/S3 标准，主要兼容特性：

### 兼容的操作
- ✅ GetObject（下载对象）
- ✅ PutObject（上传对象）
- ✅ DeleteObject（删除对象）
- ✅ HeadObject（获取元数据）
- ✅ ListObjects（列出对象）
- ✅ CopyObject（复制对象）
- ✅ CreateMultipartUpload（分片上传）
- ✅ PresignedURL（预签名 URL）

### 差异说明
- 认证方式：使用 API Key 而非 AWS Signature V4
- Bucket 管理：通过 Cloudflare 控制台配置
- 区域：固定为 `auto`（自动）
- ACL：通过权限系统管理，非 S3 ACL

### 客户端适配
可以使用 MinIO/AWS SDK，需修改认证方式：

```python
# Python 示例（伪代码）
import requests

class R2Client:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}
    
    def get_object(self, bucket, key):
        url = f"{self.base_url}/api/v1/r2/{bucket}/objects/{key}"
        return requests.get(url, headers=self.headers)
    
    def put_object(self, bucket, key, data):
        url = f"{self.base_url}/api/v1/r2/{bucket}/objects/{key}"
        return requests.put(url, headers=self.headers, data=data)
```
