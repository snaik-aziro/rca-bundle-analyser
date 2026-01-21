"""
Disk IOPS Tool
Measures Input/Output Operations Per Second (IOPS) for disk I/O.
"""

import json
import time
import psutil


def get_disk_iops(interval_sec: float = 1.0) -> str:
    """
    Get disk IOPS metrics by measuring I/O operations over a time interval.
    
    Args:
        interval_sec: Measurement interval in seconds (default: 1.0)
    
    Returns:
        JSON string containing:
        - read_iops: Read operations per second
        - write_iops: Write operations per second
        - total_iops: Total operations per second
        - read_count: Total read operations in interval
        - write_count: Total write operations in interval
        - interval_sec: Measurement interval used
        - status: "OK" or "DEGRADED" (DEGRADED if total_iops < 100)
    
    Example:
        >>> result = get_disk_iops(1.0)
        >>> data = json.loads(result)
        >>> print(data["total_iops"])
        150.5
    """
    try:
        # Get initial I/O counters
        initial_io = psutil.disk_io_counters()
        
        if initial_io is None:
            error_result = {
                "error": "No disk I/O counters available",
                "message": "System does not provide disk I/O statistics"
            }
            return json.dumps(error_result, indent=2)
        
        # Wait for the specified interval
        time.sleep(interval_sec)
        
        # Get final I/O counters
        final_io = psutil.disk_io_counters()
        
        if final_io is None:
            error_result = {
                "error": "No disk I/O counters available after interval",
                "message": "System does not provide disk I/O statistics"
            }
            return json.dumps(error_result, indent=2)
        
        # Calculate differences
        read_count = final_io.read_count - initial_io.read_count
        write_count = final_io.write_count - initial_io.write_count
        total_count = read_count + write_count
        
        # Calculate IOPS
        read_iops = read_count / interval_sec
        write_iops = write_count / interval_sec
        total_iops = total_count / interval_sec
        
        # Determine status
        if total_iops < 100:
            status = "DEGRADED"
        else:
            status = "OK"
        
        # Build result
        result = {
            "read_iops": round(read_iops, 2),
            "write_iops": round(write_iops, 2),
            "total_iops": round(total_iops, 2),
            "read_count": read_count,
            "write_count": write_count,
            "interval_sec": interval_sec,
            "status": status,
            "message": f"IOPS: {total_iops:.2f} total ({read_iops:.2f} read, {write_iops:.2f} write) over {interval_sec}s"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to get disk IOPS: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
