"""
Disk Health Tool
Get disk health and performance metrics.
"""

import json
import psutil
import time


def get_disk_health(mount_point: str = "/", test_duration: float = 1.0) -> str:
    """
    Get comprehensive disk health metrics including I/O wait times and performance.
    
    Args:
        mount_point: Mount point to check (default: "/")
        test_duration: Duration for performance test in seconds (default: 1.0)
    
    Returns:
        JSON string containing:
        - mount_point: Mount point checked
        - io_wait_percent: CPU I/O wait percentage
        - disk_utilization_percent: Disk utilization percentage
        - avg_queue_length: Average I/O queue length
        - read_speed_mbps: Average read speed in MB/s
        - write_speed_mbps: Average write speed in MB/s
        - status: Overall health status
        - health_score: Health score (0-100)
    
    Example:
        >>> result = get_disk_health("/", 1.0)
        >>> data = json.loads(result)
        >>> print(data["health_score"])
        85
    """
    try:
        # Get initial I/O counters
        initial_io = psutil.disk_io_counters()
        initial_cpu = psutil.cpu_times()
        
        if initial_io is None:
            error_result = {
                "error": "No disk I/O counters available",
                "message": "System does not provide disk I/O statistics"
            }
            return json.dumps(error_result, indent=2)
        
        # Wait for test duration
        time.sleep(test_duration)
        
        # Get final counters
        final_io = psutil.disk_io_counters()
        final_cpu = psutil.cpu_times()
        
        if final_io is None:
            error_result = {
                "error": "No disk I/O counters available after test",
                "message": "System does not provide disk I/O statistics"
            }
            return json.dumps(error_result, indent=2)
        
        # Calculate I/O metrics
        read_bytes = (final_io.read_bytes - initial_io.read_bytes) / test_duration
        write_bytes = (final_io.write_bytes - initial_io.write_bytes) / test_duration
        read_speed_mbps = (read_bytes / (1024 ** 2))
        write_speed_mbps = (write_bytes / (1024 ** 2))
        
        # Calculate I/O wait (if available)
        try:
            io_wait = final_cpu.iowait - initial_cpu.iowait
            total_time = sum([
                final_cpu.user - initial_cpu.user,
                final_cpu.nice - initial_cpu.nice,
                final_cpu.system - initial_cpu.system,
                final_cpu.idle - initial_cpu.idle,
                io_wait
            ])
            io_wait_percent = (io_wait / total_time * 100) if total_time > 0 else 0
        except AttributeError:
            io_wait_percent = None  # Not available on all systems
        
        # Get disk usage
        disk_usage = psutil.disk_usage(mount_point)
        disk_utilization_percent = disk_usage.percent
        
        # Calculate health score (0-100)
        health_score = 100
        if disk_utilization_percent > 85:
            health_score -= 30
        elif disk_utilization_percent > 70:
            health_score -= 15
        
        if io_wait_percent is not None:
            if io_wait_percent > 20:
                health_score -= 30
            elif io_wait_percent > 10:
                health_score -= 15
        
        health_score = max(0, min(100, health_score))
        
        # Determine status
        if health_score >= 80:
            status = "HEALTHY"
        elif health_score >= 60:
            status = "WARNING"
        else:
            status = "CRITICAL"
        
        result = {
            "mount_point": mount_point,
            "io_wait_percent": round(io_wait_percent, 2) if io_wait_percent is not None else None,
            "disk_utilization_percent": round(disk_utilization_percent, 2),
            "read_speed_mbps": round(read_speed_mbps, 2),
            "write_speed_mbps": round(write_speed_mbps, 2),
            "health_score": health_score,
            "status": status,
            "test_duration_sec": test_duration,
            "message": f"Disk health: {status} (Score: {health_score}/100)"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "mount_point": mount_point,
            "message": f"Failed to get disk health for {mount_point}: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
