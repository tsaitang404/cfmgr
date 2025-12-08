"""R2 Object Storage management module."""

from typing import Any, Dict, Optional


class R2Manager:
    """Manager for Cloudflare R2 Object Storage operations.
    
    R2 绑定通过 Worker 环境传入。
    """
    
    def __init__(self, r2_bucket):
        """Initialize R2 Manager.
        
        Args:
            r2_bucket: R2 bucket binding from Cloudflare Worker environment
        """
        self.bucket = r2_bucket
    
    async def upload(self, key: str, data: bytes, content_type: Optional[str] = None) -> Dict[str, Any]:
        """Upload an object to R2.
        
        Args:
            key: Object key/path in R2
            data: File data as bytes
            content_type: MIME type of the object
            
        Returns:
            Upload result
        """
        try:
            options = {}
            if content_type:
                options["httpMetadata"] = {"contentType": content_type}
            
            result = await self.bucket.put(key, data, options)
            
            return {
                "success": True,
                "key": key,
                "message": "Object uploaded successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def download(self, key: str) -> Dict[str, Any]:
        """Download an object from R2.
        
        Args:
            key: Object key/path in R2
            
        Returns:
            Download result with object data
        """
        try:
            obj = await self.bucket.get(key)
            
            if obj is None:
                return {
                    "success": False,
                    "error": f"Object not found: {key}"
                }
            
            data = await obj.arrayBuffer()
            
            return {
                "success": True,
                "key": key,
                "data": data,
                "size": len(data),
                "content_type": obj.httpMetadata.get("contentType") if obj.httpMetadata else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete(self, key: str) -> Dict[str, Any]:
        """Delete an object from R2.
        
        Args:
            key: Object key/path in R2
            
        Returns:
            Deletion result
        """
        try:
            await self.bucket.delete(key)
            
            return {
                "success": True,
                "key": key,
                "message": "Object deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_objects(self, prefix: str = "", limit: int = 100) -> Dict[str, Any]:
        """List objects in R2 bucket.
        
        Args:
            prefix: Filter objects by prefix
            limit: Maximum number of objects to return
            
        Returns:
            List of objects
        """
        try:
            options = {
                "prefix": prefix,
                "limit": limit
            }
            
            result = await self.bucket.list(options)
            
            objects = []
            if result.get("objects"):
                for obj in result["objects"]:
                    objects.append({
                        "key": obj.get("key"),
                        "size": obj.get("size"),
                        "uploaded": obj.get("uploaded"),
                        "etag": obj.get("etag")
                    })
            
            return {
                "success": True,
                "objects": objects,
                "count": len(objects),
                "is_truncated": result.get("truncated", False)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
