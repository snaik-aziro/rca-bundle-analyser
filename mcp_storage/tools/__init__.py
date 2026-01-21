"""
Storage MCP Tools Package
"""

from .capacity import get_disk_capacity
from .iops import get_disk_iops
from .latency import get_disk_latency
from .rca import generate_storage_rca
from .partitions import get_disk_partitions
from .swap import get_swap_usage
from .inodes import get_inode_usage
from .process_io import get_top_io_processes
from .disk_health import get_disk_health
from .storage_trends import get_storage_trends
from .cleanup_recommendations import get_cleanup_recommendations

# Kubernetes tools
from .kubernetes_pods import list_pods, get_pod_status
from .kubernetes_nodes import list_nodes, get_node_status
from .kubernetes_namespaces import list_namespaces
from .kubernetes_resources import get_resource_usage
from .kubernetes_logs import get_pod_logs
from .kubernetes_events import get_events
from .kubernetes_health import get_cluster_health

__all__ = [
    "get_disk_capacity",
    "get_disk_iops",
    "get_disk_latency",
    "generate_storage_rca",
    "get_disk_partitions",
    "get_swap_usage",
    "get_inode_usage",
    "get_top_io_processes",
    "get_disk_health",
    "get_storage_trends",
    "get_cleanup_recommendations",
    # Kubernetes tools
    "list_pods",
    "get_pod_status",
    "list_nodes",
    "get_node_status",
    "list_namespaces",
    "get_resource_usage",
    "get_pod_logs",
    "get_events",
    "get_cluster_health"
]
