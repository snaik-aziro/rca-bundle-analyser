"""
Kubernetes Pods Tool
List and get status of Kubernetes pods.
"""

import json
from typing import Optional


def _get_k8s_client():
    """Get Kubernetes client, handling import errors gracefully."""
    try:
        from kubernetes import client, config
        try:
            # Try to load in-cluster config first (if running in a pod)
            config.load_incluster_config()
        except:
            # Fall back to kubeconfig (local cluster)
            config.load_kube_config()
        return client.CoreV1Api()
    except ImportError:
        raise ImportError("kubernetes library not installed. Run: pip install kubernetes")
    except Exception as e:
        raise Exception(f"Failed to load Kubernetes config: {str(e)}")


def list_pods(namespace: Optional[str] = None) -> str:
    """
    List all pods in the cluster or a specific namespace.
    
    Args:
        namespace: Optional namespace to filter pods. If None, lists all namespaces.
    
    Returns:
        JSON string containing:
        - pods: List of pod information (name, namespace, status, node, age)
        - total_count: Total number of pods
        - namespaces: List of namespaces with pod counts
    """
    try:
        v1 = _get_k8s_client()
        
        if namespace:
            pods = v1.list_namespaced_pod(namespace=namespace)
            namespace_list = [namespace]
        else:
            pods = v1.list_pod_for_all_namespaces()
            namespace_list = list(set([pod.metadata.namespace for pod in pods.items]))
        
        pod_list = []
        for pod in pods.items:
            # Calculate age
            age = ""
            if pod.status.start_time:
                from datetime import datetime, timezone
                age_delta = datetime.now(timezone.utc) - pod.status.start_time
                days = age_delta.days
                hours, remainder = divmod(age_delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                if days > 0:
                    age = f"{days}d{hours}h"
                elif hours > 0:
                    age = f"{hours}h{minutes}m"
                else:
                    age = f"{minutes}m"
            
            pod_info = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name if pod.spec.node_name else "N/A",
                "age": age,
                "ready": f"{sum(1 for c in pod.status.container_statuses if c.ready)}/{len(pod.status.container_statuses) if pod.status.container_statuses else 0}",
                "restarts": sum(c.restart_count for c in pod.status.container_statuses if pod.status.container_statuses) if pod.status.container_statuses else 0
            }
            pod_list.append(pod_info)
        
        # Count pods per namespace
        namespace_counts = {}
        for pod in pod_list:
            ns = pod["namespace"]
            namespace_counts[ns] = namespace_counts.get(ns, 0) + 1
        
        result = {
            "pods": pod_list,
            "total_count": len(pod_list),
            "namespaces": [{"name": ns, "pod_count": namespace_counts.get(ns, 0)} for ns in namespace_list],
            "message": f"Found {len(pod_list)} pod(s) in {len(namespace_list)} namespace(s)"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to list pods: {str(e)}"
        }
        return json.dumps(error_result, indent=2)


def get_pod_status(pod_name: str, namespace: str = "default") -> str:
    """
    Get detailed status of a specific pod.
    
    Args:
        pod_name: Name of the pod
        namespace: Namespace of the pod (default: "default")
    
    Returns:
        JSON string containing:
        - name: Pod name
        - namespace: Pod namespace
        - status: Current phase
        - node: Node where pod is running
        - containers: Container details (name, image, status, ready)
        - conditions: Pod conditions
        - events: Recent events (if available)
    """
    try:
        v1 = _get_k8s_client()
        
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        
        # Get container statuses
        containers = []
        if pod.status.container_statuses:
            for container in pod.status.container_statuses:
                container_info = {
                    "name": container.name,
                    "image": next((c.image for c in pod.spec.containers if c.name == container.name), "N/A"),
                    "ready": container.ready,
                    "restart_count": container.restart_count,
                    "state": "running" if container.state.running else 
                            "waiting" if container.state.waiting else 
                            "terminated" if container.state.terminated else "unknown"
                }
                if container.state.waiting:
                    container_info["waiting_reason"] = container.state.waiting.reason
                containers.append(container_info)
        
        # Get conditions
        conditions = []
        if pod.status.conditions:
            for condition in pod.status.conditions:
                conditions.append({
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason if condition.reason else "N/A",
                    "message": condition.message if condition.message else "N/A"
                })
        
        # Calculate age
        age = ""
        if pod.status.start_time:
            from datetime import datetime, timezone
            age_delta = datetime.now(timezone.utc) - pod.status.start_time
            days = age_delta.days
            hours, remainder = divmod(age_delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            if days > 0:
                age = f"{days}d{hours}h"
            elif hours > 0:
                age = f"{hours}h{minutes}m"
            else:
                age = f"{minutes}m"
        
        result = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node": pod.spec.node_name if pod.spec.node_name else "N/A",
            "age": age,
            "containers": containers,
            "conditions": conditions,
            "message": f"Pod {pod_name} in namespace {namespace} is {pod.status.phase}"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "pod_name": pod_name,
            "namespace": namespace,
            "message": f"Failed to get pod status: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
