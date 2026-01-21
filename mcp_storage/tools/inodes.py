"""
Inode Usage Tool
Monitor inode usage for file systems (Unix/Linux).
"""

import json
import os
import stat


def get_inode_usage(mount_point: str = "/") -> str:
    """
    Get inode usage statistics for a mount point.
    
    Args:
        mount_point: The mount point path to check (default: "/")
    
    Returns:
        JSON string containing:
        - mount_point: Mount point checked
        - total_inodes: Total number of inodes
        - used_inodes: Number of used inodes
        - free_inodes: Number of free inodes
        - used_percent: Percentage of inodes used
        - status: "OK", "WARNING", or "CRITICAL" (CRITICAL if >90% used)
    
    Example:
        >>> result = get_inode_usage("/")
        >>> data = json.loads(result)
        >>> print(data["used_percent"])
        45.2
    """
    try:
        statvfs = os.statvfs(mount_point)
        
        # Calculate inode statistics
        total_inodes = statvfs.f_files
        free_inodes = statvfs.f_ffree
        used_inodes = total_inodes - free_inodes
        
        if total_inodes > 0:
            used_percent = (used_inodes / total_inodes) * 100
        else:
            used_percent = 0
        
        # Determine status
        if used_percent >= 90:
            status = "CRITICAL"
        elif used_percent >= 80:
            status = "WARNING"
        else:
            status = "OK"
        
        result = {
            "mount_point": mount_point,
            "total_inodes": total_inodes,
            "used_inodes": used_inodes,
            "free_inodes": free_inodes,
            "used_percent": round(used_percent, 2),
            "status": status,
            "message": f"Inode usage at {mount_point}: {used_percent:.2f}% ({used_inodes} used of {total_inodes} total)"
        }
        
        return json.dumps(result, indent=2)
    
    except AttributeError:
        # Windows doesn't support statvfs
        error_result = {
            "error": "Not supported on this platform",
            "mount_point": mount_point,
            "message": "Inode statistics are not available on Windows systems"
        }
        return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "mount_point": mount_point,
            "message": f"Failed to get inode usage for {mount_point}: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
