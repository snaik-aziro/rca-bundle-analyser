"""
Timeline Statistics Tool
Extracts and analyzes timeline statistics from timeline.json
"""

import json
import os
from typing import Dict, List, Optional
from collections import Counter, defaultdict
from datetime import datetime


def get_timeline_statistics(logs_path: str) -> str:
    """
    Get timeline statistics from timeline.json file.
    
    Args:
        logs_path: Path to the RCA logs directory containing timeline.json
    
    Returns:
        JSON string containing:
        - total_events: Total number of events
        - events_by_service: Count of events by service
        - events_by_level: Count of events by log level (INFO, ERROR, etc.)
        - events_by_time: Events grouped by time periods
        - request_distribution: Distribution of requests across services
        - event_types: Different types of events found
        - timeline_summary: Summary of timeline (first/last event, duration)
    
    Example:
        >>> result = get_timeline_statistics("/path/to/rca_logs")
        >>> data = json.loads(result)
        >>> print(data["total_events"])
    """
    try:
        timeline_file = os.path.join(logs_path, "timeline.json")
        
        if not os.path.exists(timeline_file):
            error_result = {
                "error": "File not found",
                "message": f"timeline.json not found at: {timeline_file}",
                "logs_path": logs_path
            }
            return json.dumps(error_result, indent=2)
        
        with open(timeline_file, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)
        
        # Extract timeline list
        timeline = timeline_data.get('timeline', []) if isinstance(timeline_data, dict) else timeline_data
        if not isinstance(timeline, list):
            timeline = []
        
        # Initialize statistics
        total_events = len(timeline)
        events_by_service = Counter()
        events_by_level = Counter()
        events_by_time = defaultdict(list)
        events_by_type = Counter()
        request_ids = set()
        request_distribution = defaultdict(int)
        
        # Process each event
        first_timestamp = None
        last_timestamp = None
        
        for event in timeline:
            service = event.get('service', 'unknown')
            level = event.get('level', 'UNKNOWN')
            event_type = event.get('event', 'log_entry')
            timestamp = event.get('timestamp', '')
            request_id = event.get('request_id', '-')
            
            events_by_service[service] += 1
            events_by_level[level] += 1
            events_by_type[event_type] += 1
            
            if request_id and request_id != '-':
                request_ids.add(request_id)
                request_distribution[service] += 1
            
            # Group by hour for time analysis
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour_key = dt.strftime('%Y-%m-%d %H:00')
                    events_by_time[hour_key].append({
                        'timestamp': timestamp,
                        'service': service,
                        'level': level,
                        'event': event_type
                    })
                    
                    if not first_timestamp:
                        first_timestamp = timestamp
                    last_timestamp = timestamp
                except:
                    pass
        
        # Calculate duration if timestamps available
        duration_seconds = None
        if first_timestamp and last_timestamp:
            try:
                first_dt = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
                last_dt = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
                duration_seconds = (last_dt - first_dt).total_seconds()
            except:
                pass
        
        # Build result
        result = {
            "total_events": total_events,
            "events_by_service": dict(events_by_service),
            "events_by_level": dict(events_by_level),
            "events_by_type": dict(events_by_type),
            "unique_requests": len(request_ids),
            "request_distribution": dict(request_distribution),
            "events_by_time": {
                hour: {
                    'count': len(events),
                    'events': events[:10]  # Limit to first 10 per hour
                }
                for hour, events in sorted(events_by_time.items())
            },
            "timeline_summary": {
                'first_event': first_timestamp,
                'last_event': last_timestamp,
                'duration_seconds': duration_seconds,
                'duration_formatted': f"{duration_seconds/60:.1f} minutes" if duration_seconds else None,
                'events_per_minute': round(total_events / (duration_seconds/60), 2) if duration_seconds and duration_seconds > 0 else None
            },
            "status": "OK"
        }
        
        return json.dumps(result, indent=2, default=str)
    
    except json.JSONDecodeError as e:
        error_result = {
            "error": "JSON decode error",
            "message": f"Failed to parse timeline.json: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to extract timeline statistics: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)
