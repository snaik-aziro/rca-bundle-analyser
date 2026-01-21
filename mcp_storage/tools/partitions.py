"""
Disk Partitions Tool
Get information about all disk partitions and mount points.
"""

import json
import psutil


def get_disk_partitions() -> str:
    """
    Get information about all disk partitions and mount points.
    
    Returns:
        JSON string containing:
        - partitions: List of all partitions with device, mountpoint, fstype, opts
        - total_partitions: Total number of partitions
        - mount_points: List of all mount points
        - file_systems: List of unique file system types
    
    Example:
        >>> result = get_disk_partitions()
        >>> data = json.loads(result)
        >>> print(data["total_partitions"])
        5
    """
    try:
        partitions = psutil.disk_partitions(all=False)
        
        partition_list = []
        mount_points = []
        file_systems = set()
        
        for partition in partitions:
            partition_info = {
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "opts": partition.opts
            }
            partition_list.append(partition_info)
            mount_points.append(partition.mountpoint)
            file_systems.add(partition.fstype)
        
        # Get usage for each mount point
        for part_info in partition_list:
            try:
                usage = psutil.disk_usage(part_info["mountpoint"])
                part_info["total_gb"] = round(usage.total / (1024 ** 3), 2)
                part_info["used_gb"] = round(usage.used / (1024 ** 3), 2)
                part_info["free_gb"] = round(usage.free / (1024 ** 3), 2)
                part_info["used_percent"] = round(usage.percent, 2)
            except (PermissionError, OSError):
                part_info["total_gb"] = None
                part_info["used_gb"] = None
                part_info["free_gb"] = None
                part_info["used_percent"] = None
        
        result = {
            "total_partitions": len(partition_list),
            "partitions": partition_list,
            "mount_points": mount_points,
            "file_systems": sorted(list(file_systems)),
            "message": f"Found {len(partition_list)} disk partitions"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to get disk partitions: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
