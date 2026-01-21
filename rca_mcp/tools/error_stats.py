"""
Error Statistics Tool
Extracts and analyzes error statistics from errors.json
"""

import json
import os
from typing import Dict, List, Optional
from collections import Counter, defaultdict
from datetime import datetime


def get_error_statistics(logs_path: str) -> str:
    """
    Get error statistics from errors.json file.
    
    Args:
        logs_path: Path to the RCA logs directory containing errors.json
    
    Returns:
        JSON string containing:
        - total_errors: Total number of errors
        - errors_by_category: Count of errors by category
        - errors_by_service: Count of errors by service
        - errors_by_time: Errors grouped by time periods
        - top_error_messages: Most common error messages
        - errors_by_severity: Errors grouped by severity (if available)
        - unique_requests: Number of unique request IDs with errors
        - timeline: List of errors with timestamps
    
    Example:
        >>> result = get_error_statistics("/path/to/rca_logs")
        >>> data = json.loads(result)
        >>> print(data["total_errors"])
    """
    try:
        errors_file = os.path.join(logs_path, "errors.json")
        
        if not os.path.exists(errors_file):
            error_result = {
                "error": "File not found",
                "message": f"errors.json not found at: {errors_file}",
                "logs_path": logs_path
            }
            return json.dumps(error_result, indent=2)
        
        with open(errors_file, 'r', encoding='utf-8') as f:
            errors_data = json.load(f)
        
        # Extract errors list
        errors = errors_data.get('errors', []) if isinstance(errors_data, dict) else errors_data
        if not isinstance(errors, list):
            errors = []
        
        # Initialize statistics
        total_errors = len(errors)
        errors_by_category = Counter()
        errors_by_service = Counter()
        errors_by_time = defaultdict(list)
        error_messages = []
        errors_by_severity = Counter()
        unique_requests = set()
        timeline = []
        
        # Process each error
        for error in errors:
            category = error.get('category', 'UNKNOWN')
            service = error.get('service', 'unknown')
            message = error.get('message', '')
            timestamp = error.get('timestamp') or error.get('time', '')
            severity = error.get('severity', 'UNKNOWN')
            request_id = error.get('request_id', '')
            
            errors_by_category[category] += 1
            errors_by_service[service] += 1
            errors_by_severity[severity] += 1
            
            if message:
                error_messages.append(message)
            
            if request_id:
                unique_requests.add(request_id)
            
            # Group by hour for time analysis
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour_key = dt.strftime('%Y-%m-%d %H:00')
                    errors_by_time[hour_key].append({
                        'timestamp': timestamp,
                        'service': service,
                        'category': category,
                        'message': message[:200]  # Truncate long messages
                    })
                except:
                    pass
            
            timeline.append({
                'timestamp': timestamp,
                'service': service,
                'category': category,
                'severity': severity,
                'message': message[:100] if message else '',
                'request_id': request_id
            })
        
        # Get top error messages
        message_counter = Counter(error_messages)
        top_error_messages = [{'message': msg, 'count': count} 
                             for msg, count in message_counter.most_common(10)]
        
        # Build result
        result = {
            "total_errors": total_errors,
            "errors_by_category": dict(errors_by_category),
            "errors_by_service": dict(errors_by_service),
            "errors_by_severity": dict(errors_by_severity),
            "unique_requests_with_errors": len(unique_requests),
            "top_error_messages": top_error_messages,
            "errors_by_time": {
                hour: {
                    'count': len(errors),
                    'errors': errors[:5]  # Limit to first 5 per hour
                }
                for hour, errors in sorted(errors_by_time.items())[:24]  # Last 24 hours
            },
            "timeline_summary": {
                'first_error': timeline[0]['timestamp'] if timeline else None,
                'last_error': timeline[-1]['timestamp'] if timeline else None,
                'error_count': len(timeline)
            },
            "status": "OK"
        }
        
        return json.dumps(result, indent=2, default=str)
    
    except json.JSONDecodeError as e:
        error_result = {
            "error": "JSON decode error",
            "message": f"Failed to parse errors.json: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to extract error statistics: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)
