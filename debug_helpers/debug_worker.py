#!/usr/bin/env python3
"""
Queue Worker Debug Helper
========================
Test and debug individual queue workers in PyCharm
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def debug_request_acceptance_worker():
    """Debug the request acceptance worker"""
    print("🔧 Testing Request Acceptance Worker")
    print("=" * 40)
    
    try:
        from app.queues.request_acceptance.worker import RequestAcceptanceWorker
        
        # Create worker instance
        worker = RequestAcceptanceWorker()
        print(f"✅ Worker created: {worker.queue_name}")
        
        # Create test item
        test_item = {
            "PK": "PROJECT#debug-project-123",
            "SK": "REQUEST#debug-request-456", 
            "payload": {
                "project_id": "debug-project-123",
                "project_request_id": "debug-request-456",
                "user_id": "debug_user",
                "priority": "high",
                "processing_strategy": "table",
                "config": {
                    "keywords": ["debug", "test"],
                    "sources": [
                        {
                            "name": "Debug Source",
                            "type": "regulatory", 
                            "url": "https://example.com/debug"
                        }
                    ],
                    "extraction_mode": "summary",
                    "quality_threshold": 0.8,
                    "metadata": {
                        "requestId": "debug-test-789"
                    }
                }
            },
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        print(f"📋 Test item created:")
        print(f"   Project ID: {test_item['payload']['project_id']}")
        print(f"   Request ID: {test_item['payload']['project_request_id']}")
        print(f"   User ID: {test_item['payload']['user_id']}")
        
        # Set breakpoint here to debug process_item method
        print(f"\n🐛 Processing item (set breakpoint here)...")
        result = await worker.process_item(test_item)
        
        print(f"✅ Processing result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Worker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def debug_serp_worker():
    """Debug the SERP worker"""
    print("\n🔍 Testing SERP Worker")
    print("=" * 25)
    
    try:
        from app.queues.serp.worker import SerpWorker
        
        worker = SerpWorker()
        print(f"✅ SERP Worker created: {worker.queue_name}")
        
        # Create test SERP item
        test_item = {
            "PK": "PROJECT#debug-project-123",
            "SK": "SERP#debug-serp-001",
            "payload": {
                "project_id": "debug-project-123",
                "project_request_id": "debug-request-456",
                "keywords": ["debug pharmaceutical"],
                "sources": [
                    {
                        "name": "Debug Source",
                        "type": "regulatory",
                        "url": "https://example.com"
                    }
                ],
                "search_query": "debug pharmaceutical regulatory",
                "max_results": 5
            },
            "status": "pending"
        }
        
        print(f"🔍 SERP test item:")
        print(f"   Keywords: {test_item['payload']['keywords']}")
        print(f"   Query: {test_item['payload']['search_query']}")
        
        # Set breakpoint here
        print(f"\n🐛 Processing SERP item (set breakpoint here)...")
        result = await worker.process_item(test_item)
        
        print(f"✅ SERP result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ SERP worker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def debug_perplexity_worker():
    """Debug the Perplexity worker"""
    print("\n🤖 Testing Perplexity Worker")
    print("=" * 30)
    
    try:
        from app.queues.perplexity.worker import PerplexityWorker
        
        worker = PerplexityWorker()
        print(f"✅ Perplexity Worker created: {worker.queue_name}")
        
        # Create test Perplexity item
        test_item = {
            "PK": "PROJECT#debug-project-123",
            "SK": "PERPLEXITY#debug-perp-001",
            "payload": {
                "project_id": "debug-project-123",
                "project_request_id": "debug-request-456",
                "url_data": {
                    "url": "https://example.com/debug-article",
                    "title": "Debug Pharmaceutical Article",
                    "snippet": "This is a debug article about pharmaceutical regulations..."
                },
                "user_prompt": "Analyze this content for pharmaceutical market intelligence",
                "content_id": "debug-content-001"
            },
            "status": "pending"
        }
        
        print(f"🤖 Perplexity test item:")
        print(f"   URL: {test_item['payload']['url_data']['url']}")
        print(f"   Title: {test_item['payload']['url_data']['title']}")
        
        # Set breakpoint here
        print(f"\n🐛 Processing Perplexity item (set breakpoint here)...")
        result = await worker.process_item(test_item)
        
        print(f"✅ Perplexity result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Perplexity worker test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_worker_initialization():
    """Test all worker initialization"""
    print("\n🏗️  Testing Worker Initialization")
    print("=" * 35)
    
    workers = [
        ('RequestAcceptanceWorker', 'app.queues.request_acceptance.worker'),
        ('SerpWorker', 'app.queues.serp.worker'),
        ('PerplexityWorker', 'app.queues.perplexity.worker'),
        ('RelevanceCheckWorker', 'app.queues.relevance_check.worker'),
        ('InsightWorker', 'app.queues.insight.worker'),
        ('ImplicationWorker', 'app.queues.implication.worker'),
    ]
    
    results = {}
    
    for worker_name, module_path in workers:
        try:
            module = __import__(module_path, fromlist=[worker_name])
            worker_class = getattr(module, worker_name)
            worker = worker_class()
            
            results[worker_name] = {
                'status': '✅',
                'queue_name': worker.queue_name,
                'table_name': worker.table_name
            }
            print(f"   ✅ {worker_name}: {worker.queue_name}")
            
        except Exception as e:
            results[worker_name] = {
                'status': '❌',
                'error': str(e)
            }
            print(f"   ❌ {worker_name}: {e}")
    
    return results

async def run_debug_session():
    """Run complete debug session"""
    print("🚀 Starting Queue Worker Debug Session")
    print("=" * 45)
    
    # Test worker initialization
    init_results = test_worker_initialization()
    
    # Test individual workers
    print(f"\n🧪 Testing Individual Workers:")
    print("-" * 30)
    
    # Test Request Acceptance Worker
    acceptance_result = await debug_request_acceptance_worker()
    
    # Test SERP Worker (optional - requires API key)
    # serp_result = await debug_serp_worker()
    
    # Test Perplexity Worker (optional - requires API key)  
    # perplexity_result = await debug_perplexity_worker()
    
    print(f"\n🎯 Debug Session Summary:")
    print("-" * 25)
    
    successful_inits = sum(1 for r in init_results.values() if r['status'] == '✅')
    total_workers = len(init_results)
    
    print(f"   Worker Initialization: {successful_inits}/{total_workers}")
    print(f"   Request Acceptance Test: {'✅' if acceptance_result else '❌'}")
    
    if successful_inits == total_workers and acceptance_result:
        print(f"\n🎉 All tests passed! Ready for debugging.")
    else:
        print(f"\n⚠️  Some tests failed. Check configuration and dependencies.")
    
    print(f"\n💡 PyCharm Debugging Tips:")
    print("   1. Set breakpoints in worker process_item() methods")
    print("   2. Use 'Debug' instead of 'Run' in PyCharm")
    print("   3. Inspect variables in the debug panel")
    print("   4. Use step-through debugging (F7, F8, F9)")

if __name__ == "__main__":
    print("🔧 Queue Worker Debug Helper")
    print("=" * 30)
    
    # Run async debug session
    asyncio.run(run_debug_session()) 