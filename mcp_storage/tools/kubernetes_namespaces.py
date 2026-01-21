"""
Kubernetes Namespaces Tool
List Kubernetes namespaces.
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


def list_namespaces() -> str:
    """
    List all namespaces in the cluster.
    
    Returns:
        JSON string containing:
        - namespaces: List of namespace information (name, status, age, pod_count)
        - total_count: Total number of namespaces
    """
    try:
        v1 = _get_k8s_client()
        namespaces = v1.list_namespace()
        
        namespace_list = []
        for ns in namespaces.items:
            # Calculate age
            age = ""
            if ns.metadata.creation_timestamp:
                from datetime import datetime, timezone
                age_delta = datetime.now(timezone.utc) - ns.metadata.creation_timestamp
                days = age_delta.days
                hours, remainder = divmod(age_delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                if days > 0:
                    age = f"{days}d{hours}h"
                elif hours > 0:
                    age = f"{hours}h{minutes}m"
                else:
                    age = f"{minutes}m"
            
            # Get phase/status
            status = ns.status.phase if ns.status.phase else "Active"
            
            # Count pods in namespace
            try:
                pods = v1.list_namespaced_pod(namespace=ns.metadata.name)
                pod_count = len(pods.items)
            except:
                pod_count = 0
            
            namespace_info = {
                "name": ns.metadata.name,
                "status": status,
                "age": age,
                "pod_count": pod_count
            }
            namespace_list.append(namespace_info)
        
        result = {
            "namespaces": namespace_list,
            "total_count": len(namespace_list),
            "message": f"Found {len(namespace_list)} namespace(s) in cluster"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to list namespaces: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
