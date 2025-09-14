import boto3
from typing import Dict, List, Any, Optional, Union
from botocore.exceptions import ClientError, NoCredentialsError
import json
from datetime import datetime
import io
import gzip

from app.config import settings, S3_PATHS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class S3Client:
    """S3 client for content storage operations"""
    
    def __init__(self):
        # Configure credentials based on storage type
        if settings.STORAGE_TYPE == "minio":
            # Use MinIO credentials for local development
            access_key = settings.MINIO_ACCESS_KEY
            secret_key = settings.MINIO_SECRET_KEY
            region = settings.aws_region
            
            self.session = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            
            self.client = self.session.client(
                's3',
                endpoint_url=settings.s3_endpoint_url
            )
        else:
            # AWS S3 - use IAM instance role or explicit credentials
            # Check if we have explicit credentials
            if settings.aws_access_key_id and settings.aws_secret_access_key and \
               settings.aws_access_key_id not in ["local", "dummy", "test"] and \
               settings.aws_secret_access_key not in ["local", "dummy", "test"]:
                # Use explicit credentials (for local development)
                self.session = boto3.Session(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
                
                self.client = self.session.client(
                    's3',
                    endpoint_url=settings.s3_endpoint_url
                )
            else:
                # Use default credential chain (IAM instance role, environment variables, etc.)
                self.client = boto3.client(
                    's3',
                    region_name=settings.aws_region,
                    endpoint_url=settings.s3_endpoint_url
                )
        
        self.bucket_name = settings.s3_bucket_name
    
    def bucket_exists(self) -> bool:
        """Check if the S3 bucket exists"""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                logger.error(f"Error checking bucket existence: {str(e)}")
                return False
    
    def create_bucket(self) -> bool:
        """Create the S3 bucket if it doesn't exist"""
        try:
            if self.bucket_exists():
                logger.info(f"Bucket {self.bucket_name} already exists")
                return True
            
            # Create bucket
            if settings.aws_region == 'us-east-1':
                self.client.create_bucket(Bucket=self.bucket_name)
            else:
                self.client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': settings.aws_region}
                )
            
            logger.info(f"Successfully created bucket: {self.bucket_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create bucket {self.bucket_name}: {str(e)}")
            return False
    
    def put_object(self, key: str, data: Union[str, bytes, Dict], 
                   content_type: str = 'application/json',
                   compress: bool = False) -> bool:
        """Put an object into S3"""
        try:
            # Process data based on type
            if isinstance(data, dict):
                # Ensure proper JSON serialization with clean formatting
                body = json.dumps(data, indent=2, ensure_ascii=False, default=self._json_serializer)
                content_type = 'application/json'
            elif isinstance(data, str):
                body = data
            else:
                body = data
            
            # Compress if requested
            if compress and isinstance(body, str):
                body = gzip.compress(body.encode('utf-8'))
                content_type = 'application/gzip'
            
            # Add metadata
            metadata = {
                'uploaded_at': datetime.utcnow().isoformat(),
                'original_content_type': 'application/json' if isinstance(data, dict) else content_type,
                'compressed': str(compress).lower()
            }
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=body,
                ContentType=content_type,
                Metadata=metadata
            )
            
            logger.debug(f"Successfully uploaded object to S3: {key} (compressed: {compress})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload object {key}: {str(e)}")
            return False
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for complex objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    def get_object(self, key: str, decompress: bool = False) -> Optional[Union[str, bytes, Dict]]:
        """Get an object from S3"""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            body = response['Body'].read()
            content_type = response.get('ContentType', '')
            metadata = response.get('Metadata', {})
            
            # Check if object was compressed
            is_compressed = (
                decompress or 
                content_type == 'application/gzip' or 
                metadata.get('compressed', '').lower() == 'true'
            )
            
            # Decompress if needed
            if is_compressed and isinstance(body, bytes):
                try:
                    body = gzip.decompress(body).decode('utf-8')
                    logger.debug(f"Decompressed object: {key}")
                except Exception as e:
                    logger.warning(f"Failed to decompress {key}: {str(e)}")
                    # Continue with original body
            
            # Convert bytes to string if needed
            if isinstance(body, bytes):
                try:
                    body = body.decode('utf-8')
                except UnicodeDecodeError:
                    logger.warning(f"Could not decode {key} as UTF-8")
                    return body  # Return as bytes
            
            # Try to parse as JSON if it looks like JSON
            original_content_type = metadata.get('original_content_type', content_type)
            if (original_content_type == 'application/json' or 
                (isinstance(body, str) and body.strip().startswith(('{', '[')))):
                try:
                    parsed_json = json.loads(body)
                    logger.debug(f"Successfully parsed JSON from {key}")
                    return parsed_json
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from {key}: {str(e)}")
                    # Return as string if JSON parsing fails
            
            return body
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug(f"Object not found: {key}")
                return None
            else:
                logger.error(f"Failed to get object {key}: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error getting object {key}: {str(e)}")
            return None
    
    def delete_object(self, key: str) -> bool:
        """Delete an object from S3"""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.debug(f"Successfully deleted object: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete object {key}: {str(e)}")
            return False
    
    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """List objects in S3 with optional prefix"""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })
            
            return objects
            
        except ClientError as e:
            logger.error(f"Failed to list objects with prefix {prefix}: {str(e)}")
            return []
    
    def object_exists(self, key: str) -> bool:
        """Check if an object exists in S3"""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking object existence {key}: {str(e)}")
                return False
    
    def get_object_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for an S3 object"""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=key)
            return {
                'content_length': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            logger.error(f"Failed to get metadata for {key}: {str(e)}")
            return None
    
    def generate_s3_path(self, path_type: str, project_id: str, request_id: str, 
                        filename: Optional[str] = None) -> str:
        """Generate S3 path based on type and identifiers"""
        if path_type not in S3_PATHS:
            raise ValueError(f"Unknown path type: {path_type}")
        
        base_path = S3_PATHS[path_type].format(
            project_id=project_id,
            request_id=request_id
        )
        
        if filename:
            return f"{base_path}/{filename}"
        
        return base_path
    
    def store_serp_data(self, project_id: str, request_id: str, 
                       serp_data: Dict[str, Any], compress: bool = False) -> str:
        """Store SERP data in S3"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = self.generate_s3_path('serp_data', project_id, request_id, 
                                   f"serp_results_{timestamp}.json")
        
        if self.put_object(key, serp_data, compress=compress):
            logger.info(f"Stored SERP data in S3: {key} (compressed: {compress})")
            return key
        return ""
    
    def store_content_data(self, project_id: str, request_id: str, 
                          content_data: Dict[str, Any], compress: bool = False) -> str:
        """Store content data in S3"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = self.generate_s3_path('content_data', project_id, request_id,
                                   f"content_{timestamp}.json")
        
        if self.put_object(key, content_data, compress=compress):
            logger.info(f"Stored content data in S3: {key} (compressed: {compress})")
            return key
        return ""
    
    def store_insights(self, project_id: str, request_id: str, 
                      insights: Dict[str, Any], compress: bool = False) -> str:
        """Store insights in S3"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = self.generate_s3_path('insights', project_id, request_id,
                                   f"insights_{timestamp}.json")
        
        if self.put_object(key, insights, compress=compress):
            logger.info(f"Stored insights in S3: {key} (compressed: {compress})")
            return key
        return ""
    
    def store_implications(self, project_id: str, request_id: str, 
                          implications: Dict[str, Any], compress: bool = False) -> str:
        """Store implications in S3"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        key = self.generate_s3_path('implications', project_id, request_id,
                                   f"implications_{timestamp}.json")
        
        if self.put_object(key, implications, compress=compress):
            logger.info(f"Stored implications in S3: {key} (compressed: {compress})")
            return key
        return ""
    
    def get_content_references(self, project_id: str, request_id: str) -> List[str]:
        """Get all content references for a project/request"""
        prefix = self.generate_s3_path('raw_content', project_id, request_id)
        objects = self.list_objects(prefix)
        return [obj['key'] for obj in objects]


# Global S3 client instance
s3_client = S3Client()
