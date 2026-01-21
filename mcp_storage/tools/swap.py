"""
Swap Space Tool
Monitor swap space usage and statistics.
"""

import json
import psutil


def get_swap_usage() -> str:
    """
    Get swap space usage and statistics.
    
    Returns:
        JSON string containing:
        - total_gb: Total swap space in GB
        - used_gb: Used swap space in GB
        - free_gb: Free swap space in GB
        - used_percent: Percentage of swap used
        - status: "OK", "WARNING", or "CRITICAL" (CRITICAL if >80% used)
        - sin: Number of pages swapped in from disk
        - sout: Number of pages swapped out to disk
    
    Example:
        >>> result = get_swap_usage()
        >>> data = json.loads(result)
        >>> print(data["status"])
        "OK"
    """
    try:
        swap = psutil.swap_memory()
        
        total_gb = swap.total / (1024 ** 3)
        used_gb = swap.used / (1024 ** 3)
        free_gb = swap.free / (1024 ** 3)
        used_percent = swap.percent
        
        # Determine status
        if used_percent >= 80:
            status = "CRITICAL"
        elif used_percent >= 60:
            status = "WARNING"
        else:
            status = "OK"
        
        result = {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "used_percent": round(used_percent, 2),
            "status": status,
            "sin": swap.sin,  # Pages swapped in
            "sout": swap.sout,  # Pages swapped out
            "message": f"Swap usage: {used_percent:.2f}% ({used_gb:.2f} GB used of {total_gb:.2f} GB total)"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to get swap usage: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
