"""Test suite for D1 Manager."""

import pytest
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from d1_manager import D1Manager


class MockD1:
    """Mock D1 database for testing."""
    
    async def prepare(self, sql: str):
        """Mock prepare method."""
        return MockStatement()
    
    async def run(self):
        """Mock run method."""
        return {"meta": {"changes": 1, "last_row_id": 1}}


class MockStatement:
    """Mock D1 statement for testing."""
    
    def bind(self, *args):
        """Mock bind method."""
        return self
    
    async def all(self):
        """Mock all method."""
        return [{"id": 1, "name": "test"}]
    
    async def run(self):
        """Mock run method."""
        return {"meta": {"changes": 1, "last_row_id": 1}}


@pytest.mark.asyncio
async def test_d1_query():
    """Test D1 query operation."""
    db = MockD1()
    manager = D1Manager(db)
    
    result = await manager.query("SELECT * FROM users")
    
    assert result["success"] is True
    assert len(result["data"]) > 0


@pytest.mark.asyncio
async def test_d1_execute():
    """Test D1 execute operation."""
    db = MockD1()
    manager = D1Manager(db)
    
    result = await manager.execute("INSERT INTO users (name) VALUES (?)", ["test"])
    
    assert result["success"] is True
    assert result["changes"] >= 0
