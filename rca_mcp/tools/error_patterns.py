"""
Error Patterns Analysis Tool
Analyzes error patterns and correlations from logs
"""

import json
import os
import re
from typing import Dict, List, Optional
from collections import defaultdict, Counter
from datetime import datetime


def analyze_error_patterns(logs_path: str) -> str:
    """
    Analyze error patterns and correlations from logs.
    
    Args:
        logs_path: Path to the RCA logs directory
    
    Returns:
        JSON string containing:
        - error_categories: Error categories and their counts
        - error_sequences: Common error sequences
        - error_correlations: Correlations between errors and services
        - error_frequency: Error frequency over time
        - root_cause_candidates: Potential root cause indicators
        - error_message_clusters: Clustered error messages
    
    Example:
        >>> result = analyze_error_patterns("/path/to/rca_logs")
        >>> data = json.loads(result)
        >>> print(data["error_categories"])
    """
    try:
        # Load errors.json if available
        errors_data = []
        errors_file = os.path.join(logs_path, "errors.json")
        if os.path.exists(errors_file):
            with open(errors_file, 'r', encoding='utf-8') as f:
                errors_json = json.load(f)
                errors_data = errors_json.get('errors', []) if isinstance(errors_json, dict) else errors_json
        
        # Extract errors from log files
        error_pattern = re.compile(r'(ERROR|FATAL|CRITICAL)[^:]*:\s*(.+)', re.IGNORECASE)
        stack_trace_pattern = re.compile(r'(Traceback|Exception|Error):', re.IGNORECASE)
        
        error_events = []
        service_errors = defaultdict(list)
        
        # Process log files
        for file in os.listdir(logs_path):
            if file.endswith('.log'):
                filepath = os.path.join(logs_path, file)
                service_name = file.replace('-current.log', '').replace('-previous.log', '').replace('.log', '')
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    for line_num, line in enumerate(lines, 1):
                        # Check for error messages
                        error_match = error_pattern.search(line)
                        if error_match:
                            error_level = error_match.group(1).upper()
                            error_message = error_match.group(2).strip()[:200]  # Truncate
                            
                            error_events.append({
                                'service': service_name,
                                'level': error_level,
                                'message': error_message,
                                'line': line_num,
                                'timestamp': _extract_timestamp(line),
                                'has_stack_trace': bool(stack_trace_pattern.search(line))
                            })
                            
                            service_errors[service_name].append({
                                'message': error_message,
                                'timestamp': _extract_timestamp(line)
                            })
                
                except Exception:
                    continue
        
        # Merge with errors.json data
        for error in errors_data:
            if isinstance(error, dict):
                error_events.append({
                    'service': error.get('service', 'unknown'),
                    'level': 'ERROR',
                    'message': error.get('message', '')[:200],
                    'category': error.get('category'),
                    'timestamp': error.get('timestamp') or error.get('time'),
                    'request_id': error.get('request_id')
                })
        
        # Analyze patterns
        error_categories = Counter()
        error_messages = Counter()
        service_error_counts = Counter()
        error_time_distribution = defaultdict(int)
        error_sequences = []
        
        # Extract error categories
        category_patterns = {
            'TIMEOUT': re.compile(r'timeout|timed out|deadline exceeded', re.IGNORECASE),
            'CONNECTION': re.compile(r'connection|network|socket', re.IGNORECASE),
            'VALIDATION': re.compile(r'validation|invalid|bad request', re.IGNORECASE),
            'AUTHENTICATION': re.compile(r'auth|unauthorized|forbidden|permission', re.IGNORECASE),
            'RESOURCE': re.compile(r'resource|not found|404|500', re.IGNORECASE),
            'DATABASE': re.compile(r'database|db|sql|query', re.IGNORECASE),
            'MEMORY': re.compile(r'memory|oom|out of memory', re.IGNORECASE),
            'CRASH': re.compile(r'crash|failed|terminated|restore', re.IGNORECASE),
            'NAME_ERROR': re.compile(r'name.*not defined|undefined', re.IGNORECASE)
        }
        
        for event in error_events:
            service = event['service']
            message = event['message']
            timestamp = event.get('timestamp')
            
            service_error_counts[service] += 1
            error_messages[message] += 1
            
            # Categorize error
            category = 'UNKNOWN'
            for cat_name, pattern in category_patterns.items():
                if pattern.search(message):
                    category = cat_name
                    break
            error_categories[category] += 1
            
            # Time distribution
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour_key = dt.strftime('%Y-%m-%d %H:00')
                    error_time_distribution[hour_key] += 1
                except:
                    pass
        
        # Find error sequences (errors happening close together)
        if len(error_events) > 1:
            sorted_events = sorted(
                [e for e in error_events if e.get('timestamp')],
                key=lambda x: x.get('timestamp', '')
            )
            
            for i in range(len(sorted_events) - 1):
                current = sorted_events[i]
                next_event = sorted_events[i + 1]
                
                if current.get('timestamp') and next_event.get('timestamp'):
                    try:
                        current_dt = datetime.fromisoformat(current['timestamp'].replace('Z', '+00:00'))
                        next_dt = datetime.fromisoformat(next_event['timestamp'].replace('Z', '+00:00'))
                        time_diff = (next_dt - current_dt).total_seconds()
                        
                        if time_diff < 10:  # Within 10 seconds
                            error_sequences.append({
                                'first_service': current['service'],
                                'first_message': current['message'][:100],
                                'second_service': next_event['service'],
                                'second_message': next_event['message'][:100],
                                'time_gap_seconds': round(time_diff, 2)
                            })
                    except:
                        pass
        
        # Error message clusters (similar messages)
        message_clusters = defaultdict(list)
        for message, count in error_messages.most_common(50):
            # Normalize message for clustering
            normalized = re.sub(r'\d+', 'N', message.lower())
            normalized = re.sub(r'[a-f0-9\-]{36}', 'UUID', normalized)  # Replace UUIDs
            message_clusters[normalized[:50]].append({'message': message[:100], 'count': count})
        
        # Build result
        result = {
            "total_errors_analyzed": len(error_events),
            "error_categories": dict(error_categories),
            "top_error_messages": [
                {'message': msg[:200], 'count': count}
                for msg, count in error_messages.most_common(20)
            ],
            "service_error_counts": dict(service_error_counts),
            "error_time_distribution": dict(sorted(error_time_distribution.items())),
            "error_sequences": error_sequences[:20],  # Limit to 20 sequences
            "error_message_clusters": {
                cluster[:50]: messages[:5]  # Top 5 messages per cluster
                for cluster, messages in list(message_clusters.items())[:20]
            },
            "root_cause_candidates": {
                'most_frequent_category': error_categories.most_common(1)[0][0] if error_categories else None,
                'most_affected_service': service_error_counts.most_common(1)[0][0] if service_error_counts else None,
                'error_burst_time': max(error_time_distribution.items(), key=lambda x: x[1])[0] if error_time_distribution else None
            },
            "status": "OK"
        }
        
        return json.dumps(result, indent=2, default=str)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to analyze error patterns: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)


def _extract_timestamp(line: str) -> Optional[str]:
    """Extract timestamp from log line."""
    timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)')
    match = timestamp_pattern.search(line)
    return match.group(1) if match else None
