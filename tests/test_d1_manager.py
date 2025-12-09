"""Test suite for D1 Manager.

测试 D1Manager 的所有功能，包括：
- 数据库管理
- 查询操作
- 执行操作
- 批量操作
- 表管理
- 数据导入导出
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from d1_manager import D1Manager


class MockStatement:
    """Mock D1 statement for testing."""

    def __init__(self, sql: str, return_data: Any | None = None):
        """初始化 Mock Statement.

        Args:
            sql: SQL 语句
            return_data: 返回的数据
        """
        self.sql = sql
        self.return_data = return_data or []
        self.bound_params = None

    def bind(self, *args, **kwargs):
        """Mock bind method."""
        self.bound_params = {"args": args, "kwargs": kwargs}
        return self

    async def all(self):
        """Mock all method for SELECT queries."""
        if isinstance(self.return_data, Exception):
            raise self.return_data
        return {"results": self.return_data}

    async def run(self):
        """Mock run method for write operations."""
        if isinstance(self.return_data, Exception):
            raise self.return_data
        return {
            "meta": {
                "changes": 1,
                "last_row_id": 1,
                "rows_read": 0,
            }
        }


class MockD1Database:
    """Mock D1 database for testing."""

    def __init__(self, name: str = "test-db"):
        """初始化 Mock Database.

        Args:
            name: 数据库名称
        """
        self.name = name
        self.query_results = {}
        self.execute_results = {}
        self.should_fail = False
        self.fail_message = "Database error"

    def prepare(self, sql: str):
        """Mock prepare method."""
        if self.should_fail:
            return MockStatement(sql, Exception(self.fail_message))

        # 标准化 SQL（去除多余空格）
        normalized_sql = " ".join(sql.split())

        # 根据 SQL 类型返回不同的结果
        if sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("PRAGMA"):
            # 尝试精确匹配
            result = self.query_results.get(sql)
            if result is None:
                # 尝试标准化匹配
                result = self.query_results.get(normalized_sql)
            if result is None:
                # 尝试模糊匹配（用于测试）
                for key in self.query_results:
                    if key.strip().upper() == sql.strip().upper():
                        result = self.query_results[key]
                        break
            return MockStatement(sql, result if result is not None else [])
        else:
            return MockStatement(sql, None)

    async def batch(self, statements: list[Any]):
        """Mock batch method."""
        if self.should_fail:
            raise Exception(self.fail_message)

        results = []
        for stmt in statements:
            results.append(
                {
                    "meta": {
                        "changes": 1,
                        "last_row_id": 1,
                        "rows_read": 0,
                    }
                }
            )
        return results

    def set_query_result(self, sql: str, result: list[dict[str, Any]]):
        """设置查询结果."""
        self.query_results[sql] = result

    def set_should_fail(self, fail: bool = True, message: str = "Database error"):
        """设置是否失败."""
        self.should_fail = fail
        self.fail_message = message


# ==================== 数据库管理测试 ====================


def test_init_d1_manager():
    """测试初始化 D1Manager."""
    db1 = MockD1Database("db1")
    db2 = MockD1Database("db2")
    manager = D1Manager({"db1": db1, "db2": db2})

    assert manager is not None
    assert len(manager.databases) == 2


def test_get_database():
    """测试获取数据库."""
    db1 = MockD1Database("db1")
    db2 = MockD1Database("db2")
    manager = D1Manager({"db1": db1, "db2": db2})

    # 测试获取存在的数据库
    result = manager.get_database("db1")
    assert result is not None
    assert result.name == "db1"

    # 测试获取不存在的数据库
    result = manager.get_database("db3")
    assert result is None


def test_list_databases():
    """测试列出所有数据库."""
    db1 = MockD1Database("db1")
    db2 = MockD1Database("db2")
    manager = D1Manager({"db1": db1, "db2": db2})

    databases = manager.list_databases()
    assert len(databases) == 2
    assert "db1" in databases
    assert "db2" in databases


# ==================== 查询操作测试 ====================


@pytest.mark.asyncio
async def test_query_success():
    """测试成功的查询操作."""
    db = MockD1Database("test-db")
    db.set_query_result(
        "SELECT * FROM users",
        [
            {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
            {"id": 2, "name": "李四", "email": "lisi@example.com"},
        ],
    )

    manager = D1Manager({"test-db": db})
    result = await manager.query("test-db", "SELECT * FROM users")

    assert result["success"] is True
    assert "data" in result
    assert len(result["data"]["results"]) == 2
    assert result["data"]["results"][0]["name"] == "张三"
    assert result["data"]["meta"]["rows_read"] == 2
    assert "duration_ms" in result["data"]["meta"]


@pytest.mark.asyncio
async def test_query_with_params_dict():
    """测试带命名参数的查询."""
    db = MockD1Database("test-db")
    db.set_query_result(
        "SELECT * FROM users WHERE status = ?status",
        [{"id": 1, "name": "张三", "status": "active"}],
    )

    manager = D1Manager({"test-db": db})
    result = await manager.query(
        "test-db", "SELECT * FROM users WHERE status = ?status", params={"status": "active"}
    )

    assert result["success"] is True
    assert len(result["data"]["results"]) == 1


@pytest.mark.asyncio
async def test_query_with_params_list():
    """测试带位置参数的查询."""
    db = MockD1Database("test-db")
    db.set_query_result("SELECT * FROM users WHERE id = ?", [{"id": 1, "name": "张三"}])

    manager = D1Manager({"test-db": db})
    result = await manager.query("test-db", "SELECT * FROM users WHERE id = ?", params=[1])

    assert result["success"] is True
    assert len(result["data"]["results"]) == 1


@pytest.mark.asyncio
async def test_query_with_limit():
    """测试带限制的查询."""
    db = MockD1Database("test-db")
    db.set_query_result(
        "SELECT * FROM users LIMIT 10", [{"id": i, "name": f"用户{i}"} for i in range(10)]
    )

    manager = D1Manager({"test-db": db})
    result = await manager.query("test-db", "SELECT * FROM users", limit=10)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_query_with_limit_and_offset():
    """测试带限制和偏移的查询（分页）."""
    db = MockD1Database("test-db")
    db.set_query_result(
        "SELECT * FROM users LIMIT 10 OFFSET 20",
        [{"id": i, "name": f"用户{i}"} for i in range(20, 30)],
    )

    manager = D1Manager({"test-db": db})
    result = await manager.query("test-db", "SELECT * FROM users", limit=10, offset=20)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_query_database_not_found():
    """测试查询不存在的数据库."""
    manager = D1Manager({})

    with pytest.raises(ValueError, match="Database 'nonexistent' not found"):
        await manager.query("nonexistent", "SELECT * FROM users")


@pytest.mark.asyncio
async def test_query_non_select_sql():
    """测试查询操作中使用非 SELECT 语句."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    with pytest.raises(ValueError, match="Only SELECT and PRAGMA queries are allowed"):
        await manager.query("test-db", "INSERT INTO users (name) VALUES ('test')")


@pytest.mark.asyncio
async def test_query_sql_error():
    """测试查询 SQL 错误."""
    db = MockD1Database("test-db")
    db.set_should_fail(True, "syntax error in SQL")

    manager = D1Manager({"test-db": db})
    result = await manager.query("test-db", "SELECT * FROM users")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_SQL"
    assert "syntax error" in result["error"]["message"]


# ==================== 执行操作测试 ====================


@pytest.mark.asyncio
async def test_execute_insert():
    """测试插入操作."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    result = await manager.execute(
        "test-db",
        "INSERT INTO users (name, email) VALUES (?, ?)",
        params=["张三", "zhangsan@example.com"],
    )

    assert result["success"] is True
    assert result["data"]["meta"]["rows_written"] == 1
    assert result["data"]["meta"]["last_row_id"] == 1
    assert "duration_ms" in result["data"]["meta"]


@pytest.mark.asyncio
async def test_execute_update():
    """测试更新操作."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    result = await manager.execute(
        "test-db",
        "UPDATE users SET status = ?status WHERE id = ?id",
        params={"status": "inactive", "id": 1},
    )

    assert result["success"] is True
    assert result["data"]["meta"]["changes"] == 1


@pytest.mark.asyncio
async def test_execute_delete():
    """测试删除操作."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    result = await manager.execute("test-db", "DELETE FROM users WHERE id = ?", params=[1])

    assert result["success"] is True


@pytest.mark.asyncio
async def test_execute_database_not_found():
    """测试执行操作中数据库不存在."""
    manager = D1Manager({})

    with pytest.raises(ValueError, match="Database 'nonexistent' not found"):
        await manager.execute("nonexistent", "INSERT INTO users (name) VALUES ('test')")


@pytest.mark.asyncio
async def test_execute_select_sql():
    """测试执行操作中使用 SELECT 语句."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    with pytest.raises(ValueError, match="Use query\\(\\) for SELECT statements"):
        await manager.execute("test-db", "SELECT * FROM users")


@pytest.mark.asyncio
async def test_execute_constraint_error():
    """测试约束错误."""
    db = MockD1Database("test-db")
    db.set_should_fail(True, "UNIQUE constraint failed: users.email")

    manager = D1Manager({"test-db": db})
    result = await manager.execute(
        "test-db", "INSERT INTO users (email) VALUES (?)", params=["duplicate@example.com"]
    )

    assert result["success"] is False
    assert result["error"]["code"] == "CONSTRAINT_VIOLATION"


@pytest.mark.asyncio
async def test_execute_syntax_error():
    """测试 SQL 语法错误."""
    db = MockD1Database("test-db")
    db.set_should_fail(True, "syntax error near 'INSRT'")

    manager = D1Manager({"test-db": db})
    result = await manager.execute("test-db", "INSRT INTO users (name) VALUES ('test')")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_SQL"


# ==================== 批量操作测试 ====================


@pytest.mark.asyncio
async def test_batch_success():
    """测试批量操作成功."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    statements = [
        {"sql": "INSERT INTO users (name) VALUES (?)", "params": ["用户1"]},
        {"sql": "INSERT INTO users (name) VALUES (?)", "params": ["用户2"]},
        {"sql": "INSERT INTO users (name) VALUES (?)", "params": ["用户3"]},
    ]

    result = await manager.batch("test-db", statements)

    assert result["success"] is True
    assert result["data"]["meta"]["total_statements"] == 3
    assert result["data"]["meta"]["successful"] == 3
    assert result["data"]["meta"]["failed"] == 0
    assert result["data"]["meta"]["total_rows_written"] == 3


@pytest.mark.asyncio
async def test_batch_with_dict_params():
    """测试批量操作使用命名参数."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    statements = [
        {
            "sql": "INSERT INTO users (name, email) VALUES (?name, ?email)",
            "params": {"name": "张三", "email": "zhangsan@example.com"},
        },
        {
            "sql": "UPDATE users SET status = ?status WHERE id = ?id",
            "params": {"status": "active", "id": 1},
        },
    ]

    result = await manager.batch("test-db", statements)

    assert result["success"] is True
    assert result["data"]["meta"]["total_statements"] == 2


@pytest.mark.asyncio
async def test_batch_database_not_found():
    """测试批量操作中数据库不存在."""
    manager = D1Manager({})

    with pytest.raises(ValueError, match="Database 'nonexistent' not found"):
        await manager.batch("nonexistent", [{"sql": "INSERT INTO users (name) VALUES ('test')"}])


@pytest.mark.asyncio
async def test_batch_transaction_failed():
    """测试批量操作事务失败（全部回滚）."""
    db = MockD1Database("test-db")
    db.set_should_fail(True, "Transaction failed")

    manager = D1Manager({"test-db": db})

    statements = [
        {"sql": "INSERT INTO users (name) VALUES (?)", "params": ["用户1"]},
        {"sql": "INSERT INTO users (name) VALUES (?)", "params": ["用户2"]},
    ]

    result = await manager.batch("test-db", statements)

    assert result["success"] is False
    assert result["error"]["code"] == "BATCH_TRANSACTION_FAILED"
    assert "回滚" in result["error"]["message"]


# ==================== 表管理测试 ====================


@pytest.mark.asyncio
async def test_list_tables():
    """测试列出所有表."""
    db = MockD1Database("test-db")
    tables_data = [
        {"name": "users", "type": "table", "sql": "CREATE TABLE users ..."},
        {"name": "posts", "type": "table", "sql": "CREATE TABLE posts ..."},
    ]

    # 模拟查询系统表
    sql = """
            SELECT
                name,
                type,
                sql
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """
    db.set_query_result(sql, tables_data)

    manager = D1Manager({"test-db": db})
    result = await manager.list_tables("test-db")

    assert result["success"] is True
    assert len(result["data"]["tables"]) == 2
    assert result["meta"]["count"] == 2


@pytest.mark.asyncio
async def test_create_table():
    """测试创建表."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    schema = {
        "columns": [
            {"name": "id", "type": "INTEGER", "primary_key": True, "auto_increment": True},
            {"name": "name", "type": "TEXT", "nullable": False},
            {"name": "email", "type": "TEXT", "unique": True},
            {"name": "status", "type": "TEXT", "default": "'active'"},
        ],
        "indexes": [
            {"name": "idx_email", "columns": ["email"], "unique": True},
        ],
    }

    result = await manager.create_table("test-db", "users", schema)

    assert result["success"] is True
    assert result["data"]["table"] == "users"
    assert result["data"]["created"] is True


@pytest.mark.asyncio
async def test_create_table_if_not_exists():
    """测试创建表（如果不存在）."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    schema = {
        "columns": [
            {"name": "id", "type": "INTEGER", "primary_key": True},
        ]
    }

    result = await manager.create_table("test-db", "users", schema, if_not_exists=True)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_get_table_info():
    """测试获取表信息."""
    db = MockD1Database("test-db")

    # 模拟 PRAGMA table_info（添加默认返回）
    table_info_data = [
        {"cid": 0, "name": "id", "type": "INTEGER", "notnull": 0, "pk": 1},
        {"cid": 1, "name": "name", "type": "TEXT", "notnull": 1, "pk": 0},
    ]
    db.query_results = {sql: table_info_data for sql in ["PRAGMA table_info(users)"]}

    # 模拟 PRAGMA index_list
    index_list_data = [{"name": "idx_email", "unique": 1}]
    db.query_results["PRAGMA index_list(users)"] = index_list_data

    # 模拟获取创建 SQL
    sql_data = [{"sql": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"}]
    db.query_results["SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"] = sql_data

    # 模拟计数
    count_data = [{"count": 100}]
    db.query_results["SELECT COUNT(*) as count FROM users"] = count_data

    # 设置默认返回（匹配任何未明确设置的查询）
    db.query_results = {**db.query_results}

    manager = D1Manager({"test-db": db})
    result = await manager.get_table_info("test-db", "users")

    assert result["success"] is True
    assert result["data"]["name"] == "users"
    assert len(result["data"]["columns"]) == 2
    assert result["data"]["row_count"] == 100


@pytest.mark.asyncio
async def test_get_table_indexes():
    """测试获取表索引."""
    db = MockD1Database("test-db")

    # 模拟 PRAGMA index_list
    index_list_data = [
        {"name": "idx_email", "unique": 1, "partial": 0},
        {"name": "idx_status", "unique": 0, "partial": 0},
    ]
    db.query_results["PRAGMA index_list(users)"] = index_list_data

    # 模拟 PRAGMA index_info
    db.query_results["PRAGMA index_info(idx_email)"] = [{"name": "email"}]
    db.query_results["PRAGMA index_info(idx_status)"] = [{"name": "status"}]

    manager = D1Manager({"test-db": db})
    result = await manager.get_table_indexes("test-db", "users")

    assert result["success"] is True
    assert len(result["data"]["indexes"]) == 2
    assert result["meta"]["count"] == 2


@pytest.mark.asyncio
async def test_delete_table():
    """测试删除表."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    result = await manager.delete_table("test-db", "users")

    assert result["success"] is True
    assert result["data"]["table"] == "users"
    assert result["data"]["deleted"] is True


# ==================== 数据导入导出测试 ====================


@pytest.mark.asyncio
async def test_export_data_json():
    """测试 JSON 格式导出."""
    db = MockD1Database("test-db")

    # 模拟查询系统表
    db.set_query_result(
        """
            SELECT
                name,
                type,
                sql
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """,
        [{"name": "users", "type": "table", "sql": "CREATE TABLE users ..."}],
    )

    # 模拟查询表数据
    db.set_query_result(
        "SELECT * FROM users",
        [
            {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
            {"id": 2, "name": "李四", "email": "lisi@example.com"},
        ],
    )

    manager = D1Manager({"test-db": db})
    result = await manager.export_data("test-db", format="json")

    assert result["success"] is True
    assert result["data"]["format"] == "json"
    assert "users" in result["data"]["tables"]
    assert len(result["data"]["tables"]["users"]) == 2
    assert result["data"]["row_count"] == 2


@pytest.mark.asyncio
async def test_export_data_sql():
    """测试 SQL 格式导出."""
    db = MockD1Database("test-db")

    # 模拟 list_tables
    db.set_query_result(
        """
            SELECT
                name,
                type,
                sql
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """,
        [{"name": "users", "type": "table", "sql": "CREATE TABLE users ..."}],
    )

    # 模拟 get_table_info
    db.set_query_result("PRAGMA table_info(users)", [])
    db.set_query_result("PRAGMA index_list(users)", [])
    db.set_query_result(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'",
        [{"sql": "CREATE TABLE users (id INTEGER, name TEXT)"}],
    )
    db.set_query_result("SELECT COUNT(*) as count FROM users", [{"count": 1}])

    # 模拟查询表数据
    db.set_query_result("SELECT * FROM users", [{"id": 1, "name": "张三"}])

    manager = D1Manager({"test-db": db})
    result = await manager.export_data("test-db", format="sql", include_schema=True)

    assert result["success"] is True
    assert result["data"]["format"] == "sql"
    assert "CREATE TABLE" in result["data"]["content"]
    assert "INSERT INTO" in result["data"]["content"]


@pytest.mark.asyncio
async def test_export_data_specific_tables():
    """测试导出指定表."""
    db = MockD1Database("test-db")

    db.set_query_result("SELECT * FROM users", [{"id": 1, "name": "张三"}])

    manager = D1Manager({"test-db": db})
    result = await manager.export_data("test-db", tables=["users"], format="json")

    assert result["success"] is True
    assert "users" in result["data"]["tables"]


@pytest.mark.asyncio
async def test_export_data_invalid_format():
    """测试无效的导出格式."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    result = await manager.export_data("test-db", format="xml")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_FORMAT"


@pytest.mark.asyncio
async def test_import_data_sql():
    """测试 SQL 格式导入."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    content = """
    INSERT INTO users (name, email) VALUES ('张三', 'zhangsan@example.com');
    INSERT INTO users (name, email) VALUES ('李四', 'lisi@example.com');
    """

    result = await manager.import_data("test-db", "sql", content)

    assert result["success"] is True
    assert result["data"]["format"] == "sql"
    assert result["data"]["rows_imported"] >= 0


@pytest.mark.asyncio
async def test_import_data_json():
    """测试 JSON 格式导入."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    data = [
        {"name": "张三", "email": "zhangsan@example.com"},
        {"name": "李四", "email": "lisi@example.com"},
    ]
    content = json.dumps(data)

    result = await manager.import_data("test-db", "json", content, table="users")

    assert result["success"] is True
    assert result["data"]["format"] == "json"


@pytest.mark.asyncio
async def test_import_data_json_missing_table():
    """测试 JSON 导入缺少表名."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    content = json.dumps([{"name": "test"}])
    result = await manager.import_data("test-db", "json", content)

    assert result["success"] is False
    assert result["error"]["code"] == "MISSING_PARAMETER"


@pytest.mark.asyncio
async def test_import_data_invalid_json():
    """测试导入无效的 JSON."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    result = await manager.import_data("test-db", "json", "invalid json", table="users")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_JSON"


@pytest.mark.asyncio
async def test_import_data_invalid_format():
    """测试无效的导入格式."""
    db = MockD1Database("test-db")
    manager = D1Manager({"test-db": db})

    result = await manager.import_data("test-db", "csv", "data", table="users")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_FORMAT"
