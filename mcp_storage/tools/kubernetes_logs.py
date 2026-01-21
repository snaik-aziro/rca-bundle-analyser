"""
Kubernetes Logs Tool
Get logs from Kubernetes pods.
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
        return client.CoreV1Api()
    except ImportError:
        raise ImportError("kubernetes library not installed. Run: pip install kubernetes")
    except Exception as e:
        raise Exception(f"Failed to load Kubernetes config: {str(e)}")


def get_pod_logs(pod_name: str, namespace: str = "default", container: Optional[str] = None, tail_lines: int = 100) -> str:
    """
    Get logs from a pod.
    
    Args:
        pod_name: Name of the pod
        namespace: Namespace of the pod (default: "default")
        container: Optional container name (if pod has multiple containers)
        tail_lines: Number of lines to retrieve from the end (default: 100)
    
    Returns:
        JSON string containing:
        - pod_name: Pod name
        - namespace: Pod namespace
        - container: Container name
        - logs: Log lines
        - line_count: Number of log lines
    """
    try:
        v1 = _get_k8s_client()
        
        # Get pod to check containers
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        
        # If container not specified and pod has multiple containers, get first one
        if not container:
            if pod.spec.containers:
                container = pod.spec.containers[0].name
            else:
                error_result = {
                    "error": "No containers found",
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "message": f"Pod {pod_name} has no containers"
                }
                return json.dumps(error_result, indent=2)
        
        # Get logs
        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines
        )
        
        log_lines = logs.split('\n') if logs else []
        
        result = {
            "pod_name": pod_name,
            "namespace": namespace,
            "container": container,
            "logs": log_lines,
            "line_count": len(log_lines),
            "message": f"Retrieved {len(log_lines)} log line(s) from {pod_name}/{container}"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "pod_name": pod_name,
            "namespace": namespace,
            "container": container,
            "message": f"Failed to get pod logs: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
