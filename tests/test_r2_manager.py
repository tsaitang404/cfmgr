"""Test suite for R2 Manager.

测试 R2Manager 的所有功能，包括：
- Bucket 管理
- 对象操作（上传、下载、删除、复制）
- 对象列表
- 分片上传
- 预签名 URL
"""

import base64
import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from r2_manager import R2Manager


class MockR2Object:
    """Mock R2 object for testing."""

    def __init__(
        self,
        key: str = "test.txt",
        size: int = 100,
        data: bytes = b"test data",
        content_type: str = "text/plain",
        etag: str = "abc123",
        custom_metadata: dict[str, str] | None = None,
    ):
        """初始化 Mock R2 Object.

        Args:
            key: 对象键
            size: 对象大小
            data: 对象数据
            content_type: Content-Type
            etag: ETag
            custom_metadata: 自定义元数据
        """
        self.key = key
        self.size = size
        self._data = data
        self.etag = etag
        self.uploaded = datetime.now(UTC)
        self.httpMetadata = {"contentType": content_type}
        self.customMetadata = custom_metadata or {}

    async def arrayBuffer(self):
        """Mock arrayBuffer method."""
        return self._data


class MockR2Bucket:
    """Mock R2 bucket for testing."""

    def __init__(self, name: str = "test-bucket"):
        """初始化 Mock Bucket.

        Args:
            name: Bucket 名称
        """
        self.name = name
        self.objects = {}
        self.should_fail = False
        self.fail_message = "Storage error"
        self.multipart_uploads = {}

    async def put(self, key: str, data: bytes, options: dict | None = None):
        """Mock put method."""
        if self.should_fail:
            raise Exception(self.fail_message)

        self.objects[key] = {
            "data": data,
            "options": options or {},
        }
        return {"success": True}

    async def get(self, key: str, options: dict | None = None):
        """Mock get method."""
        if self.should_fail:
            raise Exception(self.fail_message)

        if key not in self.objects:
            return None

        obj_data = self.objects[key]
        http_metadata = obj_data["options"].get("httpMetadata", {})
        custom_metadata = obj_data["options"].get("customMetadata", {})

        return MockR2Object(
            key=key,
            data=obj_data["data"],
            content_type=http_metadata.get("contentType", "application/octet-stream"),
            custom_metadata=custom_metadata,
        )

    async def head(self, key: str):
        """Mock head method."""
        if key not in self.objects:
            return None
        return await self.get(key)

    async def delete(self, key: str):
        """Mock delete method."""
        if self.should_fail:
            raise Exception(self.fail_message)

        if key in self.objects:
            del self.objects[key]
        return {"success": True}

    async def list(self, options: dict | None = None):
        """Mock list method."""
        if self.should_fail:
            raise Exception(self.fail_message)

        options = options or {}
        prefix = options.get("prefix", "")
        limit = options.get("limit", 100)
        delimiter = options.get("delimiter")

        # 过滤对象
        filtered_objects = []
        common_prefixes = set()

        for key in self.objects.keys():
            if key.startswith(prefix):
                if delimiter:
                    # 模拟目录结构
                    remainder = key[len(prefix) :]
                    if delimiter in remainder:
                        # 这是一个子目录
                        prefix_end = remainder.index(delimiter) + 1
                        common_prefixes.add(prefix + remainder[:prefix_end])
                    else:
                        # 这是当前目录的文件
                        filtered_objects.append(key)
                else:
                    filtered_objects.append(key)

        # 构建返回对象
        objects = []
        for key in filtered_objects[:limit]:
            obj_data = self.objects[key]
            http_metadata = obj_data["options"].get("httpMetadata", {})
            custom_metadata = obj_data["options"].get("customMetadata", {})

            obj_info = {
                "key": key,
                "size": len(obj_data["data"]),
                "uploaded": datetime.now(UTC),
                "etag": hashlib.md5(obj_data["data"]).hexdigest(),
            }

            if http_metadata:
                obj_info["httpMetadata"] = http_metadata
            if custom_metadata:
                obj_info["customMetadata"] = custom_metadata

            objects.append(obj_info)

        return {
            "objects": objects,
            "truncated": len(filtered_objects) > limit,
            "delimitedPrefixes": list(common_prefixes) if delimiter else [],
            "cursor": None,
        }

    async def createMultipartUpload(self, key: str, options: dict | None = None):
        """Mock createMultipartUpload method."""
        if self.should_fail:
            raise Exception(self.fail_message)

        upload_id = f"upload_{key}_{len(self.multipart_uploads)}"
        self.multipart_uploads[upload_id] = {
            "key": key,
            "options": options or {},
            "parts": {},
        }

        mock_multipart = MagicMock()
        mock_multipart.uploadId = upload_id
        return mock_multipart

    async def resumeMultipartUpload(self, key: str, upload_id: str):
        """Mock resumeMultipartUpload method."""
        if upload_id not in self.multipart_uploads:
            raise Exception(f"Upload not found: {upload_id}")

        mock_multipart = MagicMock()
        mock_multipart.uploadId = upload_id

        # Mock uploadPart
        async def upload_part(part_number: int, data: bytes):
            self.multipart_uploads[upload_id]["parts"][part_number] = data
            return {"success": True}

        mock_multipart.uploadPart = upload_part

        # Mock complete
        async def complete(parts: list[dict]):
            upload_info = self.multipart_uploads[upload_id]
            # 合并所有分片
            all_data = b""
            for part_info in sorted(parts, key=lambda x: x["part_number"]):
                part_num = part_info["part_number"]
                if part_num in upload_info["parts"]:
                    all_data += upload_info["parts"][part_num]

            # 保存完整对象
            key = upload_info["key"]
            self.objects[key] = {
                "data": all_data,
                "options": upload_info["options"],
            }

            result = MagicMock()
            result.etag = hashlib.md5(all_data).hexdigest()
            return result

        mock_multipart.complete = complete

        # Mock abort
        async def abort():
            if upload_id in self.multipart_uploads:
                del self.multipart_uploads[upload_id]

        mock_multipart.abort = abort

        return mock_multipart

    def set_should_fail(self, fail: bool = True, message: str = "Storage error"):
        """设置是否失败."""
        self.should_fail = fail
        self.fail_message = message


# ==================== Bucket 管理测试 ====================


def test_init_r2_manager():
    """测试初始化 R2Manager."""
    bucket1 = MockR2Bucket("bucket1")
    bucket2 = MockR2Bucket("bucket2")
    manager = R2Manager({"bucket1": bucket1, "bucket2": bucket2})

    assert manager is not None
    assert len(manager.buckets) == 2


def test_get_bucket():
    """测试获取 bucket."""
    bucket1 = MockR2Bucket("bucket1")
    bucket2 = MockR2Bucket("bucket2")
    manager = R2Manager({"bucket1": bucket1, "bucket2": bucket2})

    # 测试获取存在的 bucket
    result = manager.get_bucket("bucket1")
    assert result is not None
    assert result.name == "bucket1"

    # 测试获取不存在的 bucket
    result = manager.get_bucket("bucket3")
    assert result is None


def test_list_buckets():
    """测试列出所有 buckets."""
    bucket1 = MockR2Bucket("bucket1")
    bucket2 = MockR2Bucket("bucket2")
    manager = R2Manager({"bucket1": bucket1, "bucket2": bucket2})

    buckets = manager.list_buckets()
    assert len(buckets) == 2
    assert "bucket1" in buckets
    assert "bucket2" in buckets


# ==================== 对象上传测试 ====================


@pytest.mark.asyncio
async def test_upload_success():
    """测试成功上传对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.upload(
        "test-bucket", "images/photo.jpg", b"image data", content_type="image/jpeg"
    )

    assert result["success"] is True
    assert result["data"]["bucket"] == "test-bucket"
    assert result["data"]["key"] == "images/photo.jpg"
    assert result["data"]["size"] == 10
    assert result["data"]["content_type"] == "image/jpeg"
    assert "etag" in result["data"]
    assert "uploaded_at" in result["data"]
    assert "duration_ms" in result["meta"]


@pytest.mark.asyncio
async def test_upload_with_string():
    """测试上传字符串数据."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.upload(
        "test-bucket", "notes/readme.txt", "Hello, World!", content_type="text/plain"
    )

    assert result["success"] is True
    assert result["data"]["size"] == 13


@pytest.mark.asyncio
async def test_upload_with_custom_metadata():
    """测试上传带自定义元数据的对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.upload(
        "test-bucket",
        "docs/file.pdf",
        b"pdf content",
        custom_metadata={"user_id": "123", "version": "1.0"},
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_upload_with_cache_control():
    """测试上传带缓存控制的对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.upload(
        "test-bucket",
        "static/style.css",
        b"body { margin: 0; }",
        cache_control="public, max-age=3600",
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_upload_with_md5_valid():
    """测试上传带有效 MD5 校验的对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    data = b"test data"
    md5_hash = base64.b64encode(hashlib.md5(data).digest()).decode()

    result = await manager.upload("test-bucket", "test.txt", data, content_md5=md5_hash)

    assert result["success"] is True


@pytest.mark.asyncio
async def test_upload_with_md5_invalid():
    """测试上传带无效 MD5 校验的对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.upload(
        "test-bucket", "test.txt", b"test data", content_md5="invalid_md5"
    )

    assert result["success"] is False
    assert result["error"]["code"] == "CHECKSUM_MISMATCH"


@pytest.mark.asyncio
async def test_upload_bucket_not_found():
    """测试上传到不存在的 bucket."""
    manager = R2Manager({})

    with pytest.raises(ValueError, match="Bucket 'nonexistent' not found"):
        await manager.upload("nonexistent", "test.txt", b"data")


@pytest.mark.asyncio
async def test_upload_storage_error():
    """测试上传存储错误."""
    bucket = MockR2Bucket("test-bucket")
    bucket.set_should_fail(True, "Storage service unavailable")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.upload("test-bucket", "test.txt", b"data")

    assert result["success"] is False
    assert result["error"]["code"] == "STORAGE_ERROR"


# ==================== 对象下载测试 ====================


@pytest.mark.asyncio
async def test_download_success():
    """测试成功下载对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    # 先上传一个对象
    await manager.upload("test-bucket", "test.txt", b"test data", content_type="text/plain")

    # 下载对象
    result = await manager.download("test-bucket", "test.txt")

    assert result["success"] is True
    assert result["data"]["bucket"] == "test-bucket"
    assert result["data"]["key"] == "test.txt"
    assert result["data"]["data"] == b"test data"
    assert result["data"]["content_type"] == "text/plain"
    assert "etag" in result["data"]
    assert "duration_ms" in result["meta"]


@pytest.mark.asyncio
async def test_download_with_range():
    """测试 Range 请求下载."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    await manager.upload("test-bucket", "large.bin", b"0123456789" * 10)

    result = await manager.download("test-bucket", "large.bin", range_start=0, range_end=9)

    assert result["success"] is True
    assert result["meta"]["partial_content"] is True


@pytest.mark.asyncio
async def test_download_object_not_found():
    """测试下载不存在的对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.download("test-bucket", "nonexistent.txt")

    assert result["success"] is False
    assert result["error"]["code"] == "OBJECT_NOT_FOUND"


@pytest.mark.asyncio
async def test_download_bucket_not_found():
    """测试从不存在的 bucket 下载."""
    manager = R2Manager({})

    with pytest.raises(ValueError, match="Bucket 'nonexistent' not found"):
        await manager.download("nonexistent", "test.txt")


# ==================== 对象元数据测试 ====================


@pytest.mark.asyncio
async def test_get_metadata_success():
    """测试获取对象元数据."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    await manager.upload(
        "test-bucket",
        "test.txt",
        b"test data",
        content_type="text/plain",
        custom_metadata={"author": "user123"},
    )

    result = await manager.get_metadata("test-bucket", "test.txt")

    assert result["success"] is True
    assert result["data"]["key"] == "test.txt"
    assert result["data"]["size"] > 0
    assert result["data"]["content_type"] == "text/plain"
    assert result["data"]["custom_metadata"]["author"] == "user123"


@pytest.mark.asyncio
async def test_get_metadata_not_found():
    """测试获取不存在对象的元数据."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.get_metadata("test-bucket", "nonexistent.txt")

    assert result["success"] is False
    assert result["error"]["code"] == "OBJECT_NOT_FOUND"


# ==================== 对象删除测试 ====================


@pytest.mark.asyncio
async def test_delete_success():
    """测试成功删除对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    await manager.upload("test-bucket", "test.txt", b"data")

    result = await manager.delete("test-bucket", "test.txt")

    assert result["success"] is True
    assert result["data"]["deleted"] is True
    assert result["data"]["key"] == "test.txt"


@pytest.mark.asyncio
async def test_delete_bucket_not_found():
    """测试从不存在的 bucket 删除."""
    manager = R2Manager({})

    with pytest.raises(ValueError, match="Bucket 'nonexistent' not found"):
        await manager.delete("nonexistent", "test.txt")


# ==================== 对象复制测试 ====================


@pytest.mark.asyncio
async def test_copy_same_bucket():
    """测试在同一 bucket 内复制对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    await manager.upload("test-bucket", "source.txt", b"data", content_type="text/plain")

    result = await manager.copy("test-bucket", "source.txt", destination_key="backup/source.txt")

    assert result["success"] is True
    assert result["data"]["source_key"] == "source.txt"
    assert result["data"]["destination_key"] == "backup/source.txt"
    assert result["data"]["copied"] is True


@pytest.mark.asyncio
async def test_copy_cross_bucket():
    """测试跨 bucket 复制对象."""
    bucket1 = MockR2Bucket("bucket1")
    bucket2 = MockR2Bucket("bucket2")
    manager = R2Manager({"bucket1": bucket1, "bucket2": bucket2})

    await manager.upload("bucket1", "file.txt", b"data")

    result = await manager.copy(
        "bucket1", "file.txt", destination_bucket="bucket2", destination_key="copied.txt"
    )

    assert result["success"] is True
    assert result["data"]["destination_bucket"] == "bucket2"


@pytest.mark.asyncio
async def test_copy_with_metadata_replace():
    """测试复制时替换元数据."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    await manager.upload("test-bucket", "source.txt", b"data")

    result = await manager.copy(
        "test-bucket",
        "source.txt",
        destination_key="dest.txt",
        metadata_directive="REPLACE",
        custom_metadata={"version": "2"},
        cache_control="no-cache",
    )

    assert result["success"] is True


@pytest.mark.asyncio
async def test_copy_source_not_found():
    """测试复制不存在的源对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.copy("test-bucket", "nonexistent.txt", destination_key="dest.txt")

    assert result["success"] is False
    assert result["error"]["code"] == "OBJECT_NOT_FOUND"


@pytest.mark.asyncio
async def test_copy_missing_destination_key():
    """测试复制缺少目标键."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    with pytest.raises(ValueError, match="destination_key is required"):
        await manager.copy("test-bucket", "source.txt", destination_key=None)


# ==================== 对象列表测试 ====================


@pytest.mark.asyncio
async def test_list_objects_basic():
    """测试基本列表对象."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    # 上传一些对象
    await manager.upload("test-bucket", "file1.txt", b"data1")
    await manager.upload("test-bucket", "file2.txt", b"data2")
    await manager.upload("test-bucket", "dir/file3.txt", b"data3")

    result = await manager.list_objects("test-bucket")

    assert result["success"] is True
    assert result["meta"]["count"] == 3
    assert len(result["data"]["objects"]) == 3


@pytest.mark.asyncio
async def test_list_objects_with_prefix():
    """测试带前缀过滤的列表."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    await manager.upload("test-bucket", "images/photo1.jpg", b"data1")
    await manager.upload("test-bucket", "images/photo2.jpg", b"data2")
    await manager.upload("test-bucket", "docs/readme.txt", b"data3")

    result = await manager.list_objects("test-bucket", prefix="images/")

    assert result["success"] is True
    assert result["data"]["prefix"] == "images/"
    assert result["meta"]["count"] == 2


@pytest.mark.asyncio
async def test_list_objects_with_delimiter():
    """测试带分隔符的列表（目录模拟）."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    await manager.upload("test-bucket", "root.txt", b"data")
    await manager.upload("test-bucket", "dir1/file1.txt", b"data")
    await manager.upload("test-bucket", "dir2/file2.txt", b"data")

    result = await manager.list_objects("test-bucket", delimiter="/")

    assert result["success"] is True
    assert result["data"]["delimiter"] == "/"
    assert len(result["data"]["common_prefixes"]) > 0


@pytest.mark.asyncio
async def test_list_objects_with_limit():
    """测试带限制的列表."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    for i in range(10):
        await manager.upload("test-bucket", f"file{i}.txt", b"data")

    result = await manager.list_objects("test-bucket", limit=5)

    assert result["success"] is True
    assert result["meta"]["count"] <= 5


@pytest.mark.asyncio
async def test_list_objects_with_metadata():
    """测试包含元数据的列表."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    await manager.upload("test-bucket", "test.txt", b"data", custom_metadata={"key": "value"})

    result = await manager.list_objects("test-bucket", include_metadata=True)

    assert result["success"] is True
    if result["meta"]["count"] > 0:
        obj = result["data"]["objects"][0]
        assert "size_human" in obj


@pytest.mark.asyncio
async def test_list_objects_bucket_not_found():
    """测试列出不存在的 bucket."""
    manager = R2Manager({})

    with pytest.raises(ValueError, match="Bucket 'nonexistent' not found"):
        await manager.list_objects("nonexistent")


# ==================== 分片上传测试 ====================


@pytest.mark.asyncio
async def test_create_multipart_upload():
    """测试初始化分片上传."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.create_multipart_upload(
        "test-bucket", "large-file.bin", content_type="application/octet-stream"
    )

    assert result["success"] is True
    assert "upload_id" in result["data"]
    assert result["data"]["key"] == "large-file.bin"


@pytest.mark.asyncio
async def test_upload_part():
    """测试上传分片."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    # 初始化分片上传
    init_result = await manager.create_multipart_upload("test-bucket", "file.bin")
    upload_id = init_result["data"]["upload_id"]

    # 上传分片
    result = await manager.upload_part("test-bucket", "file.bin", upload_id, 1, b"part 1 data")

    assert result["success"] is True
    assert result["data"]["part_number"] == 1
    assert "etag" in result["data"]


@pytest.mark.asyncio
async def test_upload_part_invalid_number():
    """测试上传无效分片号."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    init_result = await manager.create_multipart_upload("test-bucket", "file.bin")
    upload_id = init_result["data"]["upload_id"]

    # 分片号为 0（无效）
    result = await manager.upload_part("test-bucket", "file.bin", upload_id, 0, b"data")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PART"

    # 分片号超过 10000（无效）
    result = await manager.upload_part("test-bucket", "file.bin", upload_id, 10001, b"data")

    assert result["success"] is False
    assert result["error"]["code"] == "INVALID_PART"


@pytest.mark.asyncio
async def test_upload_part_not_found():
    """测试上传到不存在的上传 ID."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    result = await manager.upload_part("test-bucket", "file.bin", "invalid_upload_id", 1, b"data")

    assert result["success"] is False
    assert result["error"]["code"] == "UPLOAD_NOT_FOUND"


@pytest.mark.asyncio
async def test_complete_multipart_upload():
    """测试完成分片上传."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    # 初始化
    init_result = await manager.create_multipart_upload("test-bucket", "file.bin")
    upload_id = init_result["data"]["upload_id"]

    # 上传两个分片
    part1 = await manager.upload_part("test-bucket", "file.bin", upload_id, 1, b"part1")
    part2 = await manager.upload_part("test-bucket", "file.bin", upload_id, 2, b"part2")

    # 完成上传
    parts = [
        {"part_number": 1, "etag": part1["data"]["etag"]},
        {"part_number": 2, "etag": part2["data"]["etag"]},
    ]

    result = await manager.complete_multipart_upload("test-bucket", "file.bin", upload_id, parts)

    assert result["success"] is True
    assert result["data"]["size"] == 10  # "part1" + "part2"


@pytest.mark.asyncio
async def test_abort_multipart_upload():
    """测试取消分片上传."""
    bucket = MockR2Bucket("test-bucket")
    manager = R2Manager({"test-bucket": bucket})

    # 初始化
    init_result = await manager.create_multipart_upload("test-bucket", "file.bin")
    upload_id = init_result["data"]["upload_id"]

    # 取消上传
    result = await manager.abort_multipart_upload("test-bucket", "file.bin", upload_id)

    assert result["success"] is True
    assert result["data"]["aborted"] is True

    # 验证上传 ID 已清理
    assert upload_id not in manager.multipart_uploads


# ==================== 辅助方法测试 ====================


def test_format_size():
    """测试格式化文件大小."""
    manager = R2Manager({})

    assert manager._format_size(100) == "100.0 B"
    assert manager._format_size(1024) == "1.0 KB"
    assert manager._format_size(1024 * 1024) == "1.0 MB"
    assert manager._format_size(1024 * 1024 * 1024) == "1.0 GB"
    assert manager._format_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"


def test_generate_presigned_url_success():
    """测试生成预签名 URL."""
    manager = R2Manager({})

    result = manager.generate_presigned_url(
        "test-bucket", "file.txt", method="GET", expires_in=3600, secret_key="my-secret-key"
    )

    assert result["success"] is True
    assert "url" in result["data"]
    assert result["data"]["method"] == "GET"
    assert result["data"]["expires_in"] == 3600


def test_generate_presigned_url_no_secret():
    """测试生成预签名 URL 缺少密钥."""
    manager = R2Manager({})

    result = manager.generate_presigned_url("test-bucket", "file.txt", secret_key=None)

    assert result["success"] is False
    assert result["error"]["code"] == "MISSING_SECRET_KEY"


def test_generate_presigned_url_max_expiry():
    """测试预签名 URL 最大过期时间限制."""
    manager = R2Manager({})

    result = manager.generate_presigned_url(
        "test-bucket", "file.txt", expires_in=1000000, secret_key="secret"  # 超过 7 天
    )

    assert result["success"] is True
    assert result["data"]["expires_in"] == 604800  # 最大 7 天
