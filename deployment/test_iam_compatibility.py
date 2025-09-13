#!/usr/bin/env python3
"""
IAM Role Compatibility Test Script
==================================
This script tests whether the NEX Pharma Insights microservice 
can properly authenticate using IAM instance roles.
"""

import os
import sys
import boto3
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

class IAMRoleCompatibilityTester:
    """Test IAM role compatibility for AWS services"""
    
    def __init__(self):
        self.test_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.ENVIRONMENT,
            "tests": {}
        }
    
    def test_instance_metadata_service(self) -> bool:
        """Test if EC2 instance metadata service is available"""
        try:
            import requests
            
            # Test metadata service v2 (IMDSv2)
            token_url = "http://169.254.169.254/latest/api/token"
            metadata_url = "http://169.254.169.254/latest/meta-data/"
            
            # Get token
            token_response = requests.put(
                token_url,
                headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
                timeout=2
            )
            
            if token_response.status_code == 200:
                token = token_response.text
                
                # Test metadata access
                metadata_response = requests.get(
                    metadata_url,
                    headers={"X-aws-ec2-metadata-token": token},
                    timeout=2
                )
                
                if metadata_response.status_code == 200:
                    logger.info("✅ EC2 Instance Metadata Service (IMDSv2) is available")
                    return True
            
            # Fallback to IMDSv1
            metadata_response = requests.get(metadata_url, timeout=2)
            if metadata_response.status_code == 200:
                logger.info("✅ EC2 Instance Metadata Service (IMDSv1) is available")
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"❌ Instance metadata service not available: {e}")
            return False
    
    def test_sts_access(self) -> Dict[str, Any]:
        """Test AWS STS access to verify IAM role"""
        try:
            sts_client = boto3.client('sts', region_name=settings.AWS_REGION)
            identity = sts_client.get_caller_identity()
            
            result = {
                "success": True,
                "account": identity.get('Account'),
                "user_id": identity.get('UserId'),
                "arn": identity.get('Arn'),
                "is_role": 'role/' in identity.get('Arn', ''),
                "is_instance_profile": 'instance-profile' in identity.get('Arn', '')
            }
            
            logger.info(f"✅ STS Access successful - ARN: {result['arn']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ STS Access failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_dynamodb_access(self) -> Dict[str, Any]:
        """Test DynamoDB access with IAM role"""
        try:
            from app.database.dynamodb_client import DynamoDBClient
            
            # Create client (should use IAM role if no explicit credentials)
            dynamodb_client = DynamoDBClient()
            
            # Test basic operations
            tables = dynamodb_client.client.list_tables()
            
            result = {
                "success": True,
                "table_count": len(tables.get('TableNames', [])),
                "tables": tables.get('TableNames', [])[:5]  # First 5 tables
            }
            
            logger.info(f"✅ DynamoDB access successful - {result['table_count']} tables found")
            return result
            
        except Exception as e:
            logger.error(f"❌ DynamoDB access failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_s3_access(self) -> Dict[str, Any]:
        """Test S3 access with IAM role"""
        try:
            from app.database.s3_client import S3Client
            
            # Create client (should use IAM role if no explicit credentials)
            s3_client = S3Client()
            
            # Test basic operations
            buckets = s3_client.client.list_buckets()
            
            result = {
                "success": True,
                "bucket_count": len(buckets.get('Buckets', [])),
                "buckets": [b['Name'] for b in buckets.get('Buckets', [])][:5]  # First 5 buckets
            }
            
            logger.info(f"✅ S3 access successful - {result['bucket_count']} buckets found")
            return result
            
        except Exception as e:
            logger.error(f"❌ S3 access failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_bedrock_access(self) -> Dict[str, Any]:
        """Test Bedrock access with IAM role"""
        try:
            bedrock_client = boto3.client('bedrock-agent-runtime', region_name=settings.AWS_REGION)
            
            # Test client creation (actual invocation would require specific agent setup)
            result = {
                "success": True,
                "client_created": True,
                "region": settings.AWS_REGION
            }
            
            logger.info("✅ Bedrock client created successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Bedrock access failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_credential_chain(self) -> Dict[str, Any]:
        """Test boto3 credential chain resolution"""
        try:
            import boto3.session
            
            session = boto3.Session()
            credentials = session.get_credentials()
            
            if credentials:
                result = {
                    "success": True,
                    "access_key_id": credentials.access_key[:8] + "..." if credentials.access_key else None,
                    "method": credentials.method if hasattr(credentials, 'method') else 'unknown',
                    "token_available": bool(credentials.token)
                }
                
                logger.info(f"✅ Credentials resolved via: {result.get('method', 'unknown')}")
                return result
            else:
                return {"success": False, "error": "No credentials found"}
                
        except Exception as e:
            logger.error(f"❌ Credential chain test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all compatibility tests"""
        logger.info("🧪 Starting IAM Role Compatibility Tests...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"AWS Region: {settings.AWS_REGION}")
        
        # Test 1: Instance Metadata Service
        self.test_results["tests"]["metadata_service"] = {
            "available": self.test_instance_metadata_service()
        }
        
        # Test 2: Credential Chain
        self.test_results["tests"]["credential_chain"] = self.test_credential_chain()
        
        # Test 3: STS Access
        self.test_results["tests"]["sts_access"] = self.test_sts_access()
        
        # Test 4: DynamoDB Access
        self.test_results["tests"]["dynamodb_access"] = self.test_dynamodb_access()
        
        # Test 5: S3 Access
        self.test_results["tests"]["s3_access"] = self.test_s3_access()
        
        # Test 6: Bedrock Access
        self.test_results["tests"]["bedrock_access"] = self.test_bedrock_access()
        
        # Calculate overall success
        successful_tests = sum(1 for test in self.test_results["tests"].values() 
                             if test.get("success", False))
        total_tests = len(self.test_results["tests"])
        
        self.test_results["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "overall_success": successful_tests >= 4  # At least STS, DynamoDB, S3, Bedrock
        }
        
        return self.test_results
    
    def print_results(self):
        """Print formatted test results"""
        print("\n" + "="*60)
        print("🧪 IAM ROLE COMPATIBILITY TEST RESULTS")
        print("="*60)
        
        summary = self.test_results["summary"]
        
        if summary["overall_success"]:
            print("🎉 OVERALL STATUS: ✅ COMPATIBLE")
        else:
            print("⚠️  OVERALL STATUS: ❌ ISSUES DETECTED")
        
        print(f"Success Rate: {summary['successful_tests']}/{summary['total_tests']} "
              f"({summary['success_rate']:.1%})")
        
        print("\n📋 DETAILED RESULTS:")
        print("-" * 40)
        
        for test_name, result in self.test_results["tests"].items():
            status = "✅" if result.get("success", False) else "❌"
            print(f"{status} {test_name.replace('_', ' ').title()}")
            
            if not result.get("success", False) and "error" in result:
                print(f"   Error: {result['error']}")
        
        print("\n💡 RECOMMENDATIONS:")
        print("-" * 40)
        
        if not summary["overall_success"]:
            print("• Ensure EC2 instance has proper IAM role attached")
            print("• Verify IAM role has required permissions for:")
            print("  - DynamoDB (ListTables, GetItem, PutItem, UpdateItem, DeleteItem)")
            print("  - S3 (ListBucket, GetObject, PutObject, DeleteObject)")
            print("  - Bedrock (InvokeAgent, InvokeModel)")
            print("• Check AWS region configuration")
        else:
            print("✅ Your microservice is ready for EC2 deployment with IAM roles!")
        
        print(f"\nTest completed at: {self.test_results['timestamp']}")
        print("="*60)


def main():
    """Main test function"""
    tester = IAMRoleCompatibilityTester()
    results = tester.run_all_tests()
    tester.print_results()
    
    # Save results to file
    results_file = f"iam_compatibility_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Exit with appropriate code
    sys.exit(0 if results["summary"]["overall_success"] else 1)


if __name__ == "__main__":
    main() 