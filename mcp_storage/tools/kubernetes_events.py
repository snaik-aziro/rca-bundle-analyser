"""
Kubernetes Events Tool
Get Kubernetes events.
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


def get_events(namespace: Optional[str] = None, limit: int = 50) -> str:
    """
    Get Kubernetes events.
    
    Args:
        namespace: Optional namespace to filter events. If None, gets all namespaces.
        limit: Maximum number of events to return (default: 50)
    
    Returns:
        JSON string containing:
        - events: List of events (name, namespace, type, reason, message, time)
        - total_count: Total number of events
    """
    try:
        v1 = _get_k8s_client()
        
        if namespace:
            events = v1.list_namespaced_event(namespace=namespace)
        else:
            events = v1.list_event_for_all_namespaces()
        
        event_list = []
        for event in events.items[:limit]:
            # Calculate age
            age = ""
            if event.first_timestamp:
                from datetime import datetime, timezone
                age_delta = datetime.now(timezone.utc) - event.first_timestamp
                days = age_delta.days
                hours, remainder = divmod(age_delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                if days > 0:
                    age = f"{days}d{hours}h"
                elif hours > 0:
                    age = f"{hours}h{minutes}m"
                else:
                    age = f"{minutes}m"
            
            event_info = {
                "name": event.metadata.name,
                "namespace": event.metadata.namespace,
                "type": event.type,  # Normal or Warning
                "reason": event.reason if event.reason else "N/A",
                "message": event.message if event.message else "N/A",
                "involved_object": {
                    "kind": event.involved_object.kind if event.involved_object else "N/A",
                    "name": event.involved_object.name if event.involved_object else "N/A"
                },
                "count": event.count if event.count else 1,
                "age": age,
                "first_seen": str(event.first_timestamp) if event.first_timestamp else "N/A",
                "last_seen": str(event.last_timestamp) if event.last_timestamp else "N/A"
            }
            event_list.append(event_info)
        
        # Sort by most recent first
        event_list.sort(key=lambda x: x["first_seen"], reverse=True)
        
        result = {
            "events": event_list,
            "total_count": len(event_list),
            "limit": limit,
            "message": f"Found {len(event_list)} event(s)"
        }
        
        return json.dumps(result, indent=2)
    
    except Exception as e:
        error_result = {
            "error": str(e),
            "message": f"Failed to get events: {str(e)}"
        }
        return json.dumps(error_result, indent=2)
