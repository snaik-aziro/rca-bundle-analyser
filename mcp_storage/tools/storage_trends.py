"""
Storage Trends Tool
Monitor storage trends over time by taking multiple samples.
"""

import json
import time
import psutil


def get_storage_trends(mount_point: str = "/", samples: int = 5, interval_sec: float = 1.0) -> str:
    """
    Get storage trends by taking multiple samples over time.
    
    Args:
        mount_point: Mount point to monitor (default: "/")
        samples: Number of samples to take (default: 5)
        interval_sec: Time between samples in seconds (default: 1.0)
    
    Returns:
        JSON string containing:
        - mount_point: Mount point monitored
        - samples: List of sample data with timestamp, used_gb, used_percent, iops
        - trend: Trend analysis (INCREASING, DECREASING, STABLE)
        - avg_usage_percent: Average usage percentage
        - max_usage_percent: Maximum usage percentage
        - min_usage_percent: Minimum usage percentage
    
    Example:
        >>> result = get_storage_trends("/", 3, 0.5)
        >>> data = json.loads(result)
        >>> print(data["trend"])
        "STABLE"
    """
    try:
        sample_data = []
        initial_io = psutil.disk_io_counters()
        
        for i in range(samples):
            # Get disk usage
            disk_usage = psutil.disk_usage(mount_point)
            used_gb = disk_usage.used / (1024 ** 3)
            used_percent = disk_usage.percent
            
            # Get I/O counters
            current_io = psutil.disk_io_counters()
            if current_io and initial_io:
                read_count = current_io.read_count - initial_io.read_count
                write_count = current_io.write_count - initial_io.write_count
                total_iops = (read_count + write_count) / (interval_sec * (i + 1)) if i > 0 else 0
            else:
                total_iops = 0
            
            sample_data.append({
                "sample": i + 1,
                "timestamp": time.time(),
                "used_gb": round(used_gb, 2),
                "used_percent": round(used_percent, 2),
                "iops": round(total_iops, 2) if i > 0 else 0
            })
            
            if i < samples - 1:
                time.sleep(interval_sec)
        
        # Analyze trend
        usage_values = [s["used_percent"] for s in sample_data]
        avg_usage = sum(usage_values) / len(usage_values)
        max_usage = max(usage_values)
        min_usage = min(usage_values)
        
        # Determine trend
        if len(usage_values) >= 2:
            first_half = sum(usage_values[:len(usage_values)//2]) / (len(usage_values)//2)
            second_half = sum(usage_values[len(usage_values)//2:]) / (len(usage_values) - len(usage_values)//2)
            
            diff = second_half - first_half
            if diff > 0.1:
                trend = "INCREASING"
            elif diff < -0.1:
                trend = "DECREASING"
            else:
                trend = "STABLE"
        else:
            trend = "INSUFFICIENT_DATA"
        
        result = {
            "mount_point": mount_point,
            "samples_taken": samples,
            "interval_sec": interval_sec,
            "samples": sample_data,
            "trend": trend,
            "avg_usage_percent": round(avg_usage, 2),
            "max_usage_percent": round(max_usage, 2),
            "min_usage_percent": round(min_usage, 2),
            "message": f"Storage trend: {trend} (Avg: {avg_usage:.2f}%, Range: {min_usage:.2f}% - {max_usage:.2f}%)"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "mount_point": mount_point,
            "message": f"Failed to get storage trends for {mount_point}: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
