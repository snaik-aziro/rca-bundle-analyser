"""
Disk Capacity Tool
Measures disk capacity, usage, and free space for a given mount point.
"""

import json
import psutil


def get_disk_capacity(mount_point: str = "/") -> str:
    """
    Get disk capacity and usage metrics for a mount point.
    
    Args:
        mount_point: The mount point path to check (default: "/")
    
    Returns:
        JSON string containing:
        - total_gb: Total disk space in GB
        - used_gb: Used disk space in GB
        - free_gb: Free disk space in GB
        - used_percent: Percentage of disk used
        - status: "OK", "WARNING", or "CRITICAL" (CRITICAL if >85%)
        - mount_point: The mount point checked
    
    Example:
        >>> result = get_disk_capacity("/")
        >>> data = json.loads(result)
        >>> print(data["status"])
        "OK"
    """
    try:
        # Get disk usage
        disk_usage = psutil.disk_usage(mount_point)
        
        # Convert bytes to GB
        total_gb = disk_usage.total / (1024 ** 3)
        used_gb = disk_usage.used / (1024 ** 3)
        free_gb = disk_usage.free / (1024 ** 3)
        used_percent = disk_usage.percent
        
        # Determine status
        if used_percent >= 85:
            status = "CRITICAL"
        elif used_percent >= 70:
            status = "WARNING"
        else:
            status = "OK"
        
        # Build result
        result = {
            "mount_point": mount_point,
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "used_percent": round(used_percent, 2),
            "status": status,
            "message": f"Disk usage at {mount_point}: {used_percent:.2f}% ({used_gb:.2f} GB used of {total_gb:.2f} GB total)"
        }
        
        return json.dumps(result, indent=2)
    
    except PermissionError:
        error_result = {
            "error": "Permission denied",
            "mount_point": mount_point,
            "message": f"Cannot access mount point: {mount_point}. Insufficient permissions."
        }
        return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "mount_point": mount_point,
            "message": f"Failed to get disk capacity for {mount_point}: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
