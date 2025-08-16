# backend/app/services/file_service.py
import os
import boto3
import uuid
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError
import logging
import tempfile
import shutil

from ..config import settings

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self):
        self.use_s3 = bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY)
        
        if self.use_s3:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.bucket_name = settings.AWS_BUCKET_NAME
        else:
            # Use local storage
            self.local_storage_path = os.path.join(os.getcwd(), "uploads")
            os.makedirs(self.local_storage_path, exist_ok=True)
    
    async def upload_file(
        self, 
        file: BinaryIO, 
        filename: str, 
        content_type: str,
        user_id: str
    ) -> str:
        """
        Upload file to storage (S3 or local) and return URL
        """
        try:
            # Generate unique filename
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{user_id}/{uuid.uuid4()}{file_extension}"
            
            if self.use_s3:
                return await self._upload_to_s3(file, unique_filename, content_type)
            else:
                return await self._upload_to_local(file, unique_filename)
                
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise RuntimeError(f"File upload failed: {str(e)}")
    
    async def _upload_to_s3(self, file: BinaryIO, filename: str, content_type: str) -> str:
        """Upload file to S3"""
        try:
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                filename,
                ExtraArgs={
                    'ContentType': content_type,
                    'ACL': 'private'
                }
            )
            
            # Generate presigned URL for access
            url = f"s3://{self.bucket_name}/{filename}"
            logger.info(f"File uploaded to S3: {filename}")
            return url
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise RuntimeError(f"S3 upload failed: {str(e)}")
    
    async def _upload_to_local(self, file: BinaryIO, filename: str) -> str:
        """Upload file to local storage"""
        try:
            file_path = os.path.join(self.local_storage_path, filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Save file
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(file, f)
            
            logger.info(f"File uploaded locally: {filename}")
            return file_path
            
        except Exception as e:
            logger.error(f"Local upload failed: {e}")
            raise RuntimeError(f"Local upload failed: {str(e)}")
    
    async def download_file(self, file_url: str) -> str:
        """
        Download file from storage to temporary location and return local path
        """
        try:
            if file_url.startswith('s3://'):
                return await self._download_from_s3(file_url)
            else:
                # Local file, return path directly
                if os.path.exists(file_url):
                    return file_url
                else:
                    raise FileNotFoundError(f"Local file not found: {file_url}")
                    
        except Exception as e:
            logger.error(f"File download failed: {e}")
            raise RuntimeError(f"File download failed: {str(e)}")
    
    async def _download_from_s3(self, s3_url: str) -> str:
        """Download file from S3 to temporary location"""
        try:
            # Parse S3 URL: s3://bucket/key
            parts = s3_url.replace('s3://', '').split('/', 1)
            bucket = parts[0]
            key = parts[1]
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.close()
            
            # Download from S3
            self.s3_client.download_file(bucket, key, temp_file.name)
            
            logger.info(f"File downloaded from S3: {key}")
            return temp_file.name
            
        except ClientError as e:
            logger.error(f"S3 download failed: {e}")
            raise RuntimeError(f"S3 download failed: {str(e)}")
    
    async def delete_file(self, file_url: str) -> bool:
        """
        Delete file from storage
        """
        try:
            if file_url.startswith('s3://'):
                return await self._delete_from_s3(file_url)
            else:
                # Local file
                if os.path.exists(file_url):
                    os.remove(file_url)
                    logger.info(f"Local file deleted: {file_url}")
                    return True
                return False
                
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            return False
    
    async def _delete_from_s3(self, s3_url: str) -> bool:
        """Delete file from S3"""
        try:
            # Parse S3 URL
            parts = s3_url.replace('s3://', '').split('/', 1)
            bucket = parts[0]
            key = parts[1]
            
            # Delete from S3
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            
            logger.info(f"File deleted from S3: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 deletion failed: {e}")
            return False
    
    async def get_file_info(self, file_url: str) -> Optional[dict]:
        """
        Get file information (size, modified date, etc.)
        """
        try:
            if file_url.startswith('s3://'):
                return await self._get_s3_file_info(file_url)
            else:
                # Local file
                if os.path.exists(file_url):
                    stat = os.stat(file_url)
                    return {
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'exists': True
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return None
    
    async def _get_s3_file_info(self, s3_url: str) -> Optional[dict]:
        """Get S3 file information"""
        try:
            # Parse S3 URL
            parts = s3_url.replace('s3://', '').split('/', 1)
            bucket = parts[0]
            key = parts[1]
            
            # Get object metadata
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            
            return {
                'size': response['ContentLength'],
                'modified': response['LastModified'].timestamp(),
                'content_type': response.get('ContentType'),
                'exists': True
            }
            
        except ClientError as e:
            logger.error(f"Failed to get S3 file info: {e}")
            return None
    
    def validate_file(self, filename: str, file_size: int, content_type: str) -> bool:
        """
        Validate uploaded file
        """
        # Check file size
        if file_size > settings.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size: {settings.MAX_FILE_SIZE / 1024 / 1024:.1f}MB")
        
        # More flexible file type checking
        allowed_extensions = ['.wav', '.mp3', '.m4a', '.mp4', '.mov', '.avi', '.mkv', '.webm', '.ogg']
        file_extension = os.path.splitext(filename.lower())[1]
        
        # Check both MIME type and file extension
        if content_type not in settings.ALLOWED_FILE_TYPES and file_extension not in allowed_extensions:
            raise ValueError(f"File type not allowed. Allowed extensions: {', '.join(allowed_extensions)}")
        
        # Check filename
        if not filename or len(filename) > 255:
            raise ValueError("Invalid filename")
        
        return True
    
    def cleanup_temp_file(self, file_path: str) -> bool:
        """
        Clean up temporary file
        """
        try:
            if os.path.exists(file_path) and file_path.startswith(tempfile.gettempdir()):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to cleanup temp file {file_path}: {e}")
            return False