"""
Disk Latency Tool
Measures disk read and write latency in milliseconds.
"""

import json
import psutil


def get_disk_latency() -> str:
    """
    Get disk latency metrics (average read and write latency in milliseconds).
    
    Returns:
        JSON string containing:
        - avg_read_latency_ms: Average read latency in milliseconds
        - avg_write_latency_ms: Average write latency in milliseconds
        - read_time_ms: Total read time in milliseconds
        - write_time_ms: Total write time in milliseconds
        - read_count: Total read operations
        - write_count: Total write operations
        - status: "OK" or "CRITICAL" (CRITICAL if latency > 20ms)
    
    Example:
        >>> result = get_disk_latency()
        >>> data = json.loads(result)
        >>> print(data["avg_read_latency_ms"])
        15.5
    """
    try:
        # Get disk I/O counters
        io_counters = psutil.disk_io_counters()
        
        if io_counters is None:
            error_result = {
                "error": "No disk I/O counters available",
                "message": "System does not provide disk I/O statistics"
            }
            return json.dumps(error_result, indent=2)
        
        # Extract metrics (time is in milliseconds)
        read_time_ms = io_counters.read_time
        write_time_ms = io_counters.write_time
        read_count = io_counters.read_count
        write_count = io_counters.write_count
        
        # Calculate average latency
        # Note: read_time and write_time are cumulative, so we calculate per-operation
        if read_count > 0:
            avg_read_latency_ms = read_time_ms / read_count
        else:
            avg_read_latency_ms = 0.0
        
        if write_count > 0:
            avg_write_latency_ms = write_time_ms / write_count
        else:
            avg_write_latency_ms = 0.0
        
        # Determine status based on worst latency
        max_latency = max(avg_read_latency_ms, avg_write_latency_ms)
        if max_latency > 20:
            status = "CRITICAL"
        elif max_latency > 10:
            status = "WARNING"
        else:
            status = "OK"
        
        # Build result
        result = {
            "avg_read_latency_ms": round(avg_read_latency_ms, 2),
            "avg_write_latency_ms": round(avg_write_latency_ms, 2),
            "read_time_ms": read_time_ms,
            "write_time_ms": write_time_ms,
            "read_count": read_count,
            "write_count": write_count,
            "status": status,
            "message": f"Latency: Read {avg_read_latency_ms:.2f}ms, Write {avg_write_latency_ms:.2f}ms"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to get disk latency: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
