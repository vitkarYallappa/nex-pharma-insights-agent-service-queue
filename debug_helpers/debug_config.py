#!/usr/bin/env python3
"""
Configuration Debug Helper
==========================
Quick script to test and debug configuration loading in PyCharm
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def debug_configuration():
    """Debug configuration loading and display current settings"""
    print("🔧 Configuration Debug Helper")
    print("=" * 50)
    
    try:
        from config import settings
        
        print("✅ Configuration loaded successfully!")
        print(f"📁 Working Directory: {Path.cwd()}")
        print(f"🐍 Python Path: {sys.path[0]}")
        
        print("\n📋 Core Settings:")
        print(f"   Environment: {settings.ENVIRONMENT}")
        print(f"   Debug Mode: {settings.DEBUG}")
        print(f"   Host: {settings.HOST}")
        print(f"   Port: {settings.PORT}")
        
        print("\n☁️  AWS Settings:")
        print(f"   Region: {settings.AWS_REGION}")
        print(f"   Has Access Key: {bool(settings.AWS_ACCESS_KEY_ID and settings.AWS_ACCESS_KEY_ID != 'local')}")
        print(f"   Has Secret Key: {bool(settings.AWS_SECRET_ACCESS_KEY and settings.AWS_SECRET_ACCESS_KEY != 'local')}")
        
        print("\n🗄️  Database Settings:")
        print(f"   Database Type: {settings.DATABASE_TYPE}")
        print(f"   DynamoDB Endpoint: {settings.DYNAMODB_ENDPOINT}")
        print(f"   Table Environment: {settings.TABLE_ENVIRONMENT}")
        
        print("\n💾 Storage Settings:")
        print(f"   Storage Type: {settings.STORAGE_TYPE}")
        print(f"   S3 Bucket: {settings.S3_BUCKET_NAME}")
        if hasattr(settings, 's3_endpoint_url'):
            print(f"   S3 Endpoint: {settings.s3_endpoint_url}")
        
        print("\n🔑 API Keys Status:")
        api_keys = {
            'Perplexity': bool(settings.PERPLEXITY_API_KEY),
            'SERP': bool(settings.SERP_API_KEY),
            'Anthropic': bool(settings.ANTHROPIC_API_KEY),
        }
        
        for service, has_key in api_keys.items():
            status = "✅" if has_key else "❌"
            print(f"   {service}: {status}")
        
        print("\n🔐 Bedrock Settings:")
        print(f"   Mock Mode: {settings.BEDROCK_MOCK_MODE}")
        print(f"   Region: {settings.BEDROCK_AWS_REGION}")
        print(f"   Has Access Key: {bool(settings.BEDROCK_AWS_ACCESS_KEY_ID)}")
        print(f"   Has Secret Key: {bool(settings.BEDROCK_AWS_SECRET_ACCESS_KEY)}")
        
        print("\n📊 Environment File Status:")
        env_files = ['.env', 'deployment/production.env']
        for env_file in env_files:
            env_path = project_root / env_file
            exists = env_path.exists()
            status = "✅" if exists else "❌"
            print(f"   {env_file}: {status}")
            if exists:
                print(f"      Size: {env_path.stat().st_size} bytes")
        
        # Check for missing critical settings
        print("\n⚠️  Warnings:")
        warnings = []
        
        if not settings.PERPLEXITY_API_KEY:
            warnings.append("Missing PERPLEXITY_API_KEY")
        if not settings.SERP_API_KEY:
            warnings.append("Missing SERP_API_KEY")
        if settings.SECRET_KEY == "your-secret-key-here-change-in-production":
            warnings.append("Using default SECRET_KEY")
        
        if warnings:
            for warning in warnings:
                print(f"   ⚠️  {warning}")
        else:
            print("   ✅ No configuration warnings")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        print(f"\n🔍 Debug Info:")
        print(f"   Current directory: {Path.cwd()}")
        print(f"   Python path: {sys.path}")
        print(f"   Environment variables: {list(os.environ.keys())[:10]}...")
        
        import traceback
        print(f"\n📋 Full traceback:")
        traceback.print_exc()
        
        return False

def test_imports():
    """Test importing key modules"""
    print("\n🧪 Testing Module Imports:")
    print("-" * 30)
    
    modules_to_test = [
        ('fastapi', 'FastAPI framework'),
        ('uvicorn', 'ASGI server'),
        ('boto3', 'AWS SDK'),
        ('pydantic', 'Data validation'),
        ('requests', 'HTTP client'),
    ]
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"   ✅ {module_name}: {description}")
        except ImportError as e:
            print(f"   ❌ {module_name}: {e}")

def test_app_imports():
    """Test importing application modules"""
    print("\n🏗️  Testing App Module Imports:")
    print("-" * 35)
    
    app_modules = [
        ('app.main', 'Main FastAPI application'),
        ('app.database.dynamodb_client', 'DynamoDB client'),
        ('app.database.s3_client', 'S3 client'),
        ('app.queues.request_acceptance.worker', 'Request acceptance worker'),
        ('app.utils.logger', 'Logging utilities'),
    ]
    
    for module_name, description in app_modules:
        try:
            __import__(module_name)
            print(f"   ✅ {module_name}: {description}")
        except ImportError as e:
            print(f"   ❌ {module_name}: {e}")

if __name__ == "__main__":
    print("🚀 Starting Configuration Debug Session...")
    
    # Test configuration
    config_ok = debug_configuration()
    
    # Test imports
    test_imports()
    test_app_imports()
    
    print(f"\n🎯 Debug Summary:")
    if config_ok:
        print("   ✅ Configuration is working correctly")
        print("   🎉 Ready for PyCharm debugging!")
    else:
        print("   ❌ Configuration issues detected")
        print("   🔧 Please fix configuration before debugging")
    
    print(f"\n💡 Next Steps:")
    print("   1. Set breakpoints in your code")
    print("   2. Create PyCharm run configuration")
    print("   3. Start debugging session")
    print("   4. Access http://localhost:8005/docs") 