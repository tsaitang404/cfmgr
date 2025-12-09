"""D1 Database management module.

提供对 Cloudflare D1 数据库的完整管理功能，包括查询、执行、批量操作、
表管理和数据导入导出。支持参数化查询防止 SQL 注入。
"""

import json
import time
from typing import Any


class D1Manager:
    """Manager for Cloudflare D1 Database operations.

    支持多数据库管理，提供查询、执行、批量操作、表管理等功能。
    """

    def __init__(self, databases: dict[str, Any]):
        """Initialize D1 Manager.

        Args:
            databases: D1 database bindings 字典 {database_name: db_binding}
                      从 Cloudflare Worker 环境传入
        """
        self.databases = databases

    def get_database(self, database_name: str) -> Any | None:
        """获取指定的数据库绑定.

        Args:
            database_name: 数据库名称

        Returns:
            数据库绑定对象，如果不存在返回 None
        """
        return self.databases.get(database_name)

    def list_databases(self) -> list[str]:
        """列出所有可用的数据库.

        Returns:
            数据库名称列表
        """
        return list(self.databases.keys())

    async def query(
        self,
        database_name: str,
        sql: str,
        params: dict[str, Any] | list[Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        """执行 SELECT 查询.

        Args:
            database_name: 数据库名称
            sql: SQL 查询语句（仅支持 SELECT）
            params: 参数化查询的参数，支持命名参数（dict）或位置参数（list）
            limit: 返回结果数量限制（默认 100，最大 10000）
            offset: 偏移量，用于分页

        Returns:
            查询结果字典，包含 results 和 meta 信息

        Raises:
            ValueError: 当数据库不存在或 SQL 不是 SELECT 语句时
        """
        db = self.get_database(database_name)
        if not db:
            raise ValueError(f"Database '{database_name}' not found")

        # 验证是否为读取操作（SELECT 或 PRAGMA）
        sql_upper = sql.strip().upper()
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("PRAGMA")):
            raise ValueError("Only SELECT and PRAGMA queries are allowed in query()")

        # 应用 limit 和 offset
        if limit is not None:
            limit = min(limit, 10000)  # 最大 10000
            sql = f"{sql} LIMIT {limit}"
        if offset is not None:
            sql = f"{sql} OFFSET {offset}"

        start_time = time.time()

        try:
            stmt = db.prepare(sql)

            # 处理参数化查询
            if params:
                if isinstance(params, dict):
                    # 命名参数
                    result = await stmt.bind(**params).all()
                else:
                    # 位置参数
                    result = await stmt.bind(*params).all()
            else:
                result = await stmt.all()

            duration_ms = (time.time() - start_time) * 1000

            # D1 返回的 result 可能是 JS 对象或字典
            results = []
            if result:
                if hasattr(result, "results"):
                    # JsProxy 对象，需要转换为 Python
                    js_results = result.results
                    if hasattr(js_results, "to_py"):
                        results = js_results.to_py()
                    else:
                        results = list(js_results) if js_results else []
                elif isinstance(result, dict):
                    results = result.get("results", [])

            return {
                "success": True,
                "data": {
                    "results": results,
                    "meta": {
                        "rows_read": len(results),
                        "duration_ms": round(duration_ms, 2),
                        "has_more": False,  # 可根据实际情况判断
                    },
                },
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": {
                    "code": "INVALID_SQL" if "syntax error" in str(e).lower() else "DATABASE_ERROR",
                    "message": str(e),
                    "details": {"sql": sql, "database": database_name},
                },
                "meta": {"duration_ms": round(duration_ms, 2)},
            }

    async def execute(
        self,
        database_name: str,
        sql: str,
        params: dict[str, Any] | list[Any] | None = None,
    ) -> dict[str, Any]:
        """执行写操作（INSERT, UPDATE, DELETE）.

        Args:
            database_name: 数据库名称
            sql: SQL 语句
            params: 参数化查询的参数

        Returns:
            执行结果字典，包含影响的行数等信息

        Raises:
            ValueError: 当数据库不存在或 SQL 是 SELECT 语句时
        """
        db = self.get_database(database_name)
        if not db:
            raise ValueError(f"Database '{database_name}' not found")

        # 验证不是 SELECT 语句
        if sql.strip().upper().startswith("SELECT"):
            raise ValueError("Use query() for SELECT statements")

        start_time = time.time()

        try:
            stmt = db.prepare(sql)

            # 处理参数化查询
            if params:
                if isinstance(params, dict):
                    result = await stmt.bind(**params).run()
                else:
                    result = await stmt.bind(*params).run()
            else:
                result = await stmt.run()

            duration_ms = (time.time() - start_time) * 1000
            meta = result.get("meta", {})

            return {
                "success": True,
                "data": {
                    "meta": {
                        "rows_read": meta.get("rows_read", 0),
                        "rows_written": meta.get("changes", 0),
                        "last_row_id": meta.get("last_row_id"),
                        "changes": meta.get("changes", 0),
                        "duration_ms": round(duration_ms, 2),
                    }
                },
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e).lower()

            # 判断错误类型
            if "constraint" in error_msg:
                error_code = "CONSTRAINT_VIOLATION"
            elif "syntax error" in error_msg:
                error_code = "INVALID_SQL"
            else:
                error_code = "DATABASE_ERROR"

            return {
                "success": False,
                "error": {
                    "code": error_code,
                    "message": str(e),
                    "details": {"sql": sql, "database": database_name},
                },
                "meta": {"duration_ms": round(duration_ms, 2)},
            }

    async def batch(
        self,
        database_name: str,
        statements: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """批量执行 SQL 语句（在单个事务中）.

        Args:
            database_name: 数据库名称
            statements: SQL 语句列表，每项包含 sql 和可选的 params
                       [{"sql": "...", "params": {...}}, ...]

        Returns:
            批量执行结果，包含每条语句的结果

        Raises:
            ValueError: 当数据库不存在时
        """
        db = self.get_database(database_name)
        if not db:
            raise ValueError(f"Database '{database_name}' not found")

        start_time = time.time()

        try:
            # 准备所有语句
            prepared_stmts = []
            for stmt_data in statements:
                sql = stmt_data.get("sql")
                params = stmt_data.get("params")

                stmt = db.prepare(sql)
                if params:
                    if isinstance(params, dict):
                        stmt = stmt.bind(**params)
                    else:
                        stmt = stmt.bind(*params)

                prepared_stmts.append(stmt)

            # 批量执行（事务）
            results = await db.batch(prepared_stmts)

            duration_ms = (time.time() - start_time) * 1000

            # 处理结果
            processed_results = []
            total_rows_written = 0
            successful = 0

            for result in results:
                if result:
                    meta = result.get("meta", {})
                    changes = meta.get("changes", 0)
                    total_rows_written += changes
                    successful += 1

                    processed_results.append(
                        {
                            "success": True,
                            "meta": {
                                "rows_written": changes,
                                "last_row_id": meta.get("last_row_id"),
                                "changes": changes,
                            },
                        }
                    )
                else:
                    processed_results.append({"success": False, "error": "Unknown error"})

            return {
                "success": True,
                "data": {
                    "results": processed_results,
                    "meta": {
                        "total_statements": len(statements),
                        "successful": successful,
                        "failed": len(statements) - successful,
                        "total_rows_written": total_rows_written,
                        "duration_ms": round(duration_ms, 2),
                    },
                },
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": {
                    "code": "BATCH_TRANSACTION_FAILED",
                    "message": f"批量操作失败，所有更改已回滚: {str(e)}",
                    "details": {"database": database_name, "statement_count": len(statements)},
                },
                "meta": {"duration_ms": round(duration_ms, 2)},
            }

    async def list_tables(self, database_name: str) -> dict[str, Any]:
        """列出数据库中的所有表.

        Args:
            database_name: 数据库名称

        Returns:
            表列表及元数据
        """
        sql = """
            SELECT
                name,
                type,
                sql
            FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """

        result = await self.query(database_name, sql)

        if result.get("success"):
            tables = result["data"]["results"]
            return {"success": True, "data": {"tables": tables}, "meta": {"count": len(tables)}}

        return result

    async def create_table(
        self,
        database_name: str,
        name: str,
        schema: dict[str, Any],
        if_not_exists: bool = False,
    ) -> dict[str, Any]:
        """创建新表.

        Args:
            database_name: 数据库名称
            name: 表名
            schema: 表结构定义
            if_not_exists: 如果表存在则忽略

        Returns:
            创建结果
        """
        # 构建 CREATE TABLE SQL
        columns_def = []
        for col in schema.get("columns", []):
            col_def = f"{col['name']} {col['type']}"

            if col.get("primary_key"):
                col_def += " PRIMARY KEY"
            if col.get("auto_increment"):
                col_def += " AUTOINCREMENT"
            if not col.get("nullable", True):
                col_def += " NOT NULL"
            if "default" in col:
                col_def += f" DEFAULT {col['default']}"
            if col.get("unique"):
                col_def += " UNIQUE"
            if col.get("check"):
                col_def += f" CHECK ({col['check']})"

            columns_def.append(col_def)

        # 添加约束
        for constraint in schema.get("constraints", []):
            if constraint["type"] == "UNIQUE":
                cols = ", ".join(constraint["columns"])
                columns_def.append(f"UNIQUE ({cols})")

        if_not_exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        sql = f"CREATE TABLE {if_not_exists_clause}{name} ({', '.join(columns_def)})"

        result = await self.execute(database_name, sql)

        if result.get("success"):
            # 创建索引
            for index in schema.get("indexes", []):
                index_name = index["name"]
                index_cols = ", ".join(index["columns"])
                unique = "UNIQUE " if index.get("unique") else ""
                index_sql = (
                    f"CREATE {unique}INDEX IF NOT EXISTS {index_name} ON {name} ({index_cols})"
                )
                await self.execute(database_name, index_sql)

            return {"success": True, "data": {"table": name, "created": True, "sql": sql}}

        return result

    async def get_table_info(
        self,
        database_name: str,
        table_name: str,
    ) -> dict[str, Any]:
        """获取表的详细信息.

        Args:
            database_name: 数据库名称
            table_name: 表名

        Returns:
            表结构信息
        """
        # 获取表结构
        pragma_sql = f"PRAGMA table_info({table_name})"
        columns_result = await self.query(database_name, pragma_sql)

        if not columns_result.get("success"):
            return columns_result

        # 获取索引信息
        index_sql = f"PRAGMA index_list({table_name})"
        indexes_result = await self.query(database_name, index_sql)

        # 获取表的创建 SQL
        sql_query = f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        sql_result = await self.query(database_name, sql_query)

        # 获取行数估计（可能较慢）
        count_sql = f"SELECT COUNT(*) as count FROM {table_name}"
        count_result = await self.query(database_name, count_sql)
        row_count = (
            count_result["data"]["results"][0]["count"] if count_result.get("success") else 0
        )

        return {
            "success": True,
            "data": {
                "name": table_name,
                "type": "table",
                "columns": columns_result["data"]["results"],
                "indexes": (
                    indexes_result["data"]["results"] if indexes_result.get("success") else []
                ),
                "row_count": row_count,
                "sql": (
                    sql_result["data"]["results"][0]["sql"]
                    if sql_result.get("success") and sql_result["data"]["results"]
                    else None
                ),
            },
        }

    async def get_table_indexes(
        self,
        database_name: str,
        table_name: str,
    ) -> dict[str, Any]:
        """获取表的索引信息.

        Args:
            database_name: 数据库名称
            table_name: 表名

        Returns:
            索引列表
        """
        # 获取索引列表
        index_list_sql = f"PRAGMA index_list({table_name})"
        result = await self.query(database_name, index_list_sql)

        if not result.get("success"):
            return result

        indexes = []
        for idx in result["data"]["results"]:
            # 获取每个索引的详细信息
            index_info_sql = f"PRAGMA index_info({idx['name']})"
            info_result = await self.query(database_name, index_info_sql)

            columns = (
                [col["name"] for col in info_result["data"]["results"]]
                if info_result.get("success")
                else []
            )

            indexes.append(
                {
                    "name": idx["name"],
                    "unique": bool(idx["unique"]),
                    "columns": columns,
                    "partial": bool(idx.get("partial", 0)),
                }
            )

        return {
            "success": True,
            "data": {"table": table_name, "indexes": indexes},
            "meta": {"count": len(indexes)},
        }

    async def delete_table(
        self,
        database_name: str,
        table_name: str,
    ) -> dict[str, Any]:
        """删除表.

        Args:
            database_name: 数据库名称
            table_name: 表名

        Returns:
            删除结果
        """
        sql = f"DROP TABLE IF EXISTS {table_name}"
        result = await self.execute(database_name, sql)

        if result.get("success"):
            return {"success": True, "data": {"table": table_name, "deleted": True}}

        return result

    async def export_data(
        self,
        database_name: str,
        tables: list[str] | None = None,
        format: str = "sql",
        include_schema: bool = True,
    ) -> dict[str, Any]:
        """导出数据.

        Args:
            database_name: 数据库名称
            tables: 要导出的表名列表（None 表示所有表）
            format: 导出格式（sql, json, csv）
            include_schema: 是否包含表结构

        Returns:
            导出的数据
        """
        # 获取要导出的表
        if tables is None:
            tables_result = await self.list_tables(database_name)
            if not tables_result.get("success"):
                return tables_result
            tables = [t["name"] for t in tables_result["data"]["tables"]]

        if format == "json":
            # JSON 格式导出
            exported_data = {}
            total_rows = 0

            for table in tables:
                result = await self.query(database_name, f"SELECT * FROM {table}")
                if result.get("success"):
                    rows = result["data"]["results"]
                    exported_data[table] = rows
                    total_rows += len(rows)

            return {
                "success": True,
                "data": {"format": "json", "tables": exported_data, "row_count": total_rows},
            }

        elif format == "sql":
            # SQL 格式导出
            sql_statements = []
            total_rows = 0

            for table in tables:
                # 包含表结构
                if include_schema:
                    schema_result = await self.get_table_info(database_name, table)
                    if schema_result.get("success") and schema_result["data"]["sql"]:
                        sql_statements.append(f"{schema_result['data']['sql']};")

                # 导出数据
                result = await self.query(database_name, f"SELECT * FROM {table}")
                if result.get("success"):
                    rows = result["data"]["results"]
                    total_rows += len(rows)

                    for row in rows:
                        cols = ", ".join(row.keys())
                        values = ", ".join(
                            [f"'{v}'" if isinstance(v, str) else str(v) for v in row.values()]
                        )
                        sql_statements.append(f"INSERT INTO {table} ({cols}) VALUES ({values});")

            content = "\n".join(sql_statements)

            return {
                "success": True,
                "data": {
                    "format": "sql",
                    "content": content,
                    "tables": tables,
                    "row_count": total_rows,
                },
            }

        return {
            "success": False,
            "error": {"code": "INVALID_FORMAT", "message": f"Unsupported export format: {format}"},
        }

    async def import_data(
        self,
        database_name: str,
        format: str,
        content: str,
        table: str | None = None,
        truncate: bool = False,
    ) -> dict[str, Any]:
        """导入数据.

        Args:
            database_name: 数据库名称
            format: 数据格式（sql, json）
            content: 导入内容
            table: 目标表名（JSON 格式必需）
            truncate: 导入前是否清空表

        Returns:
            导入结果
        """
        start_time = time.time()

        if format == "sql":
            # SQL 格式导入
            statements = [s.strip() for s in content.split(";") if s.strip()]

            # 使用批量操作
            batch_stmts = [{"sql": sql} for sql in statements]
            result = await self.batch(database_name, batch_stmts)

            duration_ms = (time.time() - start_time) * 1000

            if result.get("success"):
                return {
                    "success": True,
                    "data": {
                        "format": "sql",
                        "rows_imported": result["data"]["meta"]["total_rows_written"],
                        "duration_ms": round(duration_ms, 2),
                    },
                }
            return result

        elif format == "json":
            if not table:
                return {
                    "success": False,
                    "error": {
                        "code": "MISSING_PARAMETER",
                        "message": "Table name is required for JSON import",
                    },
                }

            # 清空表
            if truncate:
                await self.execute(database_name, f"DELETE FROM {table}")

            # 解析 JSON
            try:
                data = json.loads(content)
                if not isinstance(data, list):
                    data = [data]
            except json.JSONDecodeError as e:
                return {"success": False, "error": {"code": "INVALID_JSON", "message": str(e)}}

            # 批量插入
            statements = []
            for row in data:
                cols = ", ".join(row.keys())
                placeholders = ", ".join([f"?{i+1}" for i in range(len(row))])
                sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
                statements.append({"sql": sql, "params": list(row.values())})

            result = await self.batch(database_name, statements)
            duration_ms = (time.time() - start_time) * 1000

            if result.get("success"):
                return {
                    "success": True,
                    "data": {
                        "format": "json",
                        "rows_imported": result["data"]["meta"]["total_rows_written"],
                        "duration_ms": round(duration_ms, 2),
                    },
                }
            return result

        return {
            "success": False,
            "error": {"code": "INVALID_FORMAT", "message": f"Unsupported import format: {format}"},
        }
