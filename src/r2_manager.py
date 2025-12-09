"""R2 Object Storage management module.

提供对 Cloudflare R2 对象存储的完整管理功能，包括对象上传、下载、删除、
列表、复制、元数据管理和分片上传。支持预签名 URL 和公网访问。
"""

import base64
import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta
from typing import Any


class R2Manager:
    """Manager for Cloudflare R2 Object Storage operations.

    支持多 bucket 管理，提供对象存储、检索、列表等完整功能。
    """

    def __init__(self, buckets: dict[str, Any]):
        """Initialize R2 Manager.

        Args:
            buckets: R2 bucket bindings 字典 {bucket_name: bucket_binding}
                    从 Cloudflare Worker 环境传入
        """
        self.buckets = buckets
        self.multipart_uploads = {}  # 存储分片上传状态

    def get_bucket(self, bucket_name: str) -> Any | None:
        """获取指定的 bucket 绑定.

        Args:
            bucket_name: Bucket 名称

        Returns:
            Bucket 绑定对象，如果不存在返回 None
        """
        return self.buckets.get(bucket_name)

    def list_buckets(self) -> list[str]:
        """列出所有可用的 buckets.

        Returns:
            Bucket 名称列表
        """
        return list(self.buckets.keys())

    # ==================== 对象操作 ====================

    async def upload(
        self,
        bucket_name: str,
        key: str,
        data: bytes | str,
        content_type: str | None = None,
        custom_metadata: dict[str, str] | None = None,
        cache_control: str | None = None,
        content_md5: str | None = None,
    ) -> dict[str, Any]:
        """上传对象到 R2.

        Args:
            bucket_name: Bucket 名称
            key: 对象键/路径
            data: 文件数据（bytes 或 string）
            content_type: MIME 类型
            custom_metadata: 自定义元数据字典
            cache_control: 缓存控制头
            content_md5: MD5 校验和（base64）

        Returns:
            上传结果

        Raises:
            ValueError: 当 bucket 不存在时
        """
        bucket = self.get_bucket(bucket_name)
        if not bucket:
            raise ValueError(f"Bucket '{bucket_name}' not found")

        start_time = time.time()

        try:
            # 转换 string 为 bytes
            if isinstance(data, str):
                data = data.encode("utf-8")

            # 验证 MD5（如果提供）
            if content_md5:
                calculated_md5 = base64.b64encode(hashlib.md5(data).digest()).decode()
                if calculated_md5 != content_md5:
                    return {
                        "success": False,
                        "error": {
                            "code": "CHECKSUM_MISMATCH",
                            "message": "MD5 checksum does not match",
                            "details": {"expected": content_md5, "calculated": calculated_md5},
                        },
                    }

            # 构建选项
            options = {}

            # HTTP 元数据
            http_metadata = {}
            if content_type:
                http_metadata["contentType"] = content_type
            if cache_control:
                http_metadata["cacheControl"] = cache_control
            if http_metadata:
                options["httpMetadata"] = http_metadata

            # 自定义元数据
            if custom_metadata:
                options["customMetadata"] = custom_metadata

            # 上传对象
            await bucket.put(key, data, options)

            duration_ms = (time.time() - start_time) * 1000

            # 计算 ETag
            etag = hashlib.md5(data).hexdigest()

            return {
                "success": True,
                "data": {
                    "bucket": bucket_name,
                    "key": key,
                    "size": len(data),
                    "etag": etag,
                    "content_type": content_type,
                    "uploaded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                },
                "meta": {"duration_ms": round(duration_ms, 2)},
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e).lower()

            # 判断错误类型
            if "too large" in error_msg:
                error_code = "FILE_TOO_LARGE"
            elif "invalid" in error_msg and "key" in error_msg:
                error_code = "INVALID_KEY"
            else:
                error_code = "STORAGE_ERROR"

            return {
                "success": False,
                "error": {
                    "code": error_code,
                    "message": str(e),
                    "details": {"bucket": bucket_name, "key": key},
                },
                "meta": {"duration_ms": round(duration_ms, 2)},
            }

    async def download(
        self,
        bucket_name: str,
        key: str,
        range_start: int | None = None,
        range_end: int | None = None,
    ) -> dict[str, Any]:
        """从 R2 下载对象.

        Args:
            bucket_name: Bucket 名称
            key: 对象键/路径
            range_start: Range 请求起始位置（字节）
            range_end: Range 请求结束位置（字节）

        Returns:
            下载结果，包含对象数据和元数据

        Raises:
            ValueError: 当 bucket 不存在时
        """
        bucket = self.get_bucket(bucket_name)
        if not bucket:
            raise ValueError(f"Bucket '{bucket_name}' not found")

        start_time = time.time()

        try:
            # 构建选项
            options = {}
            if range_start is not None or range_end is not None:
                range_header = {}
                if range_start is not None:
                    range_header["offset"] = range_start
                if range_end is not None:
                    range_header["length"] = range_end - (range_start or 0) + 1
                options["range"] = range_header

            # 获取对象
            obj = await bucket.get(key, options)

            if obj is None:
                return {
                    "success": False,
                    "error": {
                        "code": "OBJECT_NOT_FOUND",
                        "message": f"Object not found: {key}",
                        "details": {"bucket": bucket_name, "key": key},
                    },
                }

            # 读取数据
            data = await obj.arrayBuffer()

            duration_ms = (time.time() - start_time) * 1000

            # 提取元数据
            http_metadata = obj.httpMetadata or {}
            custom_metadata = obj.customMetadata or {}

            return {
                "success": True,
                "data": {
                    "bucket": bucket_name,
                    "key": key,
                    "data": data,
                    "size": obj.size,
                    "etag": obj.etag,
                    "content_type": http_metadata.get("contentType"),
                    "cache_control": http_metadata.get("cacheControl"),
                    "uploaded_at": (
                        obj.uploaded.isoformat() + "Z" if hasattr(obj, "uploaded") else None
                    ),
                    "custom_metadata": custom_metadata,
                },
                "meta": {
                    "duration_ms": round(duration_ms, 2),
                    "partial_content": range_start is not None or range_end is not None,
                },
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": {
                    "code": "STORAGE_ERROR",
                    "message": str(e),
                    "details": {"bucket": bucket_name, "key": key},
                },
                "meta": {"duration_ms": round(duration_ms, 2)},
            }

    async def get_metadata(
        self,
        bucket_name: str,
        key: str,
    ) -> dict[str, Any]:
        """获取对象元数据（不下载内容）.

        Args:
            bucket_name: Bucket 名称
            key: 对象键

        Returns:
            对象元数据

        Raises:
            ValueError: 当 bucket 不存在时
        """
        bucket = self.get_bucket(bucket_name)
        if not bucket:
            raise ValueError(f"Bucket '{bucket_name}' not found")

        try:
            obj = await bucket.head(key)

            if obj is None:
                return {
                    "success": False,
                    "error": {"code": "OBJECT_NOT_FOUND", "message": f"Object not found: {key}"},
                }

            http_metadata = obj.httpMetadata or {}
            custom_metadata = obj.customMetadata or {}

            return {
                "success": True,
                "data": {
                    "bucket": bucket_name,
                    "key": key,
                    "size": obj.size,
                    "etag": obj.etag,
                    "content_type": http_metadata.get("contentType"),
                    "cache_control": http_metadata.get("cacheControl"),
                    "uploaded_at": (
                        obj.uploaded.isoformat() + "Z" if hasattr(obj, "uploaded") else None
                    ),
                    "custom_metadata": custom_metadata,
                },
            }
        except Exception as e:
            return {"success": False, "error": {"code": "STORAGE_ERROR", "message": str(e)}}

    async def delete(
        self,
        bucket_name: str,
        key: str,
    ) -> dict[str, Any]:
        """从 R2 删除对象.

        Args:
            bucket_name: Bucket 名称
            key: 对象键/路径

        Returns:
            删除结果

        Raises:
            ValueError: 当 bucket 不存在时
        """
        bucket = self.get_bucket(bucket_name)
        if not bucket:
            raise ValueError(f"Bucket '{bucket_name}' not found")

        try:
            await bucket.delete(key)

            return {
                "success": True,
                "data": {
                    "bucket": bucket_name,
                    "key": key,
                    "deleted": True,
                    "deleted_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                },
            }
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "code": "STORAGE_ERROR",
                    "message": str(e),
                    "details": {"bucket": bucket_name, "key": key},
                },
            }

    async def copy(
        self,
        source_bucket: str,
        source_key: str,
        destination_bucket: str | None = None,
        destination_key: str = None,
        metadata_directive: str = "COPY",
        custom_metadata: dict[str, str] | None = None,
        cache_control: str | None = None,
    ) -> dict[str, Any]:
        """复制对象（同一或跨 bucket）.

        Args:
            source_bucket: 源 bucket 名称
            source_key: 源对象键
            destination_bucket: 目标 bucket 名称（None 表示同源 bucket）
            destination_key: 目标对象键
            metadata_directive: "COPY" 或 "REPLACE"
            custom_metadata: 新的自定义元数据（仅 REPLACE 时）
            cache_control: 新的缓存控制（仅 REPLACE 时）

        Returns:
            复制结果

        Raises:
            ValueError: 当 bucket 不存在或参数无效时
        """
        if destination_key is None:
            raise ValueError("destination_key is required")

        src_bucket = self.get_bucket(source_bucket)
        if not src_bucket:
            raise ValueError(f"Source bucket '{source_bucket}' not found")

        dest_bucket_name = destination_bucket or source_bucket
        dest_bucket = self.get_bucket(dest_bucket_name)
        if not dest_bucket:
            raise ValueError(f"Destination bucket '{dest_bucket_name}' not found")

        start_time = time.time()

        try:
            # 下载源对象
            source_obj = await src_bucket.get(source_key)
            if source_obj is None:
                return {
                    "success": False,
                    "error": {
                        "code": "OBJECT_NOT_FOUND",
                        "message": f"Source object not found: {source_key}",
                    },
                }

            data = await source_obj.arrayBuffer()

            # 准备上传选项
            options = {}

            if metadata_directive == "COPY":
                # 复制原有元数据
                if source_obj.httpMetadata:
                    options["httpMetadata"] = source_obj.httpMetadata
                if source_obj.customMetadata:
                    options["customMetadata"] = source_obj.customMetadata
            else:  # REPLACE
                # 使用新元数据
                http_metadata = {}
                if source_obj.httpMetadata and source_obj.httpMetadata.get("contentType"):
                    http_metadata["contentType"] = source_obj.httpMetadata["contentType"]
                if cache_control:
                    http_metadata["cacheControl"] = cache_control
                if http_metadata:
                    options["httpMetadata"] = http_metadata

                if custom_metadata:
                    options["customMetadata"] = custom_metadata

            # 上传到目标位置
            await dest_bucket.put(destination_key, data, options)

            duration_ms = (time.time() - start_time) * 1000

            return {
                "success": True,
                "data": {
                    "source_bucket": source_bucket,
                    "source_key": source_key,
                    "destination_bucket": dest_bucket_name,
                    "destination_key": destination_key,
                    "copied": True,
                    "etag": source_obj.etag,
                    "size": source_obj.size,
                    "copied_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                },
                "meta": {"duration_ms": round(duration_ms, 2)},
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "error": {"code": "STORAGE_ERROR", "message": str(e)},
                "meta": {"duration_ms": round(duration_ms, 2)},
            }

    # ==================== 对象列表 ====================

    async def list_objects(
        self,
        bucket_name: str,
        prefix: str | None = None,
        delimiter: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
        include_metadata: bool = False,
    ) -> dict[str, Any]:
        """列出 bucket 中的对象.

        Args:
            bucket_name: Bucket 名称
            prefix: 对象键前缀过滤
            delimiter: 分隔符（用于模拟目录结构）
            limit: 每页数量（默认 100，最大 1000）
            cursor: 分页游标
            include_metadata: 是否包含自定义元数据

        Returns:
            对象列表

        Raises:
            ValueError: 当 bucket 不存在时
        """
        bucket = self.get_bucket(bucket_name)
        if not bucket:
            raise ValueError(f"Bucket '{bucket_name}' not found")

        try:
            # 限制最大值
            limit = min(limit, 1000)

            # 构建列表选项
            options = {
                "limit": limit,
            }
            if prefix:
                options["prefix"] = prefix
            if delimiter:
                options["delimiter"] = delimiter
            if cursor:
                options["cursor"] = cursor

            # 列出对象
            result = await bucket.list(options)

            objects = []
            total_size = 0

            if result.get("objects"):
                for obj in result["objects"]:
                    obj_data = {
                        "key": obj.get("key"),
                        "size": obj.get("size", 0),
                        "size_human": self._format_size(obj.get("size", 0)),
                        "uploaded_at": (
                            obj.get("uploaded").isoformat() + "Z" if obj.get("uploaded") else None
                        ),
                        "etag": obj.get("etag"),
                    }

                    # HTTP 元数据
                    if obj.get("httpMetadata"):
                        obj_data["content_type"] = obj["httpMetadata"].get("contentType")
                        obj_data["cache_control"] = obj["httpMetadata"].get("cacheControl")

                    # 自定义元数据
                    if include_metadata and obj.get("customMetadata"):
                        obj_data["custom_metadata"] = obj["customMetadata"]

                    objects.append(obj_data)
                    total_size += obj.get("size", 0)

            # 公共前缀（目录）
            common_prefixes = []
            if result.get("delimitedPrefixes"):
                common_prefixes = result["delimitedPrefixes"]

            return {
                "success": True,
                "data": {
                    "bucket": bucket_name,
                    "prefix": prefix,
                    "delimiter": delimiter,
                    "objects": objects,
                    "common_prefixes": common_prefixes,
                    "truncated": result.get("truncated", False),
                    "cursor": result.get("cursor"),
                },
                "meta": {
                    "count": len(objects),
                    "total_size": total_size,
                    "common_prefix_count": len(common_prefixes),
                },
            }
        except Exception as e:
            return {
                "success": False,
                "error": {
                    "code": "STORAGE_ERROR",
                    "message": str(e),
                    "details": {"bucket": bucket_name},
                },
            }

    # ==================== 分片上传 ====================

    async def create_multipart_upload(
        self,
        bucket_name: str,
        key: str,
        content_type: str | None = None,
        custom_metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """初始化分片上传.

        Args:
            bucket_name: Bucket 名称
            key: 对象键
            content_type: MIME 类型
            custom_metadata: 自定义元数据

        Returns:
            上传 ID

        Raises:
            ValueError: 当 bucket 不存在时
        """
        bucket = self.get_bucket(bucket_name)
        if not bucket:
            raise ValueError(f"Bucket '{bucket_name}' not found")

        try:
            options = {}
            if content_type:
                options["httpMetadata"] = {"contentType": content_type}
            if custom_metadata:
                options["customMetadata"] = custom_metadata

            # 创建分片上传
            multipart = await bucket.createMultipartUpload(key, options)
            upload_id = multipart.uploadId

            # 存储上传状态
            self.multipart_uploads[upload_id] = {
                "bucket": bucket_name,
                "key": key,
                "parts": [],
                "created_at": datetime.now(UTC),
            }

            return {
                "success": True,
                "data": {
                    "bucket": bucket_name,
                    "key": key,
                    "upload_id": upload_id,
                    "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                },
            }
        except Exception as e:
            return {"success": False, "error": {"code": "STORAGE_ERROR", "message": str(e)}}

    async def upload_part(
        self,
        bucket_name: str,
        key: str,
        upload_id: str,
        part_number: int,
        data: bytes,
    ) -> dict[str, Any]:
        """上传一个分片.

        Args:
            bucket_name: Bucket 名称
            key: 对象键
            upload_id: 上传 ID
            part_number: 分片号（从 1 开始）
            data: 分片数据

        Returns:
            分片信息

        Raises:
            ValueError: 当参数无效时
        """
        bucket = self.get_bucket(bucket_name)
        if not bucket:
            raise ValueError(f"Bucket '{bucket_name}' not found")

        if upload_id not in self.multipart_uploads:
            return {
                "success": False,
                "error": {
                    "code": "UPLOAD_NOT_FOUND",
                    "message": f"Upload ID not found or expired: {upload_id}",
                },
            }

        if part_number < 1 or part_number > 10000:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_PART",
                    "message": f"Part number must be between 1 and 10000, got {part_number}",
                },
            }

        try:
            # 上传分片
            multipart = await bucket.resumeMultipartUpload(key, upload_id)
            await multipart.uploadPart(part_number, data)

            # 记录分片信息
            etag = hashlib.md5(data).hexdigest()
            self.multipart_uploads[upload_id]["parts"].append(
                {
                    "part_number": part_number,
                    "etag": etag,
                    "size": len(data),
                }
            )

            return {
                "success": True,
                "data": {
                    "part_number": part_number,
                    "etag": etag,
                    "size": len(data),
                },
            }
        except Exception as e:
            return {"success": False, "error": {"code": "STORAGE_ERROR", "message": str(e)}}

    async def complete_multipart_upload(
        self,
        bucket_name: str,
        key: str,
        upload_id: str,
        parts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """完成分片上传.

        Args:
            bucket_name: Bucket 名称
            key: 对象键
            upload_id: 上传 ID
            parts: 所有分片信息列表 [{"part_number": 1, "etag": "..."}, ...]

        Returns:
            完成结果

        Raises:
            ValueError: 当参数无效时
        """
        bucket = self.get_bucket(bucket_name)
        if not bucket:
            raise ValueError(f"Bucket '{bucket_name}' not found")

        if upload_id not in self.multipart_uploads:
            return {
                "success": False,
                "error": {
                    "code": "UPLOAD_NOT_FOUND",
                    "message": f"Upload ID not found or expired: {upload_id}",
                },
            }

        try:
            # 完成分片上传
            multipart = await bucket.resumeMultipartUpload(key, upload_id)
            result = await multipart.complete(parts)

            # 计算总大小
            upload_info = self.multipart_uploads[upload_id]
            total_size = sum(p["size"] for p in upload_info["parts"])

            # 清理上传状态
            del self.multipart_uploads[upload_id]

            return {
                "success": True,
                "data": {
                    "bucket": bucket_name,
                    "key": key,
                    "etag": result.etag if hasattr(result, "etag") else None,
                    "size": total_size,
                    "completed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                },
            }
        except Exception as e:
            return {"success": False, "error": {"code": "STORAGE_ERROR", "message": str(e)}}

    async def abort_multipart_upload(
        self,
        bucket_name: str,
        key: str,
        upload_id: str,
    ) -> dict[str, Any]:
        """取消分片上传.

        Args:
            bucket_name: Bucket 名称
            key: 对象键
            upload_id: 上传 ID

        Returns:
            取消结果

        Raises:
            ValueError: 当 bucket 不存在时
        """
        bucket = self.get_bucket(bucket_name)
        if not bucket:
            raise ValueError(f"Bucket '{bucket_name}' not found")

        if upload_id not in self.multipart_uploads:
            return {
                "success": False,
                "error": {
                    "code": "UPLOAD_NOT_FOUND",
                    "message": f"Upload ID not found or expired: {upload_id}",
                },
            }

        try:
            # 取消分片上传
            multipart = await bucket.resumeMultipartUpload(key, upload_id)
            await multipart.abort()

            # 清理上传状态
            del self.multipart_uploads[upload_id]

            return {
                "success": True,
                "data": {
                    "upload_id": upload_id,
                    "aborted": True,
                },
            }
        except Exception as e:
            return {"success": False, "error": {"code": "STORAGE_ERROR", "message": str(e)}}

    # ==================== 辅助方法 ====================

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小为人类可读格式.

        Args:
            size_bytes: 字节大小

        Returns:
            格式化的大小字符串
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def generate_presigned_url(
        self,
        bucket_name: str,
        key: str,
        method: str = "GET",
        expires_in: int = 3600,
        secret_key: str = None,
    ) -> dict[str, Any]:
        """生成预签名 URL（需要配置密钥）.

        Args:
            bucket_name: Bucket 名称
            key: 对象键
            method: HTTP 方法（GET 或 PUT）
            expires_in: 过期时间（秒，最大 604800 即 7 天）
            secret_key: 签名密钥

        Returns:
            预签名 URL 信息
        """
        if not secret_key:
            return {
                "success": False,
                "error": {
                    "code": "MISSING_SECRET_KEY",
                    "message": "Secret key is required for presigned URLs",
                },
            }

        # 限制过期时间
        expires_in = min(expires_in, 604800)  # 最大 7 天
        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
        expires_timestamp = int(expires_at.timestamp())

        # 构建签名字符串
        string_to_sign = f"{method}\n{bucket_name}\n{key}\n{expires_timestamp}"

        # 生成签名
        signature = hmac.new(
            secret_key.encode(), string_to_sign.encode(), hashlib.sha256
        ).hexdigest()

        # 构建 URL（简化版本，实际应该基于 worker URL）
        url = f"/api/v1/r2/{bucket_name}/objects/{key}?signature={signature}&expires={expires_timestamp}"

        return {
            "success": True,
            "data": {
                "url": url,
                "method": method,
                "expires_at": expires_at.isoformat() + "Z",
                "expires_in": expires_in,
            },
        }
