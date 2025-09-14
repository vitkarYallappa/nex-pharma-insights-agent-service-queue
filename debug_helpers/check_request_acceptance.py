#!/usr/bin/env python3
"""
Check Request Acceptance Level
Analyze the request acceptance queue processing and identify issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.dynamodb_client import dynamodb_client
from config import QUEUE_TABLES
from app.utils.logger import get_logger
from datetime import datetime, timedelta
from typing import Dict, Any, List

logger = get_logger(__name__)

def check_request_acceptance_status():
    """Check the current status of request acceptance queue"""
    print("🔍 REQUEST ACCEPTANCE QUEUE ANALYSIS")
    print("=" * 60)
    
    table_name = QUEUE_TABLES.get('request_acceptance')
    if not table_name:
        print("❌ Request acceptance table not found in configuration")
        return
    
    print(f"📋 Table: {table_name}")
    
    try:
        # Get all request acceptance items from last 24 hours
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        items = dynamodb_client.scan_items(
            table_name=table_name,
            filter_expression="created_at >= :cutoff",
            expression_attribute_values={":cutoff": cutoff_time}
        )
        
        print(f"📊 Total items in last 24 hours: {len(items)}")
        
        # Analyze by status
        status_counts = {}
        pending_items = []
        processing_items = []
        failed_items = []
        completed_items = []
        
        for item in items:
            status = item.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if status == 'pending':
                pending_items.append(item)
            elif status == 'processing':
                processing_items.append(item)
            elif status == 'failed':
                failed_items.append(item)
            elif status == 'completed':
                completed_items.append(item)
        
        print(f"\n📈 Status Breakdown:")
        for status, count in status_counts.items():
            emoji = {
                'pending': '⏳',
                'processing': '🔄', 
                'completed': '✅',
                'failed': '❌'
            }.get(status, '❓')
            print(f"   {emoji} {status}: {count}")
        
        # Check pending items details
        if pending_items:
            print(f"\n⏳ PENDING ITEMS ANALYSIS ({len(pending_items)} items):")
            print("-" * 50)
            for i, item in enumerate(pending_items[:5]):  # Show first 5
                pk = item.get('PK', 'unknown')
                created_at = item.get('created_at', 'unknown')
                payload = item.get('payload', {})
                
                print(f"   {i+1}. PK: {pk}")
                print(f"      Created: {created_at}")
                print(f"      Payload keys: {list(payload.keys()) if payload else 'None'}")
                
                # Check if it has original_request
                original_request = payload.get('original_request', {}) if payload else {}
                if original_request:
                    config = original_request.get('config', {})
                    keywords = config.get('keywords', [])
                    sources = config.get('sources', [])
                    print(f"      Keywords: {len(keywords)} | Sources: {len(sources)}")
                else:
                    print(f"      ⚠️  No original_request found")
                print()
            
            if len(pending_items) > 5:
                print(f"   ... and {len(pending_items) - 5} more pending items")
        
        # Check processing items
        if processing_items:
            print(f"\n🔄 PROCESSING ITEMS ({len(processing_items)} items):")
            print("-" * 50)
            for item in processing_items:
                pk = item.get('PK', 'unknown')
                updated_at = item.get('updated_at', item.get('created_at', 'unknown'))
                print(f"   PK: {pk} | Last updated: {updated_at}")
        
        # Check failed items
        if failed_items:
            print(f"\n❌ FAILED ITEMS ({len(failed_items)} items):")
            print("-" * 50)
            for item in failed_items:
                pk = item.get('PK', 'unknown')
                error_message = item.get('error_message', 'No error message')
                print(f"   PK: {pk}")
                print(f"   Error: {error_message}")
                print()
        
        # Analyze completed items and their SERP creation
        if completed_items:
            print(f"\n✅ COMPLETED ITEMS ANALYSIS ({len(completed_items)} items):")
            print("-" * 50)
            
            # Check how many SERP items were created from completed request acceptance items
            serp_table = QUEUE_TABLES.get('serp')
            if serp_table:
                serp_items = dynamodb_client.scan_items(
                    table_name=serp_table,
                    filter_expression="created_at >= :cutoff",
                    expression_attribute_values={":cutoff": cutoff_time}
                )
                
                print(f"   Request Acceptance completed: {len(completed_items)}")
                print(f"   SERP items created: {len(serp_items)}")
                print(f"   Expected ratio: 1 Request → Multiple SERP (depends on sources)")
                
                # Analyze SERP items by source
                serp_by_request = {}
                for serp_item in serp_items:
                    pk = serp_item.get('PK', '')
                    if pk:
                        # Extract request ID from PK
                        parts = pk.split('#')
                        if len(parts) >= 3:
                            request_key = f"{parts[1]}#{parts[2]}"
                            serp_by_request[request_key] = serp_by_request.get(request_key, 0) + 1
                
                if serp_by_request:
                    print(f"\n   📋 SERP Items per Request:")
                    for request_key, count in serp_by_request.items():
                        print(f"      {request_key}: {count} SERP items")
                else:
                    print(f"   ⚠️  No SERP items found with matching request IDs")
        
        # Overall assessment
        print(f"\n{'=' * 60}")
        print(f"🎯 OVERALL ASSESSMENT:")
        
        total_items = len(items)
        if total_items == 0:
            print("   ℹ️  No request acceptance items found in last 24 hours")
        else:
            pending_pct = (len(pending_items) / total_items) * 100
            processing_pct = (len(processing_items) / total_items) * 100
            failed_pct = (len(failed_items) / total_items) * 100
            completed_pct = (len(completed_items) / total_items) * 100
            
            print(f"   📊 Completion rate: {completed_pct:.1f}%")
            print(f"   📊 Failure rate: {failed_pct:.1f}%")
            print(f"   📊 Pending rate: {pending_pct:.1f}%")
            print(f"   📊 Processing rate: {processing_pct:.1f}%")
            
            if completed_pct < 80:
                print(f"   ⚠️  Low completion rate - check for processing issues")
            if failed_pct > 10:
                print(f"   ❌ High failure rate - check error messages")
            if pending_pct > 20:
                print(f"   ⏳ High pending rate - worker may not be running")
            if processing_pct > 10:
                print(f"   🔄 High processing rate - items may be stuck")
                
            if completed_pct >= 80 and failed_pct <= 10:
                print(f"   ✅ Request acceptance level looks healthy!")
            else:
                print(f"   ⚠️  Request acceptance level needs attention!")
        
    except Exception as e:
        print(f"❌ Error analyzing request acceptance: {str(e)}")
        logger.error(f"Error in request acceptance analysis: {str(e)}")

def check_request_acceptance_worker():
    """Check if request acceptance worker can be initialized"""
    print(f"\n🔧 REQUEST ACCEPTANCE WORKER TEST:")
    print("-" * 40)
    
    try:
        from app.queues.request_acceptance.worker import RequestAcceptanceWorker
        worker = RequestAcceptanceWorker()
        print(f"   ✅ Worker initialized successfully")
        print(f"   📋 Queue name: {worker.queue_name}")
        print(f"   📋 Table name: {worker.table_name}")
        print(f"   ⚙️  Poll interval: {worker.poll_interval}s")
        print(f"   📦 Batch size: {worker.batch_size}")
    except Exception as e:
        print(f"   ❌ Worker initialization failed: {str(e)}")

if __name__ == "__main__":
    check_request_acceptance_status()
    check_request_acceptance_worker() 