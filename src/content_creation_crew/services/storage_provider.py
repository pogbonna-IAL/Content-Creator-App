"""
Storage Provider Interface and Implementations
Abstraction for storing generated files (local filesystem, S3, etc.)
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any
import logging
import os
import shutil
import asyncio
from pathlib import Path
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    """Abstract base class for storage providers"""
    
    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Store data and return storage URL/path
        
        Args:
            key: Storage key/path
            data: Data bytes to store
            content_type: MIME type
        
        Returns:
            Storage URL or path
        """
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[bytes]:
        """
        Retrieve data by key
        
        Args:
            key: Storage key/path
        
        Returns:
            Data bytes or None if not found
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete data by key
        
        Args:
            key: Storage key/path
        
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def get_url(self, key: str) -> str:
        """
        Get public URL for stored object
        
        Args:
            key: Storage key/path
        
        Returns:
            Public URL
        """
        pass
    
    async def check_health(self, write_test: bool = True, min_free_space_mb: int = 1024) -> Dict[str, Any]:
        """
        Check storage health (M5)
        
        Args:
            write_test: Whether to perform write test
            min_free_space_mb: Minimum free space required in MB
        
        Returns:
            Dict with health information:
            - accessible: bool
            - writable: bool
            - free_space_mb: int
            - total_space_mb: int
            - error: str (if any)
        """
        # Default implementation returns basic info
        # Subclasses should override with specific checks
        return {
            "accessible": True,
            "writable": True,
            "free_space_mb": 0,
            "total_space_mb": 0,
            "health_check": "not_implemented"
        }


class LocalDiskStorageProvider(StorageProvider):
    """Local filesystem storage provider (default for dev)"""
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize local disk storage
        
        Args:
            base_path: Base directory for storage (default: ./storage)
        """
        self.base_path = Path(base_path or os.getenv("STORAGE_PATH", "./storage"))
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.base_path / "voiceovers").mkdir(exist_ok=True)
        (self.base_path / "artifacts").mkdir(exist_ok=True)
        
        logger.info(f"LocalDiskStorageProvider initialized at {self.base_path}")
    
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Store data to local filesystem"""
        # Sanitize key (remove leading slashes, replace path separators)
        safe_key = key.lstrip('/').replace('..', '').replace('/', os.sep)
        file_path = self.base_path / safe_key
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(file_path, 'wb') as f:
            f.write(data)
        
        logger.debug(f"Stored {len(data)} bytes to {file_path}")
        return str(file_path.relative_to(self.base_path))
    
    def get(self, key: str) -> Optional[bytes]:
        """Retrieve data from local filesystem"""
        safe_key = key.lstrip('/').replace('..', '').replace('/', os.sep)
        file_path = self.base_path / safe_key
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete file from local filesystem"""
        safe_key = key.lstrip('/').replace('..', '').replace('/', os.sep)
        file_path = self.base_path / safe_key
        
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            logger.debug(f"Deleted {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    def get_url(self, key: str) -> str:
        """Get local file URL (for dev, returns relative path)"""
        # In production, this would return a full URL
        # For dev, return relative path that can be served by static file handler
        safe_key = key.lstrip('/').replace('..', '').replace('/', '/')
        return f"/storage/{safe_key}"
    
    def generate_key(self, prefix: str, extension: str = "") -> str:
        """
        Generate a unique storage key
        
        Args:
            prefix: Key prefix (e.g., 'voiceovers')
            extension: File extension (e.g., '.wav')
        
        Returns:
            Unique storage key
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        filename = f"{prefix}/{timestamp}_{random_suffix}{extension}"
        return filename
    
    async def check_health(self, write_test: bool = True, min_free_space_mb: int = 1024) -> Dict[str, Any]:
        """
        Check local disk storage health (M5)
        
        Verifies:
        - Storage path exists and is accessible
        - Storage path is writable (if write_test=True)
        - Free space >= min_free_space_mb
        
        Args:
            write_test: Whether to perform write test
            min_free_space_mb: Minimum free space required in MB
        
        Returns:
            Dict with health information
        """
        health_info = {
            "accessible": False,
            "writable": False,
            "free_space_mb": 0,
            "total_space_mb": 0,
            "path": str(self.base_path),
            "error": None
        }
        
        try:
            # Check if path exists and is accessible
            if not self.base_path.exists():
                health_info["error"] = "Storage path does not exist"
                return health_info
            
            if not self.base_path.is_dir():
                health_info["error"] = "Storage path is not a directory"
                return health_info
            
            health_info["accessible"] = True
            
            # Check free space
            stat = shutil.disk_usage(self.base_path)
            free_mb = stat.free / (1024 * 1024)
            total_mb = stat.total / (1024 * 1024)
            
            health_info["free_space_mb"] = int(free_mb)
            health_info["total_space_mb"] = int(total_mb)
            health_info["free_space_percent"] = round((stat.free / stat.total) * 100, 2) if stat.total > 0 else 0
            
            # Check if writable (if enabled)
            if write_test:
                test_file = self.base_path / ".health_check_test"
                try:
                    # Write test file
                    with open(test_file, 'w') as f:
                        f.write("health_check")
                    
                    # Read it back
                    with open(test_file, 'r') as f:
                        content = f.read()
                    
                    # Delete it
                    test_file.unlink()
                    
                    if content == "health_check":
                        health_info["writable"] = True
                    else:
                        health_info["error"] = "Write test failed: content mismatch"
                
                except Exception as e:
                    health_info["error"] = f"Write test failed: {str(e)}"
                    logger.warning(f"Storage write test failed: {e}")
            else:
                # Assume writable if accessible
                health_info["writable"] = os.access(self.base_path, os.W_OK)
            
            # Check if free space meets minimum requirement
            if free_mb < min_free_space_mb:
                if not health_info["error"]:
                    health_info["error"] = f"Low disk space: {int(free_mb)}MB < {min_free_space_mb}MB"
        
        except Exception as e:
            health_info["error"] = f"Health check failed: {str(e)}"
            logger.error(f"Storage health check failed: {e}")
        
        return health_info


class S3StorageProvider(StorageProvider):
    """S3-compatible storage provider (for production)"""
    
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1"
    ):
        """
        Initialize S3 storage provider
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key (or from env)
            aws_secret_access_key: AWS secret key (or from env)
            endpoint_url: Custom S3 endpoint (for S3-compatible services)
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        
        # Import boto3 (optional dependency)
        try:
            import boto3
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
                endpoint_url=endpoint_url or os.getenv("S3_ENDPOINT_URL"),
                region_name=region
            )
            self._available = True
        except ImportError:
            logger.warning("boto3 not installed. S3StorageProvider unavailable.")
            self._available = False
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self._available = False
    
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Store data to S3"""
        if not self._available:
            raise RuntimeError("S3StorageProvider not available")
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type
        )
        
        return key
    
    def get(self, key: str) -> Optional[bytes]:
        """Retrieve data from S3"""
        if not self._available:
            raise RuntimeError("S3StorageProvider not available")
        
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except self.s3_client.exceptions.NoSuchKey:
            return None
    
    def delete(self, key: str) -> bool:
        """Delete object from S3"""
        if not self._available:
            raise RuntimeError("S3StorageProvider not available")
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False
    
    def get_url(self, key: str) -> str:
        """Get public S3 URL"""
        if not self._available:
            raise RuntimeError("S3StorageProvider not available")
        
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': key},
            ExpiresIn=3600  # 1 hour
        )
    
    async def check_health(self, write_test: bool = True, min_free_space_mb: int = 1024) -> Dict[str, Any]:
        """
        Check S3 storage health (M5)
        
        Verifies:
        - S3 client is available
        - Can perform HEAD bucket operation
        - Can write/read/delete test object (if write_test=True)
        
        Args:
            write_test: Whether to perform write test
            min_free_space_mb: Not applicable for S3 (ignored)
        
        Returns:
            Dict with health information
        """
        health_info = {
            "accessible": False,
            "writable": False,
            "free_space_mb": -1,  # Not applicable for S3
            "total_space_mb": -1,  # Not applicable for S3
            "bucket": self.bucket_name,
            "region": self.region,
            "error": None
        }
        
        if not self._available:
            health_info["error"] = "S3 client not available"
            return health_info
        
        try:
            # HEAD bucket to check accessibility
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            health_info["accessible"] = True
            
            # Perform write test if enabled
            if write_test:
                test_key = ".health_check_test"
                test_data = b"health_check"
                
                try:
                    # Write test object
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=test_key,
                        Body=test_data
                    )
                    
                    # Read it back
                    response = self.s3_client.get_object(
                        Bucket=self.bucket_name,
                        Key=test_key
                    )
                    content = response['Body'].read()
                    
                    # Delete it
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name,
                        Key=test_key
                    )
                    
                    if content == test_data:
                        health_info["writable"] = True
                    else:
                        health_info["error"] = "Write test failed: content mismatch"
                
                except Exception as e:
                    health_info["error"] = f"Write test failed: {str(e)}"
                    logger.warning(f"S3 write test failed: {e}")
            else:
                # Assume writable if accessible
                health_info["writable"] = True
        
        except self.s3_client.exceptions.NoSuchBucket:
            health_info["error"] = f"Bucket '{self.bucket_name}' does not exist"
        except self.s3_client.exceptions.ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            health_info["error"] = f"S3 error: {error_code}"
            logger.error(f"S3 health check failed: {e}")
        except Exception as e:
            health_info["error"] = f"Health check failed: {str(e)}"
            logger.error(f"S3 health check failed: {e}")
        
        return health_info


def get_storage_provider(provider_name: str = None) -> StorageProvider:
    """
    Factory function to get storage provider
    
    Args:
        provider_name: Provider name ('local', 's3', or None for auto-detect)
    
    Returns:
        StorageProvider instance
    """
    if provider_name is None:
        provider_name = os.getenv("STORAGE_PROVIDER", "local")
    
    if provider_name.lower() == "local":
        return LocalDiskStorageProvider()
    elif provider_name.lower() == "s3":
        bucket_name = os.getenv("S3_BUCKET_NAME")
        if not bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable required for S3 storage")
        return S3StorageProvider(bucket_name=bucket_name)
    else:
        raise ValueError(f"Unknown storage provider: {provider_name}")

