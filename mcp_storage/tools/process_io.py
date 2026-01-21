"""
Process I/O Tool
Monitor I/O statistics for running processes.
"""

import json
import psutil


def get_top_io_processes(limit: int = 10) -> str:
    """
    Get top processes by I/O usage.
    
    Args:
        limit: Number of top processes to return (default: 10)
    
    Returns:
        JSON string containing:
        - processes: List of top I/O processes with pid, name, read_bytes, write_bytes, read_count, write_count
        - total_read_bytes: Total read bytes across all processes
        - total_write_bytes: Total write bytes across all processes
        - count: Number of processes returned
    
    Example:
        >>> result = get_top_io_processes(5)
        >>> data = json.loads(result)
        >>> print(data["count"])
        5
    """
    try:
        processes = []
        total_read_bytes = 0
        total_write_bytes = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'io_counters']):
            try:
                pinfo = proc.info
                if pinfo['io_counters'] is not None:
                    io = pinfo['io_counters']
                    read_bytes = io.read_bytes
                    write_bytes = io.write_bytes
                    read_count = io.read_count
                    write_count = io.write_count
                    total_io = read_bytes + write_bytes
                    
                    processes.append({
                        "pid": pinfo['pid'],
                        "name": pinfo['name'],
                        "read_bytes": read_bytes,
                        "write_bytes": write_bytes,
                        "read_bytes_gb": round(read_bytes / (1024 ** 3), 4),
                        "write_bytes_gb": round(write_bytes / (1024 ** 3), 4),
                        "read_count": read_count,
                        "write_count": write_count,
                        "total_io_bytes": total_io
                    })
                    
                    total_read_bytes += read_bytes
                    total_write_bytes += write_bytes
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        # Sort by total I/O and get top N
        processes.sort(key=lambda x: x['total_io_bytes'], reverse=True)
        top_processes = processes[:limit]
        
        result = {
            "count": len(top_processes),
            "processes": top_processes,
            "total_read_bytes": total_read_bytes,
            "total_write_bytes": total_write_bytes,
            "total_read_gb": round(total_read_bytes / (1024 ** 3), 2),
            "total_write_gb": round(total_write_bytes / (1024 ** 3), 2),
            "message": f"Top {len(top_processes)} processes by I/O usage"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to get process I/O statistics: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
