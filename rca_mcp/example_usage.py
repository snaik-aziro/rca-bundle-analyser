"""
Example usage of RCA MCP Tools

This script demonstrates how to use the RCA MCP tools to analyze log bundles.
"""

import json
import sys
import os

# Add the parent directory to the path to import tools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rca_mcp.tools.error_stats import get_error_statistics
from rca_mcp.tools.timeline_stats import get_timeline_statistics
from rca_mcp.tools.service_stats import get_service_statistics
from rca_mcp.tools.request_patterns import get_request_patterns
from rca_mcp.tools.error_patterns import analyze_error_patterns
from rca_mcp.tools.metadata_extractor import extract_metadata
from rca_mcp.tools.log_analyzer import analyze_logs


def main():
    """Example usage of RCA MCP tools."""
    
    # Path to RCA logs directory
    logs_path = "/Users/sagar.naik/Downloads/rca_logs_20251216T162338Z"
    
    if not os.path.exists(logs_path):
        print(f"Error: Logs path not found: {logs_path}")
        print("Please update the logs_path variable with a valid path.")
        return
    
    print("=" * 60)
    print("RCA MCP Tools - Example Usage")
    print("=" * 60)
    
    # 1. Extract metadata
    print("\n1. Extracting metadata...")
    metadata_json = extract_metadata(logs_path)
    metadata = json.loads(metadata_json)
    if 'error' not in metadata:
        print(f"   Scenario: {metadata.get('scenario_type')}")
        print(f"   Timestamp: {metadata.get('timestamp_utc')}")
        print(f"   Namespace: {metadata.get('namespace')}")
        print(f"   Files: {metadata.get('files_included')}")
        print(f"   Errors: {metadata.get('errors_found')}")
    else:
        print(f"   Error: {metadata.get('message')}")
    
    # 2. Get error statistics
    print("\n2. Analyzing error statistics...")
    error_stats_json = get_error_statistics(logs_path)
    error_stats = json.loads(error_stats_json)
    if 'error' not in error_stats:
        print(f"   Total Errors: {error_stats.get('total_errors')}")
        print(f"   Errors by Category: {error_stats.get('errors_by_category')}")
        print(f"   Errors by Service: {error_stats.get('errors_by_service')}")
        print(f"   Unique Requests with Errors: {error_stats.get('unique_requests_with_errors')}")
    else:
        print(f"   Error: {error_stats.get('message')}")
    
    # 3. Get timeline statistics
    print("\n3. Analyzing timeline statistics...")
    timeline_stats_json = get_timeline_statistics(logs_path)
    timeline_stats = json.loads(timeline_stats_json)
    if 'error' not in timeline_stats:
        print(f"   Total Events: {timeline_stats.get('total_events')}")
        print(f"   Events by Service: {timeline_stats.get('events_by_service')}")
        print(f"   Events by Level: {timeline_stats.get('events_by_level')}")
        print(f"   Unique Requests: {timeline_stats.get('unique_requests')}")
    else:
        print(f"   Error: {timeline_stats.get('message')}")
    
    # 4. Get service statistics
    print("\n4. Analyzing service statistics...")
    service_stats_json = get_service_statistics(logs_path)
    service_stats = json.loads(service_stats_json)
    if 'error' not in service_stats:
        print(f"   Services Analyzed: {service_stats.get('services_analyzed')}")
        print(f"   Total Log Entries: {service_stats.get('total_log_entries')}")
        print(f"   Total Errors: {service_stats.get('total_errors')}")
        print(f"   Errors by Service: {service_stats.get('errors_by_service')}")
    else:
        print(f"   Error: {service_stats.get('message')}")
    
    # 5. Analyze request patterns
    print("\n5. Analyzing request patterns...")
    request_patterns_json = get_request_patterns(logs_path)
    request_patterns = json.loads(request_patterns_json)
    if 'error' not in request_patterns:
        print(f"   Total Requests: {request_patterns.get('total_requests')}")
        print(f"   Requests by Service: {request_patterns.get('requests_by_service')}")
        print(f"   Success Rate: {request_patterns.get('success_rate')}%")
        latency_stats = request_patterns.get('request_latency_stats', {})
        if latency_stats:
            print(f"   Avg Latency: {latency_stats.get('avg')}ms")
            print(f"   P95 Latency: {latency_stats.get('p95')}ms")
    else:
        print(f"   Error: {request_patterns.get('message')}")
    
    # 6. Analyze error patterns
    print("\n6. Analyzing error patterns...")
    error_patterns_json = analyze_error_patterns(logs_path)
    error_patterns = json.loads(error_patterns_json)
    if 'error' not in error_patterns:
        print(f"   Total Errors Analyzed: {error_patterns.get('total_errors_analyzed')}")
        print(f"   Error Categories: {error_patterns.get('error_categories')}")
        root_cause = error_patterns.get('root_cause_candidates', {})
        print(f"   Most Frequent Category: {root_cause.get('most_frequent_category')}")
        print(f"   Most Affected Service: {root_cause.get('most_affected_service')}")
    else:
        print(f"   Error: {error_patterns.get('message')}")
    
    # 7. Comprehensive analysis
    print("\n7. Performing comprehensive analysis...")
    analysis_json = analyze_logs(logs_path)
    analysis = json.loads(analysis_json)
    if 'error' not in analysis:
        summary = analysis.get('summary', {})
        print(f"   Scenario: {summary.get('scenario')}")
        print(f"   Total Errors: {summary.get('total_errors')}")
        print(f"   Total Events: {summary.get('total_events')}")
        print(f"   Services Affected: {summary.get('services_affected')}")
        print(f"   Error Rate: {summary.get('error_rate')}%")
        print(f"   Most Critical Service: {summary.get('most_critical_service')}")
        print(f"   Primary Error Category: {summary.get('primary_error_category')}")
    else:
        print(f"   Error: {analysis.get('message')}")
    
    print("\n" + "=" * 60)
    print("Analysis Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
