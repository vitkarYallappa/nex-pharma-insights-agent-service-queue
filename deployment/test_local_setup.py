#!/usr/bin/env python3
"""
Local Setup Test Script
=======================
This script tests the NEX Pharma Insights microservice in the local environment
to ensure everything works before deploying to EC2.
"""

import os
import sys
import json
import time
import asyncio
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

class LocalSetupTester:
    """Test local microservice setup"""
    
    def __init__(self):
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "environment": settings.ENVIRONMENT,
            "tests": {},
            "service_url": "http://localhost:8005"
        }
        self.service_process = None
    
    def test_python_environment(self) -> Dict[str, Any]:
        """Test Python environment and dependencies"""
        try:
            import sys
            import fastapi
            import uvicorn
            import boto3
            import pydantic
            
            result = {
                "success": True,
                "python_version": sys.version,
                "fastapi_version": fastapi.__version__,
                "uvicorn_version": uvicorn.__version__,
                "boto3_version": boto3.__version__,
                "pydantic_version": pydantic.__version__
            }
            
            logger.info("✅ Python environment and dependencies are working")
            return result
            
        except Exception as e:
            logger.error(f"❌ Python environment test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_configuration_loading(self) -> Dict[str, Any]:
        """Test configuration loading"""
        try:
            from config import settings
            
            result = {
                "success": True,
                "environment": settings.ENVIRONMENT,
                "debug": settings.DEBUG,
                "aws_region": settings.AWS_REGION,
                "database_type": settings.DATABASE_TYPE,
                "storage_type": settings.STORAGE_TYPE,
                "has_env_file": Path(".env").exists()
            }
            
            logger.info(f"✅ Configuration loaded successfully - Environment: {settings.ENVIRONMENT}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Configuration loading failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_database_clients(self) -> Dict[str, Any]:
        """Test database client initialization"""
        try:
            from app.database.dynamodb_client import DynamoDBClient
            from app.database.s3_client import S3Client
            
            # Test DynamoDB client
            dynamodb_client = DynamoDBClient()
            
            # Test S3 client  
            s3_client = S3Client()
            
            result = {
                "success": True,
                "dynamodb_client": "initialized",
                "s3_client": "initialized",
                "dynamodb_endpoint": settings.DYNAMODB_ENDPOINT,
                "s3_endpoint": settings.s3_endpoint_url if hasattr(settings, 's3_endpoint_url') else None
            }
            
            logger.info("✅ Database clients initialized successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Database client test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_queue_workers(self) -> Dict[str, Any]:
        """Test queue worker initialization"""
        try:
            from app.queues.request_acceptance.worker import RequestAcceptanceWorker
            from app.queues.serp.worker import SerpWorker
            from app.queues.perplexity.worker import PerplexityWorker
            from app.queues.relevance_check.worker import RelevanceCheckWorker
            from app.queues.insight.worker import InsightWorker
            from app.queues.implication.worker import ImplicationWorker
            
            workers = {
                "request_acceptance": RequestAcceptanceWorker,
                "serp": SerpWorker,
                "perplexity": PerplexityWorker,
                "relevance_check": RelevanceCheckWorker,
                "insight": InsightWorker,
                "implication": ImplicationWorker
            }
            
            initialized_workers = {}
            for name, worker_class in workers.items():
                try:
                    worker = worker_class()
                    initialized_workers[name] = "✅ initialized"
                except Exception as e:
                    initialized_workers[name] = f"❌ failed: {str(e)}"
            
            success_count = sum(1 for status in initialized_workers.values() if "✅" in status)
            
            result = {
                "success": success_count == len(workers),
                "workers": initialized_workers,
                "success_count": success_count,
                "total_count": len(workers)
            }
            
            logger.info(f"✅ Queue workers test: {success_count}/{len(workers)} successful")
            return result
            
        except Exception as e:
            logger.error(f"❌ Queue workers test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_fastapi_import(self) -> Dict[str, Any]:
        """Test FastAPI application import"""
        try:
            from app.main import app
            
            result = {
                "success": True,
                "app_title": app.title,
                "app_version": app.version,
                "routes_count": len(app.routes)
            }
            
            logger.info("✅ FastAPI application imported successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ FastAPI import failed: {e}")
            return {"success": False, "error": str(e)}
    
    def start_service(self) -> bool:
        """Start the microservice for testing"""
        try:
            import subprocess
            import time
            
            logger.info("🚀 Starting microservice for testing...")
            
            # Start uvicorn server in background
            cmd = [
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--host", "0.0.0.0", 
                "--port", "8005",
                "--log-level", "info"
            ]
            
            self.service_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            # Wait for service to start
            for i in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get("http://localhost:8005/health", timeout=2)
                    if response.status_code in [200, 503]:  # 503 is ok for degraded health
                        logger.info("✅ Service started successfully")
                        return True
                except:
                    pass
                time.sleep(1)
            
            logger.error("❌ Service failed to start within 30 seconds")
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to start service: {e}")
            return False
    
    def test_api_endpoints(self) -> Dict[str, Any]:
        """Test API endpoints"""
        try:
            base_url = "http://localhost:8005"
            
            endpoints = {
                "root": "/",
                "health": "/health",
                "metrics": "/metrics",
                "docs": "/docs"
            }
            
            results = {}
            
            for name, endpoint in endpoints.items():
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    results[name] = {
                        "status_code": response.status_code,
                        "success": response.status_code < 400,
                        "response_time": response.elapsed.total_seconds()
                    }
                except Exception as e:
                    results[name] = {
                        "success": False,
                        "error": str(e)
                    }
            
            success_count = sum(1 for r in results.values() if r.get("success", False))
            
            result = {
                "success": success_count >= 3,  # At least root, health, metrics should work
                "endpoints": results,
                "success_count": success_count,
                "total_count": len(endpoints)
            }
            
            logger.info(f"✅ API endpoints test: {success_count}/{len(endpoints)} successful")
            return result
            
        except Exception as e:
            logger.error(f"❌ API endpoints test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def test_sample_request(self) -> Dict[str, Any]:
        """Test a sample market intelligence request"""
        try:
            base_url = "http://localhost:8005"
            
            # Sample request payload
            payload = {
                "project_id": "test-project-123",
                "project_request_id": "test-request-456",
                "user_id": "test_user",
                "priority": "high",
                "processing_strategy": "table",
                "config": {
                    "keywords": ["Test Keyword"],
                    "sources": [
                        {
                            "name": "Test Source",
                            "type": "regulatory",
                            "url": "https://example.com/"
                        }
                    ],
                    "extraction_mode": "summary",
                    "quality_threshold": 0.8,
                    "metadata": {
                        "requestId": "test-request-789"
                    }
                }
            }
            
            response = requests.post(
                f"{base_url}/api/v1/market-intelligence-requests",
                json=payload,
                timeout=30
            )
            
            result = {
                "success": response.status_code in [200, 201, 202],
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
            
            if result["success"]:
                try:
                    result["response_data"] = response.json()
                except:
                    result["response_text"] = response.text[:200]
            else:
                result["error"] = response.text[:200]
            
            logger.info(f"✅ Sample request test: Status {response.status_code}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Sample request test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_service(self):
        """Stop the test service"""
        if self.service_process:
            try:
                self.service_process.terminate()
                self.service_process.wait(timeout=10)
                logger.info("✅ Service stopped successfully")
            except:
                try:
                    self.service_process.kill()
                    logger.info("✅ Service killed successfully")
                except:
                    logger.warning("⚠️ Could not stop service process")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all local setup tests"""
        logger.info("🧪 Starting Local Setup Tests...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Working Directory: {os.getcwd()}")
        
        try:
            # Test 1: Python Environment
            self.test_results["tests"]["python_environment"] = self.test_python_environment()
            
            # Test 2: Configuration Loading
            self.test_results["tests"]["configuration"] = self.test_configuration_loading()
            
            # Test 3: Database Clients
            self.test_results["tests"]["database_clients"] = self.test_database_clients()
            
            # Test 4: Queue Workers
            self.test_results["tests"]["queue_workers"] = self.test_queue_workers()
            
            # Test 5: FastAPI Import
            self.test_results["tests"]["fastapi_import"] = self.test_fastapi_import()
            
            # Test 6: Start Service
            service_started = self.start_service()
            self.test_results["tests"]["service_startup"] = {
                "success": service_started
            }
            
            if service_started:
                # Test 7: API Endpoints
                self.test_results["tests"]["api_endpoints"] = self.test_api_endpoints()
                
                # Test 8: Sample Request
                self.test_results["tests"]["sample_request"] = self.test_sample_request()
            
            # Calculate overall success
            successful_tests = sum(1 for test in self.test_results["tests"].values() 
                                 if test.get("success", False))
            total_tests = len(self.test_results["tests"])
            
            self.test_results["summary"] = {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
                "overall_success": successful_tests >= 6  # Most tests should pass
            }
            
            return self.test_results
            
        finally:
            # Always try to stop the service
            self.stop_service()
    
    def print_results(self):
        """Print formatted test results"""
        print("\n" + "="*60)
        print("🧪 LOCAL SETUP TEST RESULTS")
        print("="*60)
        
        summary = self.test_results["summary"]
        
        if summary["overall_success"]:
            print("🎉 OVERALL STATUS: ✅ LOCAL SETUP WORKING")
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
            print("• Check Python virtual environment activation")
            print("• Verify all dependencies are installed: pip install -r requirements.txt")
            print("• Ensure .env file exists with proper configuration")
            print("• Check if local DynamoDB/MinIO services are running (if needed)")
            print("• Review error messages above for specific issues")
        else:
            print("✅ Your local setup is working correctly!")
            print("✅ Ready for EC2 deployment with IAM roles!")
        
        print(f"\nTest completed at: {self.test_results['timestamp']}")
        print("="*60)


def main():
    """Main test function"""
    tester = LocalSetupTester()
    
    try:
        results = tester.run_all_tests()
        tester.print_results()
        
        # Save results to file
        results_file = f"local_setup_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        sys.exit(0 if results["summary"]["overall_success"] else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        tester.stop_service()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        tester.stop_service()
        sys.exit(1)


if __name__ == "__main__":
    main() 