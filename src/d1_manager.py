"""D1 Database management module."""

from typing import Any, Dict, List, Optional


class D1Manager:
    """Manager for Cloudflare D1 Database operations.
    
    D1 绑定通过 Worker 环境传入。
    """
    
    def __init__(self, db):
        """Initialize D1 Manager.
        
        Args:
            db: D1 database binding from Cloudflare Worker environment
        """
        self.db = db
    
    async def query(self, sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute a query against D1.
        
        Args:
            sql: SQL query string
            params: Query parameters for parameterized queries
            
        Returns:
            Query result as dictionary
        """
        try:
            stmt = await self.db.prepare(sql)
            if params:
                result = await stmt.bind(*params).all()
            else:
                result = await stmt.all()
            
            return {
                "success": True,
                "data": result,
                "count": len(result) if result else 0
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute(self, sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """Execute a write operation against D1.
        
        Args:
            sql: SQL query string
            params: Query parameters for parameterized queries
            
        Returns:
            Execution result
        """
        try:
            stmt = await self.db.prepare(sql)
            if params:
                result = await stmt.bind(*params).run()
            else:
                result = await stmt.run()
            
            return {
                "success": True,
                "changes": result.get("meta", {}).get("changes", 0),
                "last_row_id": result.get("meta", {}).get("last_row_id")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_table(self, table_name: str, schema: str) -> Dict[str, Any]:
        """Create a new table in D1.
        
        Args:
            table_name: Name of the table to create
            schema: Table schema definition
            
        Returns:
            Creation result
        """
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({schema})"
        return await self.execute(sql)
    
    async def get_tables(self) -> Dict[str, Any]:
        """Get list of all tables in D1.
        
        Returns:
            List of table names
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table'"
        return await self.query(sql)
