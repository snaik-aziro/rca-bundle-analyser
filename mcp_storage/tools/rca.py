"""
Storage Root Cause Analysis (RCA) Tool
Analyzes storage metrics to identify issues and recommend actions.
"""

import json
from typing import Dict, Any, List


def generate_storage_rca(
    capacity_data: Dict[str, Any],
    iops_data: Dict[str, Any],
    latency_data: Dict[str, Any]
) -> str:
    """
    Generate Root Cause Analysis (RCA) for storage issues.
    
    Analyzes capacity, IOPS, and latency data to:
    - Identify storage problems
    - Provide actionable recommendations
    - Generate a summary report
    
    Args:
        capacity_data: Output from get_disk_capacity tool (parsed JSON dict)
        iops_data: Output from get_disk_iops tool (parsed JSON dict)
        latency_data: Output from get_disk_latency tool (parsed JSON dict)
    
    Returns:
        JSON string containing:
        - summary: Overall storage health summary
        - issues: List of identified issues
        - recommendations: List of recommended actions
        - severity: Overall severity level (OK, WARNING, CRITICAL)
        - metrics_summary: Quick metrics overview
    
    Example:
        >>> capacity = json.loads(get_disk_capacity())
        >>> iops = json.loads(get_disk_iops())
        >>> latency = json.loads(get_disk_latency())
        >>> rca = generate_storage_rca(capacity, iops, latency)
        >>> print(rca)
    """
    issues: List[str] = []
    recommendations: List[str] = []
    severity_levels = []
    
    # Parse input data (handle both dict and JSON string)
    if isinstance(capacity_data, str):
        capacity = json.loads(capacity_data)
    else:
        capacity = capacity_data
    
    if isinstance(iops_data, str):
        iops = json.loads(iops_data)
    else:
        iops = iops_data
    
    if isinstance(latency_data, str):
        latency = json.loads(latency_data)
    else:
        latency = latency_data
    
    # Analyze Capacity Issues
    if "error" not in capacity:
        capacity_status = capacity.get("status", "UNKNOWN")
        used_percent = capacity.get("used_percent", 0)
        free_gb = capacity.get("free_gb", 0)
        
        if capacity_status == "CRITICAL":
            issues.append(f"CRITICAL: Disk usage at {used_percent:.2f}% - Only {free_gb:.2f} GB free")
            recommendations.append("Immediate action required: Free up disk space or expand storage")
            recommendations.append("Consider: Removing old logs, temporary files, or unused data")
            recommendations.append("Consider: Adding additional storage capacity")
            severity_levels.append("CRITICAL")
        elif capacity_status == "WARNING":
            issues.append(f"WARNING: Disk usage at {used_percent:.2f}% - Monitor closely")
            recommendations.append("Plan for disk cleanup or expansion in near future")
            severity_levels.append("WARNING")
    else:
        issues.append(f"Capacity check failed: {capacity.get('error', 'Unknown error')}")
        severity_levels.append("WARNING")
    
    # Analyze IOPS Issues
    if "error" not in iops:
        iops_status = iops.get("status", "UNKNOWN")
        total_iops = iops.get("total_iops", 0)
        
        if iops_status == "DEGRADED":
            issues.append(f"DEGRADED: Low IOPS detected ({total_iops:.2f} IOPS)")
            recommendations.append("Investigate disk I/O bottlenecks")
            recommendations.append("Check for: High I/O wait times, disk queue depth, or I/O scheduler issues")
            recommendations.append("Consider: Upgrading to faster storage (SSD) or optimizing I/O patterns")
            severity_levels.append("WARNING")
        elif total_iops < 50:
            issues.append(f"Very low IOPS: {total_iops:.2f} - System may be idle or experiencing issues")
            recommendations.append("Verify system is under normal load")
            severity_levels.append("WARNING")
    else:
        issues.append(f"IOPS check failed: {iops.get('error', 'Unknown error')}")
        severity_levels.append("WARNING")
    
    # Analyze Latency Issues
    if "error" not in latency:
        latency_status = latency.get("status", "UNKNOWN")
        avg_read_latency = latency.get("avg_read_latency_ms", 0)
        avg_write_latency = latency.get("avg_write_latency_ms", 0)
        max_latency = max(avg_read_latency, avg_write_latency)
        
        if latency_status == "CRITICAL":
            issues.append(f"CRITICAL: High latency detected (Read: {avg_read_latency:.2f}ms, Write: {avg_write_latency:.2f}ms)")
            recommendations.append("Immediate action: Investigate disk performance issues")
            recommendations.append("Check for: Disk fragmentation, failing hardware, or overloaded storage")
            recommendations.append("Consider: Replacing failing disks or redistributing I/O load")
            severity_levels.append("CRITICAL")
        elif latency_status == "WARNING":
            issues.append(f"WARNING: Elevated latency (Read: {avg_read_latency:.2f}ms, Write: {avg_write_latency:.2f}ms)")
            recommendations.append("Monitor latency trends and investigate if it persists")
            severity_levels.append("WARNING")
    else:
        issues.append(f"Latency check failed: {latency.get('error', 'Unknown error')}")
        severity_levels.append("WARNING")
    
    # Determine overall severity
    if "CRITICAL" in severity_levels:
        overall_severity = "CRITICAL"
    elif "WARNING" in severity_levels:
        overall_severity = "WARNING"
    else:
        overall_severity = "OK"
    
    # Generate summary
    if overall_severity == "OK":
        summary = "Storage system is operating normally. All metrics are within acceptable ranges."
    elif overall_severity == "WARNING":
        summary = f"Storage system shows {len(issues)} warning(s). Monitor closely and take preventive action."
    else:
        summary = f"Storage system has CRITICAL issues. Immediate action required. {len(issues)} critical issue(s) detected."
    
    # Build metrics summary
    metrics_summary = {
        "capacity": {
            "status": capacity.get("status", "UNKNOWN") if "error" not in capacity else "ERROR",
            "used_percent": capacity.get("used_percent", 0) if "error" not in capacity else None
        },
        "iops": {
            "status": iops.get("status", "UNKNOWN") if "error" not in iops else "ERROR",
            "total_iops": iops.get("total_iops", 0) if "error" not in iops else None
        },
        "latency": {
            "status": latency.get("status", "UNKNOWN") if "error" not in latency else "ERROR",
            "max_latency_ms": max(
                latency.get("avg_read_latency_ms", 0),
                latency.get("avg_write_latency_ms", 0)
            ) if "error" not in latency else None
        }
    }
    
    # Build result
    result = {
        "summary": summary,
        "severity": overall_severity,
        "issues": issues if issues else ["No issues detected"],
        "recommendations": recommendations if recommendations else ["Continue monitoring"],
        "metrics_summary": metrics_summary,
        "timestamp": json.dumps({})  # Could add actual timestamp if needed
    }
    
    return json.dumps(result, indent=2)
