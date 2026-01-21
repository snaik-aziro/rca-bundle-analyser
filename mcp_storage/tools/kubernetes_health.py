"""
Kubernetes Cluster Health Tool
Get overall cluster health status.
"""

import json


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


def get_cluster_health() -> str:
    """
    Get overall cluster health status.
    
    Returns:
        JSON string containing:
        - status: Overall cluster status (HEALTHY, WARNING, CRITICAL)
        - nodes: Node health summary
        - pods: Pod health summary
        - issues: List of identified issues
        - summary: Health summary message
    """
    try:
        v1 = _get_k8s_client()
        
        # Get nodes
        nodes = v1.list_node()
        node_count = len(nodes.items)
        ready_nodes = 0
        not_ready_nodes = []
        
        for node in nodes.items:
            if node.status.conditions:
                for condition in node.status.conditions:
                    if condition.type == "Ready" and condition.status == "True":
                        ready_nodes += 1
                    elif condition.type == "Ready" and condition.status == "False":
                        not_ready_nodes.append({
                            "name": node.metadata.name,
                            "reason": condition.reason if condition.reason else "Unknown",
                            "message": condition.message if condition.message else "N/A"
                        })
        
        # Get pods
        pods = v1.list_pod_for_all_namespaces()
        pod_count = len(pods.items)
        running_pods = 0
        pending_pods = []
        failed_pods = []
        crash_loop_pods = []
        
        for pod in pods.items:
            if pod.status.phase == "Running":
                running_pods += 1
            elif pod.status.phase == "Pending":
                pending_pods.append({
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "reason": pod.status.reason if pod.status.reason else "N/A"
                })
            elif pod.status.phase == "Failed":
                failed_pods.append({
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "reason": pod.status.reason if pod.status.reason else "N/A"
                })
            
            # Check for crash loop
            if pod.status.container_statuses:
                for container in pod.status.container_statuses:
                    if container.state.waiting and "CrashLoopBackOff" in container.state.waiting.reason:
                        crash_loop_pods.append({
                            "name": pod.metadata.name,
                            "namespace": pod.metadata.namespace,
                            "container": container.name,
                            "reason": container.state.waiting.reason
                        })
        
        # Determine overall status
        issues = []
        status = "HEALTHY"
        
        if not_ready_nodes:
            status = "CRITICAL"
            issues.append(f"{len(not_ready_nodes)} node(s) not ready")
        
        if failed_pods:
            status = "CRITICAL" if status != "CRITICAL" else status
            issues.append(f"{len(failed_pods)} pod(s) in Failed state")
        
        if crash_loop_pods:
            status = "CRITICAL" if status != "CRITICAL" else status
            issues.append(f"{len(crash_loop_pods)} pod(s) in CrashLoopBackOff")
        
        if pending_pods:
            if len(pending_pods) > pod_count * 0.1:  # More than 10% pending
                status = "WARNING" if status == "HEALTHY" else status
                issues.append(f"{len(pending_pods)} pod(s) pending (high count)")
        
        if ready_nodes < node_count:
            if status == "HEALTHY":
                status = "WARNING"
        
        # Build result
        result = {
            "status": status,
            "nodes": {
                "total": node_count,
                "ready": ready_nodes,
                "not_ready": len(not_ready_nodes),
                "not_ready_details": not_ready_nodes
            },
            "pods": {
                "total": pod_count,
                "running": running_pods,
                "pending": len(pending_pods),
                "failed": len(failed_pods),
                "crash_loop": len(crash_loop_pods),
                "pending_details": pending_pods[:10],  # Limit details
                "failed_details": failed_pods[:10],
                "crash_loop_details": crash_loop_pods[:10]
            },
            "issues": issues if issues else ["No issues detected"],
            "message": f"Cluster status: {status}. {ready_nodes}/{node_count} nodes ready, {running_pods}/{pod_count} pods running."
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "status": "UNKNOWN",
            "message": f"Failed to get cluster health: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
