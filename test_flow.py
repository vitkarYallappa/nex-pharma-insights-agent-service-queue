#!/usr/bin/env python3
"""
Simple test script to demonstrate the market intelligence processing flow
"""

import json
import requests
import time
from datetime import datetime

# Test request data
test_request = {
    "project_id": "041da4cc-c722-4f62-bcb6-07c930cafcf1",
    "project_request_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1",
    "user_id": "debug_user", 
    "priority": "high",
    "processing_strategy": "table",
    "config": {
        "keywords": ["Semaglutide", "Ozempic", "GLP-1 receptor agonist", "diabetes", "weight loss"],
        "sources": [
            {
                "name": "FDA",
                "type": "regulatory",
                "url": "https://www.fda.gov/"
            },
            {
                "name": "EMA",
                "type": "regulatory", 
                "url": "https://www.ema.europa.eu/"
            },
            {
                "name": "PubMed",
                "type": "academic",
                "url": "https://pubmed.ncbi.nlm.nih.gov/"
            }
        ],
        "extraction_mode": "summary",
        "quality_threshold": 0.8,
        "metadata": {
            "requestId": "214d5c73-dfc2-42ac-b787-e4cf8be3911b"
        }
    }
}

def test_api_flow():
    """Test the complete API flow"""
    base_url = "http://localhost:8000"
    
    print("🚀 Testing Market Intelligence Service Flow")
    print("=" * 50)
    
    # Step 1: Submit request
    print("\n📤 Step 1: Submitting market intelligence request...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/market-intelligence-requests",
            json=test_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            request_id = result["request_id"]
            print(f"✅ Request submitted successfully!")
            print(f"   Request ID: {request_id}")
            print(f"   Status: {result['status']}")
            print(f"   Estimated completion: {result['estimated_completion']}")
            print(f"   Tracking URL: {result['tracking_url']}")
        else:
            print(f"❌ Failed to submit request: {response.status_code}")
            print(f"   Error: {response.text}")
            return
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the service. Make sure it's running on localhost:8000")
        print("   Run: python3 -m uvicorn app.main:app --reload")
        return
    except Exception as e:
        print(f"❌ Error submitting request: {str(e)}")
        return
    
    # Step 2: Monitor processing
    print(f"\n👀 Step 2: Monitoring processing status...")
    
    for i in range(10):  # Check status 10 times
        try:
            time.sleep(2)  # Wait 2 seconds between checks
            
            status_response = requests.get(f"{base_url}/api/v1/requests/{request_id}/status")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                print(f"\n   Check {i+1}/10 - Overall Status: {status_data['status']}")
                print(f"   Progress:")
                
                for queue_name, queue_status in status_data.get('progress', {}).items():
                    status_icon = {
                        'pending': '⏳',
                        'processing': '🔄', 
                        'completed': '✅',
                        'failed': '❌',
                        'retry': '🔁'
                    }.get(queue_status, '❓')
                    
                    print(f"     {status_icon} {queue_name}: {queue_status}")
                
                # Check if processing is complete
                if status_data['status'] in ['completed', 'partially_completed']:
                    print(f"\n🎉 Processing completed with status: {status_data['status']}")
                    break
                elif status_data['status'] == 'failed':
                    print(f"\n💥 Processing failed: {status_data.get('error_message', 'Unknown error')}")
                    break
                    
            else:
                print(f"   ❌ Failed to get status: {status_response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error checking status: {str(e)}")
    
    # Step 3: Get results (if completed)
    print(f"\n📊 Step 3: Attempting to get results...")
    try:
        results_response = requests.get(f"{base_url}/api/v1/requests/{request_id}/results")
        
        if results_response.status_code == 200:
            results_data = results_response.json()
            print(f"✅ Results retrieved successfully!")
            print(f"   Status: {results_data['status']}")
            print(f"   Completed at: {results_data['completed_at']}")
            
            # Show insights
            insights = results_data.get('results', {}).get('insights')
            if insights:
                print(f"   📈 Insights available: {len(insights) if isinstance(insights, dict) else 'Yes'}")
            else:
                print(f"   📈 Insights: Not yet available")
            
            # Show implications  
            implications = results_data.get('results', {}).get('implications')
            if implications:
                print(f"   💡 Implications available: {len(implications) if isinstance(implications, dict) else 'Yes'}")
            else:
                print(f"   💡 Implications: Not yet available")
            
            # Show data references
            references = results_data.get('results', {}).get('raw_data_references', [])
            print(f"   📁 Raw data references: {len(references)} files")
            
        elif results_response.status_code == 400:
            print(f"⏳ Results not ready yet: {results_response.json().get('detail', 'Processing not complete')}")
        else:
            print(f"❌ Failed to get results: {results_response.status_code}")
            print(f"   Error: {results_response.text}")
            
    except Exception as e:
        print(f"❌ Error getting results: {str(e)}")
    
    # Step 4: Show expected flow
    print(f"\n📋 Expected Processing Flow:")
    print(f"   1. ✅ Request accepted → stored in main table")
    print(f"   2. 🔄 Request acceptance → validates & creates 3 SERP items (one per source)")
    print(f"   3. 🔄 SERP processing → each source finds URLs, creates Perplexity batches")
    print(f"   4. 🔄 Perplexity processing → each batch creates both Insight + Implication items")
    print(f"   5. 🔄 Final processing → Insight & Implication workers generate results")
    print(f"   6. ✅ Complete → Results available via API")
    
    print(f"\n🎯 Flow Summary:")
    print(f"   • 1 Request → 3 SERP items (FDA, EMA, PubMed)")
    print(f"   • Each SERP → Multiple Perplexity batches (based on URLs found)")
    print(f"   • Each Perplexity → 2 items (Insight + Implication)")
    print(f"   • Simple, understandable, parallel processing")

def test_health_check():
    """Test basic health check"""
    base_url = "http://localhost:8000"
    
    print("🏥 Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Service is healthy!")
            print(f"   Status: {health_data.get('status')}")
            print(f"   Database: {health_data.get('database', {}).get('status')}")
            print(f"   Workers: {len(health_data.get('workers', {}))}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {str(e)}")

if __name__ == "__main__":
    print("Market Intelligence Service - Flow Test")
    print("=====================================")
    
    # Test health first
    test_health_check()
    
    # Test the main flow
    test_api_flow()
    
    print(f"\n✨ Test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n💡 To run the service:")
    print(f"   python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print(f"\n📚 API Documentation:")
    print(f"   http://localhost:8000/docs") 