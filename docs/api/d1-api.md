# D1 数据库 API

管理 Cloudflare D1 数据库的 RESTful API，支持多数据库操作和细粒度权限控制。

## 基础信息

**Base URL**: `/api/v1/d1`

**认证方式**: API Key (Header: `X-API-Key`)

**权限级别**:
- `query` - 执行查询（SELECT）
- `execute` - 执行写操作（INSERT, UPDATE, DELETE）
- `admin` - 管理数据库（CREATE TABLE, DROP TABLE, ALTER）

---

## 目录

- [Database 管理](#database-管理)
- [查询操作](#查询操作)
- [执行操作](#执行操作)
- [批量操作](#批量操作)
- [表管理](#表管理)
- [数据导入导出](#数据导入导出)
- [错误代码](#错误代码)

---

## Database 管理

### 列出所有 Databases

列出当前 API Key 有权限访问的所有数据库。

**请求**

```http
GET /api/v1/d1/databases
```

**权限**: 任意（仅返回有权限的数据库）

**响应**

```json
{
  "success": true,
  "data": {
    "databases": [
      {
        "name": "production-db",
        "id": "db_xxxxxx",
        "size_bytes": 10485760,
        "table_count": 15,
        "created_at": "2024-01-01T00:00:00.000Z",
        "permissions": ["query", "execute"]
      },
      {
        "name": "analytics-db",
        "id": "db_yyyyyy",
        "size_bytes": 52428800,
        "table_count": 8,
        "created_at": "2024-01-15T00:00:00.000Z",
        "permissions": ["query"]
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
curl "https://your-worker.workers.dev/api/v1/d1/databases" \
  -H "X-API-Key: your-api-key"
```

---

### 获取 Database 信息

获取指定数据库的详细信息和统计数据。

**请求**

```http
GET /api/v1/d1/databases/:database
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |

**权限**: 任意（至少需要对该数据库的读权限）

**响应**

```json
{
  "success": true,
  "data": {
    "name": "production-db",
    "id": "db_xxxxxx",
    "size_bytes": 10485760,
    "size_human": "10 MB",
    "table_count": 15,
    "row_count_estimate": 125000,
    "created_at": "2024-01-01T00:00:00.000Z",
    "last_query_at": "2024-01-20T09:55:00.000Z",
    "permissions": ["query", "execute", "admin"]
  }
}
```

**示例**

```bash
curl "https://your-worker.workers.dev/api/v1/d1/databases/production-db" \
  -H "X-API-Key: your-api-key"
```

---

### 获取 Database 统计信息

获取数据库的详细统计信息，包括查询性能指标。

**请求**

```http
GET /api/v1/d1/databases/:database/stats
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |

**查询参数**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `period` | string | 否 | 统计周期：`1h`, `24h`, `7d`, `30d`（默认 `24h`） |

**权限**: `query` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "database": "production-db",
    "period": "24h",
    "stats": {
      "total_queries": 15420,
      "total_rows_read": 1250000,
      "total_rows_written": 8500,
      "avg_query_time_ms": 12.5,
      "slow_queries": 23,
      "errors": 5
    },
    "top_tables": [
      {
        "name": "users",
        "row_count": 50000,
        "size_bytes": 5242880,
        "index_count": 3
      }
    ],
    "generated_at": "2024-01-20T10:00:00.000Z"
  }
}
```

**示例**

```bash
curl "https://your-worker.workers.dev/api/v1/d1/databases/production-db/stats?period=7d" \
  -H "X-API-Key: your-api-key"
```

---

## 查询操作

### 执行查询

执行 SELECT 查询语句，支持参数化查询。

**请求**

```http
POST /api/v1/d1/:database/query
Content-Type: application/json
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `sql` | string | 是 | SQL 查询语句（仅支持 SELECT） |
| `params` | object/array | 否 | 参数化查询的参数 |
| `limit` | integer | 否 | 返回结果数量限制（默认 100，最大 10000） |
| `offset` | integer | 否 | 偏移量，用于分页 |

**参数化查询格式**:
- 命名参数: `?name` 或 `:name`，params 使用对象 `{"name": "value"}`
- 位置参数: `?` 或 `?1`, `?2`，params 使用数组 `["value1", "value2"]`

**权限**: `query` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": 1,
        "name": "张三",
        "email": "zhangsan@example.com",
        "created_at": "2024-01-01T00:00:00.000Z"
      },
      {
        "id": 2,
        "name": "李四",
        "email": "lisi@example.com",
        "created_at": "2024-01-02T00:00:00.000Z"
      }
    ],
    "meta": {
      "rows_read": 2,
      "duration_ms": 5.2,
      "has_more": false
    }
  }
}
```

**示例**

```bash
# 简单查询
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/query" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM users LIMIT 10"
  }'

# 命名参数查询
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/query" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM users WHERE status = ?status AND created_at > ?date",
    "params": {
      "status": "active",
      "date": "2024-01-01"
    }
  }'

# 位置参数查询
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/query" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM users WHERE id = ? AND email = ?",
    "params": [123, "user@example.com"]
  }'

# 分页查询
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/query" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM users ORDER BY id",
    "limit": 50,
    "offset": 100
  }'
```

---

## 执行操作

### 执行写操作

执行 INSERT、UPDATE、DELETE 等数据修改操作。

**请求**

```http
POST /api/v1/d1/:database/execute
Content-Type: application/json
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `sql` | string | 是 | SQL 语句（INSERT, UPDATE, DELETE） |
| `params` | object/array | 否 | 参数化查询的参数 |

**权限**: `execute` 或 `admin`

**响应**

```json
{
  "success": true,
  "data": {
    "meta": {
      "rows_read": 0,
      "rows_written": 1,
      "last_row_id": 124,
      "changes": 1,
      "duration_ms": 3.8
    }
  }
}
```

**示例**

```bash
# 插入数据
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/execute" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "INSERT INTO users (name, email, status) VALUES (?name, ?email, ?status)",
    "params": {
      "name": "王五",
      "email": "wangwu@example.com",
      "status": "active"
    }
  }'

# 更新数据
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/execute" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "UPDATE users SET status = ?status WHERE id = ?id",
    "params": {
      "status": "inactive",
      "id": 123
    }
  }'

# 删除数据
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/execute" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "DELETE FROM users WHERE id = ?",
    "params": [123]
  }'
```

---

## 批量操作

### 批量执行 SQL

在单个事务中执行多条 SQL 语句，保证原子性（全部成功或全部失败）。

**请求**

```http
POST /api/v1/d1/:database/batch
Content-Type: application/json
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `statements` | array | 是 | SQL 语句数组 |
| `statements[].sql` | string | 是 | SQL 语句 |
| `statements[].params` | object/array | 否 | 参数 |

**权限**: 根据 SQL 类型，需要 `query`、`execute` 或 `admin`

**响应**

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "success": true,
        "meta": {
          "rows_written": 1,
          "last_row_id": 1,
          "changes": 1
        }
      },
      {
        "success": true,
        "meta": {
          "rows_written": 1,
          "last_row_id": 2,
          "changes": 1
        }
      }
    ],
    "meta": {
      "total_statements": 2,
      "successful": 2,
      "failed": 0,
      "total_rows_written": 2,
      "duration_ms": 12.5
    }
  }
}
```

**失败响应（事务回滚）**

```json
{
  "success": false,
  "error": {
    "code": "BATCH_TRANSACTION_FAILED",
    "message": "批量操作失败，所有更改已回滚",
    "details": {
      "failed_statement": 1,
      "error": "UNIQUE constraint failed: users.email"
    }
  }
}
```

**示例**

```bash
# 批量插入
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/batch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "statements": [
      {
        "sql": "INSERT INTO users (name, email) VALUES (?, ?)",
        "params": ["用户1", "user1@example.com"]
      },
      {
        "sql": "INSERT INTO users (name, email) VALUES (?, ?)",
        "params": ["用户2", "user2@example.com"]
      },
      {
        "sql": "INSERT INTO users (name, email) VALUES (?, ?)",
        "params": ["用户3", "user3@example.com"]
      }
    ]
  }'

# 混合操作
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/batch" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "statements": [
      {
        "sql": "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
        "params": [123]
      },
      {
        "sql": "INSERT INTO login_logs (user_id, ip_address) VALUES (?, ?)",
        "params": [123, "192.168.1.1"]
      },
      {
        "sql": "UPDATE users SET login_count = login_count + 1 WHERE id = ?",
        "params": [123]
      }
    ]
  }'
```

---

## 表管理

### 列出所有表

列出数据库中的所有表。

**请求**

```http
GET /api/v1/d1/:database/tables
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |

**权限**: `query` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "tables": [
      {
        "name": "users",
        "type": "table",
        "row_count": 50000,
        "size_bytes": 5242880,
        "created_at": "2024-01-01T00:00:00.000Z"
      },
      {
        "name": "posts",
        "type": "table",
        "row_count": 125000,
        "size_bytes": 15728640,
        "created_at": "2024-01-05T00:00:00.000Z"
      }
    ]
  },
  "meta": {
    "count": 2,
    "total_size_bytes": 20971520
  }
}
```

**示例**

```bash
curl "https://your-worker.workers.dev/api/v1/d1/production-db/tables" \
  -H "X-API-Key: your-api-key"
```

---

### 创建表

创建新的数据库表。

**请求**

```http
POST /api/v1/d1/:database/tables
Content-Type: application/json
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 表名 |
| `schema` | object | 是 | 表结构定义 |
| `if_not_exists` | boolean | 否 | 如果表存在则忽略（默认 false） |

**Schema 定义**

```json
{
  "name": "products",
  "schema": {
    "columns": [
      {
        "name": "id",
        "type": "INTEGER",
        "primary_key": true,
        "auto_increment": true
      },
      {
        "name": "name",
        "type": "TEXT",
        "nullable": false
      },
      {
        "name": "price",
        "type": "REAL",
        "nullable": false,
        "check": "price > 0"
      },
      {
        "name": "created_at",
        "type": "TEXT",
        "default": "CURRENT_TIMESTAMP"
      }
    ],
    "indexes": [
      {
        "name": "idx_name",
        "columns": ["name"],
        "unique": false
      }
    ],
    "constraints": [
      {
        "type": "UNIQUE",
        "columns": ["name"]
      }
    ]
  },
  "if_not_exists": true
}
```

**权限**: `admin`

**响应**

```json
{
  "success": true,
  "data": {
    "table": "products",
    "created": true,
    "sql": "CREATE TABLE products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, price REAL NOT NULL CHECK (price > 0), created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
  }
}
```

**示例**

```bash
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/tables" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "products",
    "schema": {
      "columns": [
        {"name": "id", "type": "INTEGER", "primary_key": true, "auto_increment": true},
        {"name": "name", "type": "TEXT", "nullable": false},
        {"name": "price", "type": "REAL", "nullable": false}
      ]
    },
    "if_not_exists": true
  }'
```

---

### 获取表结构

获取指定表的详细结构信息。

**请求**

```http
GET /api/v1/d1/:database/tables/:name
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |
| `name` | string | 表名 |

**权限**: `query` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "name": "users",
    "type": "table",
    "columns": [
      {
        "cid": 0,
        "name": "id",
        "type": "INTEGER",
        "notnull": 1,
        "dflt_value": null,
        "pk": 1
      },
      {
        "cid": 1,
        "name": "name",
        "type": "TEXT",
        "notnull": 1,
        "dflt_value": null,
        "pk": 0
      },
      {
        "cid": 2,
        "name": "email",
        "type": "TEXT",
        "notnull": 1,
        "dflt_value": null,
        "pk": 0
      }
    ],
    "indexes": [
      {
        "name": "idx_email",
        "unique": 1,
        "columns": ["email"]
      }
    ],
    "row_count": 50000,
    "size_bytes": 5242880,
    "sql": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE)"
  }
}
```

**示例**

```bash
curl "https://your-worker.workers.dev/api/v1/d1/production-db/tables/users" \
  -H "X-API-Key: your-api-key"
```

---

### 获取表索引

获取指定表的所有索引信息。

**请求**

```http
GET /api/v1/d1/:database/tables/:name/indexes
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |
| `name` | string | 表名 |

**权限**: `query` 或更高

**响应**

```json
{
  "success": true,
  "data": {
    "table": "users",
    "indexes": [
      {
        "name": "idx_email",
        "unique": true,
        "columns": ["email"],
        "partial": false,
        "sql": "CREATE UNIQUE INDEX idx_email ON users(email)"
      },
      {
        "name": "idx_created_at",
        "unique": false,
        "columns": ["created_at"],
        "partial": false,
        "sql": "CREATE INDEX idx_created_at ON users(created_at)"
      }
    ]
  },
  "meta": {
    "count": 2
  }
}
```

**示例**

```bash
curl "https://your-worker.workers.dev/api/v1/d1/production-db/tables/users/indexes" \
  -H "X-API-Key: your-api-key"
```

---

### 删除表

删除指定的表（谨慎操作）。

**请求**

```http
DELETE /api/v1/d1/:database/tables/:name
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |
| `name` | string | 表名 |

**查询参数**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `confirm` | string | 是 | 必须为表名，确认删除操作 |

**权限**: `admin`

**响应**

```json
{
  "success": true,
  "data": {
    "table": "old_table",
    "deleted": true
  }
}
```

**示例**

```bash
curl -X DELETE "https://your-worker.workers.dev/api/v1/d1/production-db/tables/old_table?confirm=old_table" \
  -H "X-API-Key: your-api-key"
```

---

## 数据导入导出

### 导出数据

导出表数据为指定格式。

**请求**

```http
POST /api/v1/d1/:database/export
Content-Type: application/json
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `tables` | array | 否 | 要导出的表名列表（不指定则导出全部） |
| `format` | string | 否 | 导出格式：`sql`, `csv`, `json`（默认 `sql`） |
| `include_schema` | boolean | 否 | 是否包含表结构（默认 true） |

**权限**: `query` 或更高

**响应（SQL 格式）**

```json
{
  "success": true,
  "data": {
    "format": "sql",
    "content": "CREATE TABLE users (...); INSERT INTO users VALUES (...); ...",
    "tables": ["users", "posts"],
    "row_count": 175000,
    "size_bytes": 15728640
  }
}
```

**响应（JSON 格式）**

```json
{
  "success": true,
  "data": {
    "format": "json",
    "tables": {
      "users": [
        {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
        {"id": 2, "name": "李四", "email": "lisi@example.com"}
      ]
    },
    "row_count": 2
  }
}
```

**示例**

```bash
# 导出为 SQL
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/export" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "tables": ["users", "posts"],
    "format": "sql"
  }'

# 导出为 JSON
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/export" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "tables": ["users"],
    "format": "json",
    "include_schema": false
  }'
```

---

### 导入数据

从文件或数据导入到数据库。

**请求**

```http
POST /api/v1/d1/:database/import
Content-Type: application/json
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `database` | string | 数据库名称或 ID |

**请求体**

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `format` | string | 是 | 数据格式：`sql`, `csv`, `json` |
| `content` | string | 是 | 导入内容 |
| `table` | string | 视情况 | 目标表名（CSV/JSON 必需） |
| `truncate` | boolean | 否 | 导入前清空表（默认 false） |

**权限**: `admin`

**响应**

```json
{
  "success": true,
  "data": {
    "format": "sql",
    "rows_imported": 1000,
    "tables_affected": ["users", "posts"],
    "duration_ms": 1250.5
  }
}
```

**示例**

```bash
# 导入 SQL
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/import" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "sql",
    "content": "INSERT INTO users (name, email) VALUES (\"张三\", \"zhangsan@example.com\");"
  }'

# 导入 JSON
curl -X POST "https://your-worker.workers.dev/api/v1/d1/production-db/import" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "format": "json",
    "table": "users",
    "truncate": false,
    "content": "[{\"name\":\"张三\",\"email\":\"zhangsan@example.com\"}]"
  }'
```

---

## 错误代码

| 错误代码 | HTTP 状态 | 说明 |
|----------|-----------|------|
| `DATABASE_NOT_FOUND` | 404 | 数据库不存在或无权限访问 |
| `DATABASE_ACCESS_DENIED` | 403 | 没有访问该数据库的权限 |
| `INVALID_SQL` | 400 | SQL 语法错误 |
| `PERMISSION_DENIED` | 403 | 权限不足（如尝试用 query 权限执行写操作） |
| `MISSING_PARAMETER` | 400 | 缺少必需参数 |
| `INVALID_PARAMETER` | 400 | 参数格式或值无效 |
| `CONSTRAINT_VIOLATION` | 409 | 约束冲突（如唯一键、外键） |
| `TABLE_NOT_FOUND` | 404 | 表不存在 |
| `TABLE_ALREADY_EXISTS` | 409 | 表已存在 |
| `QUERY_TIMEOUT` | 408 | 查询超时 |
| `TRANSACTION_FAILED` | 500 | 事务执行失败 |
| `BATCH_TRANSACTION_FAILED` | 400 | 批量操作事务失败 |
| `DATABASE_ERROR` | 500 | 数据库内部错误 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超出速率限制 |

---

## 错误响应示例

### SQL 语法错误

```json
{
  "success": false,
  "error": {
    "code": "INVALID_SQL",
    "message": "SQL 语法错误: near \"SELEC\": syntax error",
    "details": {
      "sql": "SELEC * FROM users",
      "position": 0
    }
  },
  "meta": {
    "timestamp": "2024-01-20T10:00:00.000Z",
    "request_id": "req_abc123"
  }
}
```

### 权限不足

```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "当前 API Key 只有 query 权限，无法执行写操作",
    "details": {
      "required_permission": "execute",
      "current_permissions": ["query"]
    }
  }
}
```

### 约束冲突

```json
{
  "success": false,
  "error": {
    "code": "CONSTRAINT_VIOLATION",
    "message": "UNIQUE constraint failed: users.email",
    "details": {
      "constraint": "UNIQUE",
      "column": "email",
      "value": "existing@example.com"
    }
  }
}
```

---

## 最佳实践

### 1. 使用参数化查询

```json
// ✅ 推荐
{
  "sql": "SELECT * FROM users WHERE email = ?email",
  "params": {"email": "user@example.com"}
}

// ❌ 不推荐（SQL 注入风险）
{
  "sql": "SELECT * FROM users WHERE email = 'user@example.com'"
}
```

### 2. 批量操作使用事务

```json
// ✅ 使用 batch API 保证原子性
POST /api/v1/d1/production-db/batch

// ❌ 多次独立请求（无法保证一致性）
POST /api/v1/d1/production-db/execute (多次)
```

### 3. 分页大数据集

```json
// ✅ 使用 limit 和 offset
{
  "sql": "SELECT * FROM users ORDER BY id",
  "limit": 100,
  "offset": 0
}

// ❌ 一次获取所有数据
{
  "sql": "SELECT * FROM users"  // 可能导致超时或内存问题
}
```

### 4. 索引优化

```json
// ✅ 为常用查询字段创建索引
POST /api/v1/d1/production-db/tables
{
  "name": "users",
  "schema": {
    "columns": [...],
    "indexes": [
      {"name": "idx_email", "columns": ["email"], "unique": true}
    ]
  }
}
```

### 5. 错误处理

```javascript
// 客户端应该处理所有可能的错误
try {
  const response = await fetch('/api/v1/d1/production-db/query', {...});
  const data = await response.json();
  
  if (!data.success) {
    switch (data.error.code) {
      case 'DATABASE_NOT_FOUND':
        // 处理数据库不存在
        break;
      case 'PERMISSION_DENIED':
        // 处理权限不足
        break;
      default:
        // 处理其他错误
    }
  }
} catch (error) {
  // 处理网络错误
}
```
