"""Test suite for R2 Manager."""

import pytest
import sys
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from r2_manager import R2Manager


class MockR2Bucket:
    """Mock R2 bucket for testing."""
    
    async def put(self, key: str, data: bytes, options=None):
        """Mock put method."""
        return {"success": True}
    
    async def get(self, key: str):
        """Mock get method."""
        return MockR2Object()
    
    async def delete(self, key: str):
        """Mock delete method."""
        return {"success": True}
    
    async def list(self, options=None):
        """Mock list method."""
        return {
            "objects": [
                {"key": "file1.txt", "size": 100, "uploaded": "2024-12-08T00:00:00Z"},
                {"key": "file2.txt", "size": 200, "uploaded": "2024-12-08T00:00:00Z"}
            ],
            "truncated": False
        }


class MockR2Object:
    """Mock R2 object for testing."""
    
    def __init__(self):
        self.httpMetadata = {"contentType": "text/plain"}
    
    async def arrayBuffer(self):
        """Mock arrayBuffer method."""
        return b"test data"


@pytest.mark.asyncio
async def test_r2_upload():
    """Test R2 upload operation."""
    bucket = MockR2Bucket()
    manager = R2Manager(bucket)
    
    result = await manager.upload("test.txt", b"content", "text/plain")
    
    assert result["success"] is True


@pytest.mark.asyncio
async def test_r2_download():
    """Test R2 download operation."""
    bucket = MockR2Bucket()
    manager = R2Manager(bucket)
    
    result = await manager.download("test.txt")
    
    assert result["success"] is True
    assert result["size"] > 0


@pytest.mark.asyncio
async def test_r2_list():
    """Test R2 list operation."""
    bucket = MockR2Bucket()
    manager = R2Manager(bucket)
    
    result = await manager.list_objects()
    
    assert result["success"] is True
    assert result["count"] > 0
