"""
Service Statistics Tool
Extracts statistics from service log files
"""

import json
import os
import re
from typing import Dict, List, Optional
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def get_service_statistics(logs_path: str, service_name: Optional[str] = None) -> str:
    """
    Get service statistics from service log files.
    
    Args:
        logs_path: Path to the RCA logs directory containing service log files
        service_name: Optional specific service name to analyze (e.g., 'service-a')
    
    Returns:
        JSON string containing:
        - services_analyzed: List of services found
        - log_entries_by_service: Count of log entries per service
        - log_levels_by_service: Log levels distribution per service
        - errors_by_service: Error count per service
        - request_counts: Request counts per service
        - performance_metrics: Performance metrics extracted from logs
        - service_summary: Summary statistics per service
    
    Example:
        >>> result = get_service_statistics("/path/to/rca_logs")
        >>> data = json.loads(result)
        >>> print(data["services_analyzed"])
    """
    try:
        log_files = []
        service_pattern = r'service-(\w+)(?:-current|-previous)?\.log'
        
        # Find all service log files
        for file in os.listdir(logs_path):
            if re.match(service_pattern, file) or 'persistent-' in file:
                if service_name is None or service_name in file:
                    log_files.append(os.path.join(logs_path, file))
        
        if not log_files:
            error_result = {
                "error": "No log files found",
                "message": f"No service log files found in: {logs_path}",
                "logs_path": logs_path
            }
            return json.dumps(error_result, indent=2)
        
        # Statistics containers
        services_analyzed = []
        log_entries_by_service = Counter()
        log_levels_by_service = defaultdict(Counter)
        errors_by_service = Counter()
        request_counts = Counter()
        performance_metrics = defaultdict(list)
        service_info = defaultdict(dict)
        
        # Log level patterns
        log_level_pattern = re.compile(r'\b(INFO|ERROR|WARN|WARNING|DEBUG|TRACE|FATAL)\b', re.IGNORECASE)
        # Request ID patterns
        request_id_pattern = re.compile(r'req=([a-f0-9\-]{36})', re.IGNORECASE)
        # Performance patterns (latency, duration)
        perf_patterns = {
            'latency': re.compile(r'latency_ms=([\d.]+)', re.IGNORECASE),
            'duration': re.compile(r'duration_ms=([\d.]+)', re.IGNORECASE),
            'status': re.compile(r'status=(\d{3})', re.IGNORECASE)
        }
        
        # Process each log file
        for log_file in log_files:
            # Extract service name from filename
            filename = os.path.basename(log_file)
            service_match = re.search(service_pattern, filename)
            if service_match:
                service_name_from_file = service_match.group(1)
            elif 'persistent-' in filename:
                service_name_from_file = filename.replace('persistent-', '').replace('.log', '')
            else:
                service_name_from_file = filename.replace('.log', '')
            
            if service_name_from_file not in services_analyzed:
                services_analyzed.append(service_name_from_file)
            
            # Read and analyze log file
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                entry_count = 0
                error_count = 0
                request_ids_found = set()
                
                for line in lines:
                    entry_count += 1
                    
                    # Extract log level
                    level_match = log_level_pattern.search(line)
                    if level_match:
                        level = level_match.group(1).upper()
                        log_levels_by_service[service_name_from_file][level] += 1
                        
                        if level in ['ERROR', 'FATAL']:
                            error_count += 1
                    
                    # Extract request IDs
                    req_match = request_id_pattern.search(line)
                    if req_match:
                        req_id = req_match.group(1)
                        request_ids_found.add(req_id)
                    
                    # Extract performance metrics
                    for metric_name, pattern in perf_patterns.items():
                        match = pattern.search(line)
                        if match:
                            try:
                                value = float(match.group(1))
                                performance_metrics[f"{service_name_from_file}_{metric_name}"].append(value)
                            except:
                                pass
                
                log_entries_by_service[service_name_from_file] = entry_count
                errors_by_service[service_name_from_file] = error_count
                request_counts[service_name_from_file] = len(request_ids_found)
                
                # Calculate performance statistics
                service_perf = {}
                for metric_key, values in performance_metrics.items():
                    if service_name_from_file in metric_key:
                        if values:
                            service_perf[metric_key.replace(f"{service_name_from_file}_", "")] = {
                                'count': len(values),
                                'min': round(min(values), 2),
                                'max': round(max(values), 2),
                                'avg': round(sum(values) / len(values), 2),
                                'p95': round(sorted(values)[int(len(values) * 0.95)], 2) if len(values) > 20 else None
                            }
                
                service_info[service_name_from_file] = {
                    'log_file': filename,
                    'total_entries': entry_count,
                    'errors': error_count,
                    'unique_requests': len(request_ids_found),
                    'error_rate': round((error_count / entry_count * 100), 2) if entry_count > 0 else 0,
                    'performance': service_perf
                }
            
            except Exception as e:
                service_info[service_name_from_file] = {
                    'log_file': filename,
                    'error': f"Failed to process: {str(e)}"
                }
        
        # Build result
        result = {
            "services_analyzed": services_analyzed,
            "log_entries_by_service": dict(log_entries_by_service),
            "log_levels_by_service": {
                service: dict(levels) for service, levels in log_levels_by_service.items()
            },
            "errors_by_service": dict(errors_by_service),
            "request_counts": dict(request_counts),
            "service_summary": dict(service_info),
            "total_services": len(services_analyzed),
            "total_log_entries": sum(log_entries_by_service.values()),
            "total_errors": sum(errors_by_service.values()),
            "status": "OK"
        }
        
        return json.dumps(result, indent=2, default=str)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to extract service statistics: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)
