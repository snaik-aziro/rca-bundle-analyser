"""
Request Patterns Tool
Extracts request patterns and metrics from logs
"""

import json
import os
import re
from typing import Dict, List, Optional
from collections import defaultdict, Counter
from datetime import datetime


def get_request_patterns(logs_path: str) -> str:
    """
    Get request patterns and metrics from logs.
    
    Args:
        logs_path: Path to the RCA logs directory
    
    Returns:
        JSON string containing:
        - total_requests: Total number of requests
        - requests_by_service: Request counts per service
        - requests_by_endpoint: Request counts by endpoint
        - requests_by_method: Request counts by HTTP method
        - request_latency_stats: Latency statistics
        - request_status_distribution: Status code distribution
        - request_timeline: Request timeline data
        - failed_requests: Information about failed requests
    
    Example:
        >>> result = get_request_patterns("/path/to/rca_logs")
        >>> data = json.loads(result)
        >>> print(data["total_requests"])
    """
    try:
        # Patterns for extracting request data
        request_start_pattern = re.compile(r'\[REQUEST_START\]\s+endpoint=([^\s]+)\s+method=([A-Z]+)')
        request_complete_pattern = re.compile(
            r'\[REQUEST_COMPLETE\]\s+endpoint=([^\s]+)\s+method=([A-Z]+)\s+duration_ms=([\d.]+)\s+status=(\d{3})'
        )
        request_id_pattern = re.compile(r'req=([a-f0-9\-]{36})', re.IGNORECASE)
        latency_pattern = re.compile(r'latency_ms=([\d.]+)', re.IGNORECASE)
        
        # Collect data from all log files
        request_data = []
        services_found = set()
        
        # Process service log files
        for file in os.listdir(logs_path):
            if file.endswith('.log'):
                filepath = os.path.join(logs_path, file)
                service_name = file.replace('-current.log', '').replace('-previous.log', '').replace('.log', '')
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            # Extract request start
                            start_match = request_start_pattern.search(line)
                            if start_match:
                                endpoint = start_match.group(1)
                                method = start_match.group(2)
                                req_id_match = request_id_pattern.search(line)
                                req_id = req_id_match.group(1) if req_id_match else None
                                
                                request_data.append({
                                    'type': 'start',
                                    'service': service_name,
                                    'request_id': req_id,
                                    'endpoint': endpoint,
                                    'method': method,
                                    'line': line_num,
                                    'timestamp': _extract_timestamp(line)
                                })
                                services_found.add(service_name)
                            
                            # Extract request complete
                            complete_match = request_complete_pattern.search(line)
                            if complete_match:
                                endpoint = complete_match.group(1)
                                method = complete_match.group(2)
                                duration = float(complete_match.group(3))
                                status = int(complete_match.group(4))
                                req_id_match = request_id_pattern.search(line)
                                req_id = req_id_match.group(1) if req_id_match else None
                                
                                request_data.append({
                                    'type': 'complete',
                                    'service': service_name,
                                    'request_id': req_id,
                                    'endpoint': endpoint,
                                    'method': method,
                                    'duration_ms': duration,
                                    'status': status,
                                    'line': line_num,
                                    'timestamp': _extract_timestamp(line)
                                })
                                services_found.add(service_name)
                            
                            # Extract latency info
                            latency_match = latency_pattern.search(line)
                            if latency_match and req_id_match:
                                latency = float(latency_match.group(1))
                                req_id = req_id_match.group(1)
                                request_data.append({
                                    'type': 'latency',
                                    'service': service_name,
                                    'request_id': req_id,
                                    'latency_ms': latency,
                                    'timestamp': _extract_timestamp(line)
                                })
                
                except Exception as e:
                    continue
        
        # Analyze request data
        requests_by_service = Counter()
        requests_by_endpoint = Counter()
        requests_by_method = Counter()
        request_latencies = []
        status_distribution = Counter()
        failed_requests = []
        
        # Group requests by ID
        requests_by_id = defaultdict(list)
        for req in request_data:
            if req.get('request_id'):
                requests_by_id[req['request_id']].append(req)
        
        # Process requests
        for req_id, req_events in requests_by_id.items():
            start_event = next((e for e in req_events if e['type'] == 'start'), None)
            complete_event = next((e for e in req_events if e['type'] == 'complete'), None)
            
            if start_event:
                service = start_event['service']
                endpoint = start_event['endpoint']
                method = start_event['method']
                
                requests_by_service[service] += 1
                requests_by_endpoint[endpoint] += 1
                requests_by_method[method] += 1
            
            if complete_event:
                duration = complete_event.get('duration_ms')
                status = complete_event.get('status')
                
                if duration:
                    request_latencies.append(duration)
                
                if status:
                    status_distribution[status] += 1
                    
                    if status >= 400:
                        failed_requests.append({
                            'request_id': req_id,
                            'service': complete_event.get('service'),
                            'endpoint': complete_event.get('endpoint'),
                            'method': complete_event.get('method'),
                            'status': status,
                            'duration_ms': duration
                        })
        
        # Calculate latency statistics
        latency_stats = {}
        if request_latencies:
            sorted_latencies = sorted(request_latencies)
            latency_stats = {
                'count': len(request_latencies),
                'min': round(min(request_latencies), 2),
                'max': round(max(request_latencies), 2),
                'avg': round(sum(request_latencies) / len(request_latencies), 2),
                'median': round(sorted_latencies[len(sorted_latencies) // 2], 2),
                'p95': round(sorted_latencies[int(len(sorted_latencies) * 0.95)], 2) if len(sorted_latencies) > 20 else None,
                'p99': round(sorted_latencies[int(len(sorted_latencies) * 0.99)], 2) if len(sorted_latencies) > 100 else None
            }
        
        # Build result
        result = {
            "total_requests": len(requests_by_id),
            "services_with_requests": list(services_found),
            "requests_by_service": dict(requests_by_service),
            "requests_by_endpoint": dict(requests_by_endpoint.most_common(20)),
            "requests_by_method": dict(requests_by_method),
            "request_latency_stats": latency_stats,
            "status_distribution": dict(status_distribution),
            "failed_requests_count": len(failed_requests),
            "failed_requests": failed_requests[:50],  # Limit to first 50
            "success_rate": round(
                (status_distribution[200] / sum(status_distribution.values()) * 100), 2
            ) if status_distribution else None,
            "status": "OK"
        }
        
        return json.dumps(result, indent=2, default=str)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to extract request patterns: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)


def _extract_timestamp(line: str) -> Optional[str]:
    """Extract timestamp from log line."""
    timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)')
    match = timestamp_pattern.search(line)
    return match.group(1) if match else None
