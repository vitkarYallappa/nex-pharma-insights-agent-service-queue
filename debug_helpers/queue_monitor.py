#!/usr/bin/env python3
"""
Queue Processing Monitor
Helps diagnose SERP → Perplexity → Insight/Implication queue processing issues
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


class QueueMonitor:
    """Monitor queue processing ratios and identify issues"""
    
    def __init__(self):
        self.tables = QUEUE_TABLES
        
    def get_queue_counts(self, hours_back: int = 24) -> Dict[str, Dict[str, int]]:
        """Get queue item counts by status for the last N hours"""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
        
        results = {}
        
        for queue_name, table_name in self.tables.items():
            try:
                # Get all items from the last N hours
                items = dynamodb_client.scan_items(
                    table_name=table_name,
                    filter_expression="created_at >= :cutoff",
                    expression_attribute_values={":cutoff": cutoff_time}
                )
                
                # Count by status
                status_counts = {
                    'pending': 0,
                    'processing': 0,
                    'completed': 0,
                    'failed': 0,
                    'total': len(items)
                }
                
                for item in items:
                    status = item.get('status', 'unknown')
                    if status in status_counts:
                        status_counts[status] += 1
                
                results[queue_name] = status_counts
                
            except Exception as e:
                logger.error(f"Failed to get counts for {queue_name}: {str(e)}")
                results[queue_name] = {'error': str(e)}
        
        return results
    
    def analyze_serp_to_perplexity_ratio(self, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze the SERP to Perplexity processing ratio"""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
        
        try:
            # Get completed SERP items
            serp_items = dynamodb_client.scan_items(
                table_name=self.tables['serp'],
                filter_expression="created_at >= :cutoff AND #status = :status",
                expression_attribute_names={"#status": "status"},
                expression_attribute_values={
                    ":cutoff": cutoff_time,
                    ":status": "completed"
                }
            )
            
            # Get all Perplexity items (any status)
            perplexity_items = dynamodb_client.scan_items(
                table_name=self.tables['perplexity'],
                filter_expression="created_at >= :cutoff",
                expression_attribute_values={":cutoff": cutoff_time}
            )
            
            # Analyze by project/request
            serp_by_request = {}
            perplexity_by_request = {}
            
            # Group SERP items by request
            for item in serp_items:
                pk = item.get('PK', '')
                if pk:
                    # Extract project_id and request_id from PK
                    parts = pk.split('#')
                    if len(parts) >= 3:
                        request_key = f"{parts[1]}#{parts[2]}"  # project_id#request_id
                        serp_by_request[request_key] = serp_by_request.get(request_key, 0) + 1
            
            # Group Perplexity items by request
            for item in perplexity_items:
                pk = item.get('PK', '')
                status = item.get('status', 'unknown')
                if pk:
                    parts = pk.split('#')
                    if len(parts) >= 3:
                        request_key = f"{parts[1]}#{parts[2]}"
                        if request_key not in perplexity_by_request:
                            perplexity_by_request[request_key] = {'total': 0, 'completed': 0, 'failed': 0, 'pending': 0, 'processing': 0}
                        perplexity_by_request[request_key]['total'] += 1
                        if status in perplexity_by_request[request_key]:
                            perplexity_by_request[request_key][status] += 1
            
            # Calculate ratios
            analysis = {
                'total_serp_completed': len(serp_items),
                'total_perplexity_items': len(perplexity_items),
                'expected_perplexity_items': len(serp_items) * 3,  # Should be 3x SERP items
                'ratio_analysis': [],
                'summary': {}
            }
            
            # Analyze each request
            for request_key in serp_by_request:
                serp_count = serp_by_request[request_key]
                perplexity_data = perplexity_by_request.get(request_key, {'total': 0, 'completed': 0, 'failed': 0})
                expected_perplexity = serp_count * 3
                
                analysis['ratio_analysis'].append({
                    'request': request_key,
                    'serp_completed': serp_count,
                    'perplexity_total': perplexity_data['total'],
                    'perplexity_completed': perplexity_data['completed'],
                    'perplexity_failed': perplexity_data['failed'],
                    'expected_perplexity': expected_perplexity,
                    'ratio_achieved': perplexity_data['total'] / serp_count if serp_count > 0 else 0,
                    'ratio_expected': 3.0,
                    'missing_perplexity': max(0, expected_perplexity - perplexity_data['total'])
                })
            
            # Calculate summary statistics
            total_missing = analysis['expected_perplexity_items'] - analysis['total_perplexity_items']
            actual_ratio = analysis['total_perplexity_items'] / analysis['total_serp_completed'] if analysis['total_serp_completed'] > 0 else 0
            
            analysis['summary'] = {
                'overall_ratio': actual_ratio,
                'expected_ratio': 3.0,
                'total_missing_perplexity': total_missing,
                'success_rate': (analysis['total_perplexity_items'] / analysis['expected_perplexity_items'] * 100) if analysis['expected_perplexity_items'] > 0 else 0
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze SERP to Perplexity ratio: {str(e)}")
            return {'error': str(e)}
    
    def print_queue_status_report(self, hours_back: int = 24):
        """Print a comprehensive queue status report"""
        print(f"\n{'='*60}")
        print(f"QUEUE PROCESSING REPORT - Last {hours_back} hours")
        print(f"{'='*60}")
        
        # Get queue counts
        counts = self.get_queue_counts(hours_back)
        
        print(f"\n📊 QUEUE STATUS SUMMARY:")
        print(f"{'Queue':<15} {'Total':<8} {'Completed':<10} {'Failed':<8} {'Pending':<8} {'Processing':<10}")
        print(f"{'-'*60}")
        
        for queue_name, data in counts.items():
            if 'error' in data:
                print(f"{queue_name:<15} ERROR: {data['error']}")
            else:
                print(f"{queue_name:<15} {data['total']:<8} {data['completed']:<10} {data['failed']:<8} {data['pending']:<8} {data['processing']:<10}")
        
        # Analyze SERP → Perplexity ratio
        print(f"\n🔍 SERP → PERPLEXITY RATIO ANALYSIS:")
        print(f"{'-'*60}")
        
        ratio_analysis = self.analyze_serp_to_perplexity_ratio(hours_back)
        
        if 'error' in ratio_analysis:
            print(f"ERROR: {ratio_analysis['error']}")
        else:
            summary = ratio_analysis['summary']
            print(f"Total SERP completed: {ratio_analysis['total_serp_completed']}")
            print(f"Total Perplexity items: {ratio_analysis['total_perplexity_items']}")
            print(f"Expected Perplexity items: {ratio_analysis['expected_perplexity_items']}")
            print(f"Actual ratio: {summary['overall_ratio']:.2f} (expected: 3.0)")
            print(f"Success rate: {summary['success_rate']:.1f}%")
            print(f"Missing Perplexity items: {summary['total_missing_perplexity']}")
            
            if summary['success_rate'] < 90:
                print(f"\n⚠️  WARNING: Success rate is below 90%!")
                print(f"   This indicates issues in SERP → Perplexity processing")
            
            # Show per-request breakdown if there are issues
            if summary['total_missing_perplexity'] > 0:
                print(f"\n📋 PER-REQUEST BREAKDOWN:")
                print(f"{'Request':<25} {'SERP':<6} {'Perplexity':<10} {'Expected':<9} {'Missing':<8} {'Ratio':<6}")
                print(f"{'-'*70}")
                
                for item in ratio_analysis['ratio_analysis']:
                    if item['missing_perplexity'] > 0:
                        print(f"{item['request']:<25} {item['serp_completed']:<6} {item['perplexity_total']:<10} {item['expected_perplexity']:<9} {item['missing_perplexity']:<8} {item['ratio_achieved']:.1f}")
        
        print(f"\n{'='*60}")


def main():
    """Main function to run the queue monitor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor queue processing ratios')
    parser.add_argument('--hours', type=int, default=24, help='Hours back to analyze (default: 24)')
    args = parser.parse_args()
    
    monitor = QueueMonitor()
    monitor.print_queue_status_report(args.hours)


if __name__ == "__main__":
    main() 