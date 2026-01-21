"""
Log Analyzer Tool
Comprehensive log analysis combining multiple data sources
"""

import json
import os
from typing import Dict, Optional
from .error_stats import get_error_statistics
from .timeline_stats import get_timeline_statistics
from .service_stats import get_service_statistics
from .request_patterns import get_request_patterns
from .error_patterns import analyze_error_patterns
from .metadata_extractor import extract_metadata


def analyze_logs(logs_path: str) -> str:
    """
    Perform comprehensive log analysis combining all data sources.
    
    Args:
        logs_path: Path to the RCA logs directory
    
    Returns:
        JSON string containing comprehensive analysis:
        - metadata: Metadata information
        - error_analysis: Error statistics and patterns
        - timeline_analysis: Timeline statistics
        - service_analysis: Service statistics
        - request_analysis: Request patterns and metrics
        - summary: Overall summary and insights
    
    Example:
        >>> result = analyze_logs("/path/to/rca_logs")
        >>> data = json.loads(result)
        >>> print(data["summary"])
    """
    try:
        # Collect all analyses
        metadata_str = extract_metadata(logs_path)
        error_stats_str = get_error_statistics(logs_path)
        timeline_stats_str = get_timeline_statistics(logs_path)
        service_stats_str = get_service_statistics(logs_path)
        request_patterns_str = get_request_patterns(logs_path)
        error_patterns_str = analyze_error_patterns(logs_path)
        
        # Parse JSON results
        metadata = json.loads(metadata_str)
        error_stats = json.loads(error_stats_str)
        timeline_stats = json.loads(timeline_stats_str)
        service_stats = json.loads(service_stats_str)
        request_patterns = json.loads(request_patterns_str)
        error_patterns = json.loads(error_patterns_str)
        
        # Build comprehensive summary
        summary = {
            "scenario": metadata.get('scenario_type', 'unknown'),
            "timestamp": metadata.get('timestamp_utc'),
            "namespace": metadata.get('namespace'),
            "total_errors": error_stats.get('total_errors', 0) if 'error' not in error_stats else 0,
            "total_events": timeline_stats.get('total_events', 0) if 'error' not in timeline_stats else 0,
            "services_affected": len(service_stats.get('services_analyzed', [])) if 'error' not in service_stats else 0,
            "total_requests": request_patterns.get('total_requests', 0) if 'error' not in request_patterns else 0,
            "error_rate": None,
            "most_critical_service": None,
            "primary_error_category": None,
            "analysis_status": "OK"
        }
        
        # Calculate error rate
        if summary['total_requests'] > 0 and summary['total_errors'] > 0:
            summary['error_rate'] = round(
                (summary['total_errors'] / summary['total_requests']) * 100, 2
            )
        
        # Find most critical service
        if 'errors_by_service' in error_stats and error_stats.get('errors_by_service'):
            summary['most_critical_service'] = max(
                error_stats['errors_by_service'].items(),
                key=lambda x: x[1]
            )[0] if error_stats['errors_by_service'] else None
        
        # Find primary error category
        if 'error_categories' in error_patterns and error_patterns.get('error_categories'):
            summary['primary_error_category'] = max(
                error_patterns['error_categories'].items(),
                key=lambda x: x[1]
            )[0] if error_patterns['error_categories'] else None
        
        # Build comprehensive result
        result = {
            "metadata": metadata,
            "error_analysis": error_stats,
            "timeline_analysis": timeline_stats,
            "service_analysis": service_stats,
            "request_analysis": request_patterns,
            "error_pattern_analysis": error_patterns,
            "summary": summary,
            "status": "OK"
        }
        
        return json.dumps(result, indent=2, default=str)
    
    except json.JSONDecodeError as e:
        error_result = {
            "error": "JSON decode error",
            "message": f"Failed to parse analysis results: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to perform comprehensive log analysis: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)
