"""
Kubernetes Nodes Tool
List and get status of Kubernetes nodes.
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


def list_nodes() -> str:
    """
    List all nodes in the cluster.
    
    Returns:
        JSON string containing:
        - nodes: List of node information (name, status, roles, version, resources)
        - total_count: Total number of nodes
    """
    try:
        v1 = _get_k8s_client()
        nodes = v1.list_node()
        
        node_list = []
        for node in nodes.items:
            # Get roles
            roles = []
            if node.metadata.labels:
                for key in node.metadata.labels:
                    if "node-role.kubernetes.io" in key:
                        role = key.split("/")[-1]
                        roles.append(role)
            if not roles:
                roles = ["worker"]
            
            # Get node conditions
            conditions = {}
            status = "Unknown"
            if node.status.conditions:
                for condition in node.status.conditions:
                    conditions[condition.type] = condition.status
                    if condition.type == "Ready":
                        status = "Ready" if condition.status == "True" else "NotReady"
            
            # Get resource capacity and allocatable
            capacity = {}
            allocatable = {}
            if node.status.capacity:
                capacity = {
                    "cpu": node.status.capacity.get("cpu", "N/A"),
                    "memory": node.status.capacity.get("memory", "N/A"),
                    "pods": node.status.capacity.get("pods", "N/A")
                }
            if node.status.allocatable:
                allocatable = {
                    "cpu": node.status.allocatable.get("cpu", "N/A"),
                    "memory": node.status.allocatable.get("memory", "N/A"),
                    "pods": node.status.allocatable.get("pods", "N/A")
                }
            
            node_info = {
                "name": node.metadata.name,
                "status": status,
                "roles": roles,
                "version": node.status.node_info.kubelet_version if node.status.node_info else "N/A",
                "os": f"{node.status.node_info.os_image if node.status.node_info else 'N/A'}",
                "kernel": node.status.node_info.kernel_version if node.status.node_info else "N/A",
                "container_runtime": node.status.node_info.container_runtime_version if node.status.node_info else "N/A",
                "capacity": capacity,
                "allocatable": allocatable,
                "conditions": conditions
            }
            node_list.append(node_info)
        
        result = {
            "nodes": node_list,
            "total_count": len(node_list),
            "message": f"Found {len(node_list)} node(s) in cluster"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to list nodes: {str(e)}"
        }
        return json.dumps(error_result, indent=2)


def get_node_status(node_name: str) -> str:
    """
    Get detailed status of a specific node.
    
    Args:
        node_name: Name of the node
    
    Returns:
        JSON string containing:
        - name: Node name
        - status: Node status
        - roles: Node roles
        - resources: Resource capacity and allocatable
        - conditions: Node conditions
        - pods: Pods running on this node
    """
    try:
        v1 = _get_k8s_client()
        
        node = v1.read_node(name=node_name)
        
        # Get roles
        roles = []
        if node.metadata.labels:
            for key in node.metadata.labels:
                if "node-role.kubernetes.io" in key:
                    role = key.split("/")[-1]
                    roles.append(role)
        if not roles:
            roles = ["worker"]
        
        # Get conditions
        conditions = []
        status = "Unknown"
        if node.status.conditions:
            for condition in node.status.conditions:
                conditions.append({
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason if condition.reason else "N/A",
                    "message": condition.message if condition.message else "N/A",
                    "last_transition_time": str(condition.last_transition_time) if condition.last_transition_time else "N/A"
                })
                if condition.type == "Ready":
                    status = "Ready" if condition.status == "True" else "NotReady"
        
        # Get resource capacity and allocatable
        capacity = {}
        allocatable = {}
        if node.status.capacity:
            capacity = {
                "cpu": node.status.capacity.get("cpu", "N/A"),
                "memory": node.status.capacity.get("memory", "N/A"),
                "pods": node.status.capacity.get("pods", "N/A")
            }
        if node.status.allocatable:
            allocatable = {
                "cpu": node.status.allocatable.get("cpu", "N/A"),
                "memory": node.status.allocatable.get("memory", "N/A"),
                "pods": node.status.allocatable.get("pods", "N/A")
            }
        
        # Get pods on this node
        pods = v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}")
        pod_list = [{"name": p.metadata.name, "namespace": p.metadata.namespace, "status": p.status.phase} 
                   for p in pods.items]
        
        result = {
            "name": node.metadata.name,
            "status": status,
            "roles": roles,
            "version": node.status.node_info.kubelet_version if node.status.node_info else "N/A",
            "os": node.status.node_info.os_image if node.status.node_info else "N/A",
            "kernel": node.status.node_info.kernel_version if node.status.node_info else "N/A",
            "container_runtime": node.status.node_info.container_runtime_version if node.status.node_info else "N/A",
            "capacity": capacity,
            "allocatable": allocatable,
            "conditions": conditions,
            "pods": pod_list,
            "pod_count": len(pod_list),
            "message": f"Node {node_name} is {status} with {len(pod_list)} pod(s)"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "node_name": node_name,
            "message": f"Failed to get node status: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
