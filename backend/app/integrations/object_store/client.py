"""Object Store (MinIO/S3) integration"""
import hashlib
import io
from typing import Optional, BinaryIO, List, Dict, Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings


class ObjectStoreClient:
    """MinIO/S3 object store client"""

    def __init__(self):
        self._client = None
        self._bucket = settings.s3_bucket

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    async def ensure_bucket(self):
        """Ensure bucket exists"""
        try:
            self.client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self._bucket)

    def upload_file(
        self,
        key: str,
        file_data: bytes,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """Upload file to object store"""
        # Calculate checksum
        checksum = hashlib.sha256(file_data).hexdigest()

        self.client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=file_data,
            ContentType=content_type,
            Metadata={"checksum": checksum},
        )

        return {
            "key": key,
            "size": len(file_data),
            "checksum": checksum,
        }

    def upload_fileobj(
        self,
        key: str,
        file_obj: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> Dict[str, Any]:
        """Upload file object to object store"""
        file_data = file_obj.read()
        return self.upload_file(key, file_data, content_type)

    def download_file(self, key: str) -> bytes:
        """Download file from object store"""
        response = self.client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def delete_file(self, key: str) -> bool:
        """Delete file from object store"""
        try:
            self.client.delete_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    def list_files(self, prefix: str, max_keys: int = 1000) -> List[Dict[str, Any]]:
        """List files with given prefix"""
        response = self.client.list_objects_v2(
            Bucket=self._bucket,
            Prefix=prefix,
            MaxKeys=max_keys,
        )
        return [
            {
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"].isoformat(),
            }
            for obj in response.get("Contents", [])
        ]

    def get_file_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get file metadata"""
        try:
            response = self.client.head_object(Bucket=self._bucket, Key=key)
            return {
                "key": key,
                "size": response["ContentLength"],
                "content_type": response.get("ContentType"),
                "checksum": response.get("Metadata", {}).get("checksum"),
                "last_modified": response["LastModified"].isoformat(),
            }
        except ClientError:
            return None

    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """Copy file within bucket"""
        try:
            self.client.copy_object(
                Bucket=self._bucket,
                CopySource={"Bucket": self._bucket, "Key": source_key},
                Key=dest_key,
            )
            return True
        except ClientError:
            return False

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for download"""
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def get_presigned_upload_url(
        self, key: str, content_type: str = "application/octet-stream", expires_in: int = 3600
    ) -> str:
        """Generate presigned URL for upload"""
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )


# Singleton instance
object_store = ObjectStoreClient()
