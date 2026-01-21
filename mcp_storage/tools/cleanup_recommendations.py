"""
Storage Cleanup Recommendations Tool
Analyze storage and provide cleanup recommendations.
"""

import json
import os
import psutil
from pathlib import Path


def get_cleanup_recommendations(mount_point: str = "/", analyze_depth: int = 2) -> str:
    """
    Analyze storage and provide cleanup recommendations.
    
    Args:
        mount_point: Mount point to analyze (default: "/")
        analyze_depth: Directory depth to analyze (default: 2, max 3 for performance)
    
    Returns:
        JSON string containing:
        - mount_point: Mount point analyzed
        - current_usage: Current disk usage
        - recommendations: List of cleanup recommendations
        - large_directories: List of large directories found
        - estimated_savings_gb: Estimated space that could be freed
        - priority: Cleanup priority (LOW, MEDIUM, HIGH, CRITICAL)
    
    Example:
        >>> result = get_cleanup_recommendations("/")
        >>> data = json.loads(result)
        >>> print(data["priority"])
        "MEDIUM"
    """
    try:
        disk_usage = psutil.disk_usage(mount_point)
        used_percent = disk_usage.percent
        free_gb = disk_usage.free / (1024 ** 3)
        
        recommendations = []
        large_directories = []
        estimated_savings = 0.0
        
        # Common cleanup targets
        cleanup_targets = [
            ("/tmp", "Temporary files"),
            ("/var/log", "Log files"),
            ("/var/cache", "Cache files"),
            ("~/.cache", "User cache"),
            ("~/.local/share/Trash", "Trash files"),
        ]
        
        # Check common locations
        for target_path, description in cleanup_targets:
            full_path = os.path.expanduser(target_path)
            if os.path.exists(full_path):
                try:
                    total_size = 0
                    file_count = 0
                    
                    for root, dirs, files in os.walk(full_path):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                size = os.path.getsize(file_path)
                                total_size += size
                                file_count += 1
                            except (OSError, PermissionError):
                                continue
                        
                        # Limit depth
                        if root.count(os.sep) - full_path.count(os.sep) >= analyze_depth:
                            dirs[:] = []
                    
                    size_gb = total_size / (1024 ** 3)
                    if size_gb > 0.1:  # Only report if > 100MB
                        large_directories.append({
                            "path": full_path,
                            "size_gb": round(size_gb, 2),
                            "file_count": file_count,
                            "description": description
                        })
                        estimated_savings += size_gb * 0.5  # Assume 50% can be cleaned
                except (PermissionError, OSError):
                    continue
        
        # Generate recommendations based on usage
        if used_percent >= 85:
            priority = "CRITICAL"
            recommendations.append({
                "action": "Immediate cleanup required",
                "reason": f"Disk usage at {used_percent:.1f}%",
                "impact": "HIGH"
            })
        elif used_percent >= 70:
            priority = "HIGH"
            recommendations.append({
                "action": "Plan cleanup soon",
                "reason": f"Disk usage at {used_percent:.1f}%",
                "impact": "MEDIUM"
            })
        else:
            priority = "MEDIUM" if used_percent >= 50 else "LOW"
        
        # Add specific recommendations
        if large_directories:
            for dir_info in large_directories[:5]:  # Top 5
                recommendations.append({
                    "action": f"Clean {dir_info['description']}",
                    "path": dir_info["path"],
                    "potential_savings_gb": round(dir_info["size_gb"] * 0.5, 2),
                    "impact": "MEDIUM"
                })
        
        # General recommendations
        if used_percent > 50:
            recommendations.append({
                "action": "Review and remove unused applications",
                "reason": "Free up space by removing unused software",
                "impact": "MEDIUM"
            })
        
        if free_gb < 10:
            recommendations.append({
                "action": "Consider expanding storage",
                "reason": f"Only {free_gb:.2f} GB free",
                "impact": "HIGH"
            })
        
        result = {
            "mount_point": mount_point,
            "current_usage": {
                "used_percent": round(used_percent, 2),
                "free_gb": round(free_gb, 2),
                "status": "CRITICAL" if used_percent >= 85 else "WARNING" if used_percent >= 70 else "OK"
            },
            "priority": priority,
            "recommendations": recommendations,
            "large_directories": large_directories[:10],  # Top 10
            "estimated_savings_gb": round(estimated_savings, 2),
            "message": f"Cleanup priority: {priority}. Estimated savings: {estimated_savings:.2f} GB"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "mount_point": mount_point,
            "message": f"Failed to generate cleanup recommendations for {mount_point}: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
