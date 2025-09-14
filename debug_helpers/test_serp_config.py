#!/usr/bin/env python3
"""
Test SERP Configuration
Verify that the SERP worker is using the correct configuration values
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import QUEUE_PROCESSING_LIMITS, QUEUE_WORKFLOW
from app.queues.serp.worker import SerpWorker
from app.utils.logger import get_logger

logger = get_logger(__name__)

def test_serp_configuration():
    """Test SERP configuration values"""
    print("🔧 TESTING SERP CONFIGURATION")
    print("=" * 50)
    
    # Test 1: Check configuration values
    print(f"1. Configuration Values:")
    print(f"   max_perplexity_urls_per_serp: {QUEUE_PROCESSING_LIMITS.get('max_perplexity_urls_per_serp')}")
    print(f"   task_delay_seconds: {QUEUE_PROCESSING_LIMITS.get('task_delay_seconds')}")
    print(f"   SERP workflow: {QUEUE_WORKFLOW.get('serp')}")
    
    # Test 2: Check if values are correct
    expected_urls = 3
    expected_delay = 3
    expected_workflow = ['perplexity']
    
    actual_urls = QUEUE_PROCESSING_LIMITS.get('max_perplexity_urls_per_serp')
    actual_delay = QUEUE_PROCESSING_LIMITS.get('task_delay_seconds')
    actual_workflow = QUEUE_WORKFLOW.get('serp')
    
    print(f"\n2. Validation:")
    print(f"   URLs per SERP: {actual_urls} {'✅' if actual_urls == expected_urls else '❌ (should be 3)'}")
    print(f"   Task delay: {actual_delay} {'✅' if actual_delay == expected_delay else '❌ (should be 3)'}")
    print(f"   Workflow: {actual_workflow} {'✅' if actual_workflow == expected_workflow else '❌ (should be [\"perplexity\"])'}")
    
    # Test 3: Test SERP worker initialization
    print(f"\n3. SERP Worker Test:")
    try:
        worker = SerpWorker()
        print(f"   Worker initialized: ✅")
        print(f"   Queue name: {worker.queue_name}")
        print(f"   Table name: {worker.table_name}")
    except Exception as e:
        print(f"   Worker initialization failed: ❌ {str(e)}")
    
    # Test 4: Test URL selection logic
    print(f"\n4. URL Selection Logic Test:")
    try:
        # Mock URL data
        mock_urls = [
            {'url': 'https://example1.com', 'relevance_score': 0.9},
            {'url': 'https://example2.com', 'relevance_score': 0.8},
            {'url': 'https://example3.com', 'relevance_score': 0.7},
            {'url': 'https://example4.com', 'relevance_score': 0.6},
            {'url': 'https://example5.com', 'relevance_score': 0.5},
        ]
        
        max_urls = QUEUE_PROCESSING_LIMITS.get('max_perplexity_urls_per_serp', 3)
        selected = worker._select_best_urls(mock_urls, max_urls)
        
        print(f"   Input URLs: {len(mock_urls)}")
        print(f"   Max URLs config: {max_urls}")
        print(f"   Selected URLs: {len(selected)}")
        print(f"   Selection working: {'✅' if len(selected) == max_urls else '❌'}")
        
        if len(selected) == max_urls:
            print(f"   Top selected URLs:")
            for i, url in enumerate(selected):
                print(f"     {i+1}. {url['url']} (score: {url['relevance_score']})")
                
    except Exception as e:
        print(f"   URL selection test failed: ❌ {str(e)}")
    
    print(f"\n{'=' * 50}")
    
    # Overall assessment
    all_good = (
        actual_urls == expected_urls and 
        actual_delay == expected_delay and 
        actual_workflow == expected_workflow
    )
    
    if all_good:
        print("🎯 OVERALL STATUS: ✅ Configuration looks good!")
        print("   The 1:3 SERP to Perplexity ratio should work correctly.")
    else:
        print("⚠️  OVERALL STATUS: ❌ Configuration issues detected!")
        print("   The 1:3 ratio may not work as expected.")
        
        if actual_urls != expected_urls:
            print(f"   → Fix: Set max_perplexity_urls_per_serp to {expected_urls}")
        if actual_delay != expected_delay:
            print(f"   → Fix: Set task_delay_seconds to {expected_delay}")
        if actual_workflow != expected_workflow:
            print(f"   → Fix: Set serp workflow to {expected_workflow}")

if __name__ == "__main__":
    test_serp_configuration() 