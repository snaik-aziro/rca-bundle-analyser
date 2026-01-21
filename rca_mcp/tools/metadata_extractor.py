"""
Metadata Extractor Tool
Extracts metadata from metadata.txt file
"""

import json
import os
import re
from typing import Dict, Optional


def extract_metadata(logs_path: str) -> str:
    """
    Extract metadata from metadata.txt file.
    
    Args:
        logs_path: Path to the RCA logs directory containing metadata.txt
    
    Returns:
        JSON string containing:
        - scenario_type: Type of scenario (crash, etc.)
        - timestamp_utc: Collection timestamp
        - namespace: Kubernetes namespace
        - files_included: Number of files in bundle
        - errors_found: Number of errors found
        - timeline_events: Number of timeline events
        - all_metadata: All key-value pairs from metadata file
    
    Example:
        >>> result = extract_metadata("/path/to/rca_logs")
        >>> data = json.loads(result)
        >>> print(data["scenario_type"])
    """
    try:
        metadata_file = os.path.join(logs_path, "metadata.txt")
        
        if not os.path.exists(metadata_file):
            error_result = {
                "error": "File not found",
                "message": f"metadata.txt not found at: {metadata_file}",
                "logs_path": logs_path
            }
            return json.dumps(error_result, indent=2)
        
        # Read metadata file
        metadata = {}
        with open(metadata_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Try to parse numeric values
                    if value.isdigit():
                        value = int(value)
                    elif re.match(r'^\d+\.\d+$', value):
                        value = float(value)
                    
                    metadata[key] = value
        
        # Extract common fields
        result = {
            "scenario_type": metadata.get('scenario_type'),
            "timestamp_utc": metadata.get('timestamp_utc'),
            "namespace": metadata.get('namespace'),
            "files_included": metadata.get('files_included'),
            "errors_found": metadata.get('errors_found'),
            "timeline_events": metadata.get('timeline_events'),
            "all_metadata": metadata,
            "status": "OK"
        }
        
        return json.dumps(result, indent=2, default=str)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to extract metadata: {str(e)}",
            "logs_path": logs_path
        }
        return json.dumps(error_result, indent=2)
