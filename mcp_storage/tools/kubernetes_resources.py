"""
Kubernetes Resource Usage Tool
Get CPU and memory usage for pods and nodes.
"""

import json
from typing import Optional


def _get_k8s_client():
    """Get Kubernetes client, handling import errors gracefully."""
    try:
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        return client.CoreV1Api(), client.CustomObjectsApi()
    except ImportError:
        raise ImportError("kubernetes library not installed. Run: pip install kubernetes")
    except Exception as e:
        raise Exception(f"Failed to load Kubernetes config: {str(e)}")


def get_resource_usage(resource_type: str = "pods", namespace: Optional[str] = None) -> str:
    """
    Get CPU and memory usage for pods or nodes.
    
    Args:
        resource_type: Type of resource ("pods" or "nodes")
        namespace: Optional namespace to filter pods. If None, gets all namespaces.
    
    Returns:
        JSON string containing:
        - resources: List of resource usage information
        - total_cpu: Total CPU usage
        - total_memory: Total memory usage
    """
    try:
        v1, custom_api = _get_k8s_client()
        
        # Try to get metrics from metrics-server
        try:
            if resource_type == "pods":
                if namespace:
                    metrics = custom_api.list_namespaced_custom_object(
                        group="metrics.k8s.io",
                        version="v1beta1",
                        namespace=namespace,
                        plural="pods"
                    )
                else:
                    metrics = custom_api.list_cluster_custom_object(
                        group="metrics.k8s.io",
                        version="v1beta1",
                        plural="pods"
                    )
                
                resource_list = []
                total_cpu_cores = 0.0
                total_memory_bytes = 0.0
                
                for item in metrics.get("items", []):
                    pod_name = item["metadata"]["name"]
                    pod_namespace = item["metadata"]["namespace"]
                    
                    # Sum container usage
                    cpu_usage = 0.0
                    memory_usage = 0.0
                    containers = []
                    
                    for container in item.get("containers", []):
                        container_name = container["name"]
                        # Parse CPU (e.g., "100m" = 0.1 cores, "1" = 1 core)
                        cpu_str = container.get("usage", {}).get("cpu", "0")
                        cpu_value = _parse_cpu(cpu_str)
                        # Parse Memory (e.g., "100Mi" = 100 * 1024 * 1024 bytes)
                        memory_str = container.get("usage", {}).get("memory", "0")
                        memory_value = _parse_memory(memory_str)
                        
                        cpu_usage += cpu_value
                        memory_usage += memory_value
                        
                        containers.append({
                            "name": container_name,
                            "cpu": cpu_str,
                            "cpu_cores": round(cpu_value, 3),
                            "memory": memory_str,
                            "memory_mb": round(memory_value / (1024 * 1024), 2)
                        })
                    
                    total_cpu_cores += cpu_usage
                    total_memory_bytes += memory_usage
                    
                    resource_list.append({
                        "name": pod_name,
                        "namespace": pod_namespace,
                        "cpu": f"{cpu_usage:.3f}",
                        "cpu_cores": round(cpu_usage, 3),
                        "memory": f"{memory_usage / (1024 * 1024):.2f}Mi",
                        "memory_mb": round(memory_usage / (1024 * 1024), 2),
                        "containers": containers
                    })
                
                result = {
                    "resource_type": "pods",
                    "resources": resource_list,
                    "total_cpu_cores": round(total_cpu_cores, 3),
                    "total_memory_mb": round(total_memory_bytes / (1024 * 1024), 2),
                    "total_count": len(resource_list),
                    "message": f"Found resource usage for {len(resource_list)} pod(s)"
                }
                
            elif resource_type == "nodes":
                metrics = custom_api.list_cluster_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    plural="nodes"
                )
                
                resource_list = []
                total_cpu_cores = 0.0
                total_memory_bytes = 0.0
                
                for item in metrics.get("items", []):
                    node_name = item["metadata"]["name"]
                    cpu_str = item.get("usage", {}).get("cpu", "0")
                    memory_str = item.get("usage", {}).get("memory", "0")
                    
                    cpu_value = _parse_cpu(cpu_str)
                    memory_value = _parse_memory(memory_str)
                    
                    total_cpu_cores += cpu_value
                    total_memory_bytes += memory_value
                    
                    resource_list.append({
                        "name": node_name,
                        "cpu": cpu_str,
                        "cpu_cores": round(cpu_value, 3),
                        "memory": memory_str,
                        "memory_mb": round(memory_value / (1024 * 1024), 2)
                    })
                
                result = {
                    "resource_type": "nodes",
                    "resources": resource_list,
                    "total_cpu_cores": round(total_cpu_cores, 3),
                    "total_memory_mb": round(total_memory_bytes / (1024 * 1024), 2),
                    "total_count": len(resource_list),
                    "message": f"Found resource usage for {len(resource_list)} node(s)"
                }
            else:
                raise ValueError(f"Invalid resource_type: {resource_type}. Must be 'pods' or 'nodes'")
            
            return json.dumps(result, indent=2)
        
        except Exception as metrics_error:
            # Metrics server not available
            error_result = {
                "error": "Metrics server not available",
                "details": str(metrics_error),
                "message": "Kubernetes metrics-server is not installed or not accessible. Install metrics-server to get resource usage data."
            }
            return json.dumps(error_result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "resource_type": resource_type,
            "message": f"Failed to get resource usage: {str(e)}"
        }
        return json.dumps(error_result, indent=2)


def _parse_cpu(cpu_str: str) -> float:
    """Parse CPU string (e.g., '100m' = 0.1, '1' = 1.0, '500m' = 0.5)."""
    if not cpu_str or cpu_str == "0":
        return 0.0
    
    cpu_str = cpu_str.strip()
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1]) / 1000.0
    elif cpu_str.endswith("n"):
        return float(cpu_str[:-1]) / 1000000000.0
    else:
        return float(cpu_str)


def _parse_memory(memory_str: str) -> float:
    """Parse memory string to bytes (e.g., '100Mi' = 100 * 1024 * 1024, '1Gi' = 1024 * 1024 * 1024)."""
    if not memory_str or memory_str == "0":
        return 0.0
    
    memory_str = memory_str.strip()
    multipliers = {
        "Ki": 1024,
        "Mi": 1024 ** 2,
        "Gi": 1024 ** 3,
        "Ti": 1024 ** 4,
        "K": 1000,
        "M": 1000 ** 2,
        "G": 1000 ** 3,
        "T": 1000 ** 4
    }
    
    for suffix, multiplier in multipliers.items():
        if memory_str.endswith(suffix):
            return float(memory_str[:-len(suffix)]) * multiplier
    
    # If no suffix, assume bytes
    return float(memory_str)
