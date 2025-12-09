"""Main entry point for Cloudflare Worker."""

import json

from workers import Response, WorkerEntrypoint

from d1_manager import D1Manager
from r2_manager import R2Manager

# 嵌入的 API 文档内容
D1_API_DOC = """# D1 数据库 API

管理 Cloudflare D1 数据库的 RESTful API。

## 基础信息

**Base URL**: `/api/v1/d1`
**认证方式**: API Key (Header: `X-API-Key`)

## 核心端点

### 1. 查询数据 (SELECT)

```http
POST /api/v1/d1/query
Content-Type: application/json
X-API-Key: your-api-key

{
  "database": "my-db",
  "sql": "SELECT * FROM users WHERE age > ?",
  "params": [18],
  "limit": 100,
  "offset": 0
}
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    {"id": 1, "name": "Alice", "age": 25},
    {"id": 2, "name": "Bob", "age": 30}
  ],
  "meta": {
    "rows": 2,
    "duration_ms": 5.2
  }
}
```

### 2. 执行操作 (INSERT/UPDATE/DELETE)

```http
POST /api/v1/d1/execute
Content-Type: application/json
X-API-Key: your-api-key

{
  "database": "my-db",
  "sql": "INSERT INTO users (name, age) VALUES (?, ?)",
  "params": ["Charlie", 28]
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "changes": 1,
    "last_row_id": 123
  }
}
```

### 3. 批量操作

```http
POST /api/v1/d1/batch
Content-Type: application/json
X-API-Key: your-api-key

{
  "database": "my-db",
  "statements": [
    {
      "sql": "INSERT INTO users (name, age) VALUES (?, ?)",
      "params": ["David", 35]
    },
    {
      "sql": "UPDATE users SET age = ? WHERE name = ?",
      "params": [36, "David"]
    }
  ]
}
```

### 4. 表管理

**列出所有表**:
```http
GET /api/v1/d1/tables?database=my-db
```

**获取表结构**:
```http
GET /api/v1/d1/tables/users?database=my-db
```

**创建表**:
```http
POST /api/v1/d1/tables
Content-Type: application/json

{
  "database": "my-db",
  "name": "products",
  "columns": [
    {"name": "id", "type": "INTEGER", "primary_key": true},
    {"name": "title", "type": "TEXT", "not_null": true},
    {"name": "price", "type": "REAL"}
  ]
}
```

**删除表**:
```http
DELETE /api/v1/d1/tables/products?database=my-db
```

### 5. 数据导入导出

**导出数据** (JSON 或 SQL 格式):
```http
POST /api/v1/d1/export
Content-Type: application/json

{
  "database": "my-db",
  "format": "json",
  "tables": ["users", "products"]
}
```

**导入数据**:
```http
POST /api/v1/d1/import
Content-Type: application/json

{
  "database": "my-db",
  "format": "json",
  "data": {
    "users": [
      {"name": "Alice", "age": 25},
      {"name": "Bob", "age": 30}
    ]
  }
}
```

## 错误代码

| 代码 | 说明 |
|------|------|
| 400  | 请求参数错误 |
| 401  | 未授权（API Key 无效） |
| 403  | 权限不足 |
| 404  | 数据库或表不存在 |
| 500  | 服务器错误 |

## 完整文档

访问 [GitHub 仓库](https://github.com/tsaitang404/cfmgr/blob/main/docs/api/d1-api.md) 查看完整 API 文档。
"""

R2_API_DOC = """# R2 对象存储 API

管理 Cloudflare R2 对象存储的 RESTful API，提供 S3 兼容接口。

## 基础信息

**Base URL**: `/api/v1/r2`
**认证方式**: API Key (Header: `X-API-Key`) 或预签名 URL

## 核心端点

### 1. 上传对象

```http
POST /api/v1/r2/objects
Content-Type: multipart/form-data
X-API-Key: your-api-key

{
  "bucket": "my-bucket",
  "key": "images/photo.jpg",
  "file": <binary data>,
  "metadata": {
    "author": "Alice",
    "category": "photos"
  },
  "cache_control": "public, max-age=31536000"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "key": "images/photo.jpg",
    "size": 102400,
    "size_human": "100 KB",
    "etag": "abc123...",
    "uploaded_at": "2024-01-20T10:00:00.000Z",
    "url": "https://your-bucket.r2.cloudflarestorage.com/images/photo.jpg"
  }
}
```

### 2. 下载对象

```http
GET /api/v1/r2/objects/images/photo.jpg?bucket=my-bucket
X-API-Key: your-api-key
```

**支持 Range 请求**:
```http
GET /api/v1/r2/objects/video.mp4?bucket=my-bucket
Range: bytes=0-1023
```

### 3. 列出对象

```http
GET /api/v1/r2/objects?bucket=my-bucket&prefix=images/&limit=100
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "objects": [
      {
        "key": "images/photo1.jpg",
        "size": 102400,
        "size_human": "100 KB",
        "last_modified": "2024-01-20T10:00:00.000Z",
        "etag": "abc123..."
      }
    ],
    "truncated": false,
    "next_cursor": null
  }
}
```

### 4. 获取对象元数据

```http
HEAD /api/v1/r2/objects/images/photo.jpg?bucket=my-bucket
```

### 5. 删除对象

```http
DELETE /api/v1/r2/objects/images/photo.jpg?bucket=my-bucket
```

### 6. 复制对象

```http
POST /api/v1/r2/copy
Content-Type: application/json

{
  "source_bucket": "my-bucket",
  "source_key": "images/original.jpg",
  "destination_bucket": "backup-bucket",
  "destination_key": "archive/original.jpg",
  "metadata_directive": "REPLACE",
  "metadata": {
    "archived": "true"
  }
}
```

### 7. 分片上传 (大文件)

**初始化分片上传**:
```http
POST /api/v1/r2/multipart
Content-Type: application/json

{
  "bucket": "my-bucket",
  "key": "large-file.zip",
  "metadata": {"type": "archive"}
}
```

**上传分片**:
```http
PUT /api/v1/r2/multipart/:upload_id/parts/:part_number
Content-Type: application/octet-stream

<binary chunk data>
```

**完成上传**:
```http
POST /api/v1/r2/multipart/:upload_id/complete
Content-Type: application/json

{
  "parts": [
    {"part_number": 1, "etag": "abc123..."},
    {"part_number": 2, "etag": "def456..."}
  ]
}
```

**取消上传**:
```http
DELETE /api/v1/r2/multipart/:upload_id
```

### 8. 预签名 URL (公网访问)

```http
POST /api/v1/r2/presign
Content-Type: application/json

{
  "bucket": "my-bucket",
  "key": "images/photo.jpg",
  "expires_in": 3600,
  "method": "GET"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "url": "https://your-worker.workers.dev/public/abc123...?expires=1234567890&signature=xyz...",
    "expires_at": "2024-01-20T11:00:00.000Z"
  }
}
```

## Bucket 管理

**列出所有 Buckets**:
```http
GET /api/v1/r2/buckets
```

**获取 Bucket 信息**:
```http
GET /api/v1/r2/buckets/my-bucket
```

## 错误代码

| 代码 | 说明 |
|------|------|
| 400  | 请求参数错误 |
| 401  | 未授权（API Key 无效） |
| 403  | 权限不足 |
| 404  | Bucket 或对象不存在 |
| 409  | 冲突（对象已存在） |
| 413  | 文件过大 |
| 500  | 服务器错误 |

## 完整文档

访问 [GitHub 仓库](https://github.com/tsaitang404/cfmgr/blob/main/docs/api/r2-api.md) 查看完整 API 文档。
"""


def render_html_docs(title, content):
    """Render markdown documentation as HTML using marked.js and highlight.js."""
    # 转义内容用于 JavaScript
    content_escaped = content.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - cfmgr API 文档</title>

    <!-- Highlight.js CSS (GitHub Dark theme) -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">

    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin: 20px 0;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: #3498db;
            text-decoration: none;
            font-weight: 500;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        #content h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
            text-align: left;
        }}
        #content h2 {{
            color: #34495e;
            margin-top: 40px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
            text-align: left;
        }}
        #content h3 {{
            color: #7f8c8d;
            margin-top: 30px;
            text-align: left;
        }}
        #content h4, #content h5, #content h6 {{
            text-align: left;
        }}
        #content p, #content ul, #content ol {{
            text-align: left;
        }}
        #content code {{
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Courier New", Consolas, monospace;
            color: #e74c3c;
            font-size: 0.9em;
        }}
        #content pre {{
            background: #2d2d2d;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: left;
        }}
        #content pre code {{
            background: none;
            color: #f8f8f2;
            padding: 0;
            font-size: 0.9em;
            line-height: 1.5;
            text-align: left;
            display: block;
        }}
        #content table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        #content th, #content td {{
            border: 1px solid #ddd;
            padding: 12px 15px;
            text-align: left;
        }}
        #content th {{
            background: #3498db;
            color: white;
            font-weight: 600;
        }}
        #content tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        #content tr:hover {{
            background: #e8f4f8;
        }}
        #content a {{
            color: #3498db;
            text-decoration: none;
            font-weight: 500;
        }}
        #content a:hover {{
            text-decoration: underline;
        }}
        #content blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 20px;
            margin: 20px 0;
            color: #7f8c8d;
            background: #f8f9fa;
            padding: 15px 20px;
            border-radius: 4px;
        }}
        #content ul, #content ol {{
            padding-left: 30px;
            margin: 15px 0;
        }}
        #content li {{
            margin: 8px 0;
        }}
        #content hr {{
            border: none;
            border-top: 2px solid #ecf0f1;
            margin: 30px 0;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #7f8c8d;
        }}
    </style>

    <!-- Marked.js for Markdown parsing -->
    <script src="https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js"></script>

    <!-- Highlight.js for code syntax highlighting -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
</head>
<body>
    <div class="container">
        <a href="/docs" class="back-link">← 返回文档首页</a>
        <div id="content" class="loading">正在加载文档...</div>
    </div>

    <script>
        // Markdown 内容
        const markdownContent = `{content_escaped}`;

        // 配置 marked.js
        marked.setOptions({{
            breaks: true,
            gfm: true,
            headerIds: true,
            mangle: false
        }});

        // 渲染 Markdown
        document.addEventListener('DOMContentLoaded', function() {{
            const contentDiv = document.getElementById('content');

            try {{
                // 转换 Markdown 为 HTML
                const html = marked.parse(markdownContent);
                contentDiv.innerHTML = html;

                // 高亮代码块
                contentDiv.querySelectorAll('pre code').forEach((block) => {{
                    hljs.highlightElement(block);
                }});

                // 为外部链接添加 target="_blank"
                contentDiv.querySelectorAll('a[href^="http"]').forEach((link) => {{
                    link.setAttribute('target', '_blank');
                    link.setAttribute('rel', 'noopener noreferrer');
                }});
            }} catch (error) {{
                contentDiv.innerHTML = '<p style="color: red;">文档渲染失败：' + error.message + '</p>';
            }}
        }});
    </script>
</body>
</html>"""
    return html


class Default(WorkerEntrypoint):
    async def on_fetch(self, request):
        """Handle incoming HTTP requests."""
        # Parse URL path
        url_parts = request.url.split("/")
        path = "/".join(url_parts[3:]) if len(url_parts) > 3 else ""
        path = path.split("?")[0]  # Remove query params

        # Public routes (no authentication required)
        public_routes = ["", "health", "docs", "docs/", "docs/d1", "docs/r2"]

        # Check authentication for non-public routes
        if path not in public_routes and not path.startswith("docs"):
            api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
            expected_api_key = getattr(self.env, "API_KEY", None)

            # If API_KEY is configured, validate it
            if expected_api_key:
                if not api_key:
                    return Response(
                        json.dumps(
                            {
                                "success": False,
                                "error": "Missing API Key",
                                "message": "Please provide X-API-Key header",
                            }
                        ),
                        headers={"Content-Type": "application/json"},
                        status=401,
                    )

                if api_key != expected_api_key:
                    return Response(
                        json.dumps(
                            {
                                "success": False,
                                "error": "Invalid API Key",
                                "message": "The provided API Key is invalid",
                            }
                        ),
                        headers={"Content-Type": "application/json"},
                        status=403,
                    )

        # API Documentation routes
        if path.startswith("docs"):
            if path == "docs" or path == "docs/":
                # 文档首页
                index_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>cfmgr API 文档</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1000px;
            margin: 50px auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 40px;
            font-size: 1.2em;
        }}
        .docs-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }}
        .doc-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.3s, box-shadow 0.3s;
            cursor: pointer;
        }}
        .doc-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.3);
        }}
        .doc-card h2 {{
            color: white;
            margin: 0 0 15px 0;
            font-size: 2em;
        }}
        .doc-card p {{
            color: rgba(255,255,255,0.9);
            margin: 10px 0;
        }}
        .doc-card a {{
            color: white;
            text-decoration: none;
            display: inline-block;
            margin-top: 15px;
            padding: 10px 25px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            font-weight: bold;
            transition: background 0.3s;
        }}
        .doc-card a:hover {{
            background: rgba(255,255,255,0.3);
        }}
        .info {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
        }}
        .info h3 {{ color: #2c3e50; margin-top: 0; }}
        .endpoint {{
            background: #f8f9fa;
            padding: 10px;
            border-left: 4px solid #3498db;
            margin: 10px 0;
            font-family: monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 cfmgr API 文档</h1>
        <p class="subtitle">Cloudflare Worker D1 数据库 & R2 对象存储管理平台</p>

        <div class="docs-grid">
            <div class="doc-card">
                <h2>📊 D1 数据库</h2>
                <p>完整的 D1 数据库管理 API</p>
                <p>查询、执行、批量操作、表管理、数据导入导出</p>
                <a href="/docs/d1">查看文档 →</a>
            </div>

            <div class="doc-card">
                <h2>🗄️ R2 存储</h2>
                <p>S3 兼容的对象存储 API</p>
                <p>上传、下载、列表、分片上传、预签名 URL</p>
                <a href="/docs/r2">查看文档 →</a>
            </div>
        </div>

        <div class="info">
            <h3>快速开始</h3>
            <p><strong>Base URL:</strong> <code>https://your-worker.workers.dev/api/v1</code></p>
            <p><strong>认证方式:</strong> API Key (Header: <code>X-API-Key</code>)</p>

            <h3>核心端点</h3>
            <div class="endpoint">GET / - 服务信息</div>
            <div class="endpoint">GET /health - 健康检查</div>
            <div class="endpoint">GET /docs - 文档首页（当前页面）</div>
            <div class="endpoint">GET /docs/d1 - D1 数据库文档</div>
            <div class="endpoint">GET /docs/r2 - R2 存储文档</div>

            <p style="margin-top: 20px; color: #7f8c8d;">
                <strong>项目主页:</strong> <a href="https://github.com/tsaitang404/cfmgr" target="_blank">github.com/tsaitang404/cfmgr</a>
            </p>
        </div>
    </div>
</body>
</html>"""
                return Response(index_html, headers={"Content-Type": "text/html; charset=utf-8"})

            elif path == "docs/d1":
                # D1 API 文档
                html = render_html_docs("D1 数据库 API", D1_API_DOC)
                return Response(html, headers={"Content-Type": "text/html; charset=utf-8"})

            elif path == "docs/r2":
                # R2 API 文档
                html = render_html_docs("R2 对象存储 API", R2_API_DOC)
                return Response(html, headers={"Content-Type": "text/html; charset=utf-8"})

        # Root endpoint
        if not path or path == "":
            return Response(
                json.dumps(
                    {
                        "service": "cfmgr",
                        "version": "1.0.0",
                        "description": "Cloudflare Worker for D1 & R2 management",
                        "documentation": "/docs",
                        "endpoints": {
                            "health": "GET /health",
                            "docs": "GET /docs",
                            "d1_api": "/api/v1/d1/*",
                            "r2_api": "/api/v1/r2/*",
                        },
                    }
                ),
                headers={"Content-Type": "application/json"},
            )

        # Health check
        if path == "health":
            return Response(
                json.dumps({"status": "ok", "service": "cfmgr"}),
                headers={"Content-Type": "application/json"},
            )

        # Initialize managers
        d1_manager = D1Manager(self.env.DB)
        r2_manager = R2Manager(self.env.R2)

        # D1 query endpoint
        if path == "d1/query" and request.method == "POST":
            try:
                body = await request.json()
                sql = body.get("sql", "")
                params = body.get("params", [])
                result = await d1_manager.query(sql, params)
                return Response(json.dumps(result), headers={"Content-Type": "application/json"})
            except Exception as e:
                return Response(
                    json.dumps({"success": False, "error": str(e)}),
                    headers={"Content-Type": "application/json"},
                    status=500,
                )

        # D1 execute endpoint
        if path == "d1/execute" and request.method == "POST":
            try:
                body = await request.json()
                sql = body.get("sql", "")
                params = body.get("params", [])
                result = await d1_manager.execute(sql, params)
                return Response(json.dumps(result), headers={"Content-Type": "application/json"})
            except Exception as e:
                return Response(
                    json.dumps({"success": False, "error": str(e)}),
                    headers={"Content-Type": "application/json"},
                    status=500,
                )

        # D1 tables endpoint
        if path == "d1/tables" and request.method == "GET":
            try:
                result = await d1_manager.get_tables()
                return Response(json.dumps(result), headers={"Content-Type": "application/json"})
            except Exception as e:
                return Response(
                    json.dumps({"success": False, "error": str(e)}),
                    headers={"Content-Type": "application/json"},
                    status=500,
                )

        # R2 list endpoint
        if path == "r2/list" and request.method == "GET":
            try:
                result = await r2_manager.list_objects()
                return Response(json.dumps(result), headers={"Content-Type": "application/json"})
            except Exception as e:
                return Response(
                    json.dumps({"success": False, "error": str(e)}),
                    headers={"Content-Type": "application/json"},
                    status=500,
                )

        # 404 Not Found
        return Response(
            json.dumps({"error": "Not Found", "path": path}),
            headers={"Content-Type": "application/json"},
            status=404,
        )
