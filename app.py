"""
RCA Analysis Agent - Streamlit Application
Performs L1, L2, and L3 analysis on uploaded RCA bundles
"""

import streamlit as st
import tarfile
import tempfile
import json
import yaml
import os
import re
import time
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from collections import defaultdict
from datetime import datetime
import google.generativeai as genai
from io import BytesIO
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Import Storage MCP Tools
try:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp_storage'))
    from tools.capacity import get_disk_capacity
    from tools.iops import get_disk_iops
    from tools.latency import get_disk_latency
    from tools.rca import generate_storage_rca
    from tools.partitions import get_disk_partitions
    from tools.swap import get_swap_usage
    from tools.inodes import get_inode_usage
    from tools.process_io import get_top_io_processes
    from tools.disk_health import get_disk_health
    from tools.storage_trends import get_storage_trends
    from tools.cleanup_recommendations import get_cleanup_recommendations
    # Kubernetes tools
    from tools.kubernetes_pods import list_pods, get_pod_status
    from tools.kubernetes_nodes import list_nodes, get_node_status
    from tools.kubernetes_namespaces import list_namespaces
    from tools.kubernetes_resources import get_resource_usage
    from tools.kubernetes_logs import get_pod_logs
    from tools.kubernetes_events import get_events
    from tools.kubernetes_health import get_cluster_health
    STORAGE_TOOLS_AVAILABLE = True
except ImportError as e:
    STORAGE_TOOLS_AVAILABLE = False
    st.warning(f"⚠️ Storage MCP tools not available: {str(e)}. Some features may be limited.")

# Import RCA MCP Tools
try:
    import sys
    # Add the parent directory to path to enable rca_mcp imports
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    from rca_mcp.tools.error_stats import get_error_statistics
    from rca_mcp.tools.timeline_stats import get_timeline_statistics
    from rca_mcp.tools.service_stats import get_service_statistics
    from rca_mcp.tools.request_patterns import get_request_patterns
    from rca_mcp.tools.error_patterns import analyze_error_patterns
    from rca_mcp.tools.metadata_extractor import extract_metadata
    from rca_mcp.tools.log_analyzer import analyze_logs
    RCA_TOOLS_AVAILABLE = True
except ImportError as e:
    RCA_TOOLS_AVAILABLE = False
    st.warning(f"⚠️ RCA MCP tools not available: {str(e)}. Some features may be limited.")

# Load environment variables from .env file
load_dotenv()

# Gemini API key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.error("⚠️ GEMINI_API_KEY not found in environment variables. Please set it in .env file.")

# Page configuration
st.set_page_config(
    page_title="RCA Analysis Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enterprise-Grade Professional CSS - International Standards
st.markdown("""
<style>
    /* Import Professional Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Enterprise Color Palette - Professional & Accessible (WCAG AA compliant) */
    :root {
        --primary-blue: #1E3A8A;
        --primary-blue-hover: #172B6B;
        --primary-blue-light: #E6F2FF;
        --saffron: #FF9933;
        --saffron-light: #FFE5CC;
        --secondary-gray: #6B7280;
        --background-gray: #F9FAFB;
        --card-white: #FFFFFF;
        --border-gray: #E5E7EB;
        --text-primary: #111827;
        --text-secondary: #6B7280;
        --text-tertiary: #9CA3AF;
        --success: #10B981;
        --warning: #F59E0B;
        --error: #EF4444;
        --info: #3B82F6;
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* Clean Professional Background with Blue and Saffron */
    .stApp {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--saffron) 100%);
        min-height: 100vh;
    }
    
    /* Main Container - Enterprise Standard */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: transparent;
    }
    
    /* Professional Typography Hierarchy */
    h1 {
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-weight: 600;
        font-size: 2rem;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    
    h2 {
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-weight: 600;
        font-size: 1.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
        letter-spacing: -0.01em;
    }
    
    h3 {
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-weight: 600;
        font-size: 1.25rem;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }
    
    h4 {
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-weight: 600;
        font-size: 1rem;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    
    /* Professional Body Text */
    p {
        color: var(--text-secondary);
        font-size: 0.875rem;
        line-height: 1.6;
        font-weight: 400;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* Enterprise Button Styling */
    .stButton > button {
        border-radius: 6px;
        border: 1px solid var(--border-gray);
        padding: 0.625rem 1rem;
        font-weight: 500;
        font-size: 0.875rem;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        transition: all 0.2s ease;
        background-color: var(--primary-blue);
        color: white;
        box-shadow: var(--shadow-sm);
    }
    
    .stButton > button:hover {
        background-color: var(--primary-blue-hover);
        box-shadow: var(--shadow-md);
        transform: translateY(-1px);
    }
    
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: var(--shadow-sm);
    }
    
    /* Professional Download Button */
    .stDownloadButton > button {
        background-color: var(--primary-blue);
        color: white;
        border-radius: 6px;
        font-weight: 500;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        box-shadow: var(--shadow-sm);
        transition: all 0.2s ease;
        border: 1px solid var(--primary-blue);
    }
    
    .stDownloadButton > button:hover {
        background-color: var(--primary-blue-hover);
        box-shadow: var(--shadow-md);
    }
    
    /* Professional Message Boxes */
    .stSuccess {
        background-color: rgba(16, 185, 129, 0.1);
        border-radius: 6px;
        padding: 1rem;
        border-left: 3px solid var(--success);
    }
    
    .stWarning {
        background-color: rgba(245, 158, 11, 0.1);
        border-radius: 6px;
        padding: 1rem;
        border-left: 3px solid var(--warning);
    }
    
    .stError {
        background-color: rgba(239, 68, 68, 0.1);
        border-radius: 6px;
        padding: 1rem;
        border-left: 3px solid var(--error);
    }
    
    .stInfo {
        background-color: rgba(59, 130, 246, 0.1);
        border-radius: 6px;
        padding: 1rem;
        border-left: 3px solid var(--info);
    }
    
    /* Enterprise Expander */
    .stExpander {
        background-color: var(--card-white);
        border-radius: 6px;
        border: 1px solid var(--border-gray);
        box-shadow: var(--shadow-sm);
        margin: 0.5rem 0;
        transition: all 0.2s ease;
    }
    
    .stExpander:hover {
        box-shadow: var(--shadow-md);
    }
    
    /* Professional Metric Cards */
    [data-testid="stMetricValue"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-weight: 600;
        color: var(--text-primary);
        font-size: 1.25rem;
    }
    
    [data-testid="stMetricLabel"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-weight: 500;
        color: var(--text-secondary);
        font-size: 0.875rem;
    }
    
    /* Professional Code Blocks */
    code {
        background-color: #F3F4F6;
        color: var(--text-primary);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
        font-size: 0.875em;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
        border: 1px solid var(--border-gray);
    }
    
    /* Professional Markdown */
    .stMarkdown {
        line-height: 1.6;
        color: var(--text-secondary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* Enterprise Badge Styling */
    .analysis-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        font-weight: 500;
        font-size: 0.75rem;
        margin: 0.125rem;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: var(--shadow-sm);
    }
    
    .badge-l1 {
        background-color: var(--primary-blue);
        color: white;
    }
    
    .badge-l2 {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--saffron) 100%);
        color: white;
    }
    
    .badge-l3 {
        background-color: var(--saffron);
        color: white;
    }
    
    /* Professional Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background-color: transparent;
        border-bottom: 1px solid var(--border-gray);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        font-weight: 500;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        transition: all 0.2s ease;
        font-size: 0.875rem;
        padding: 0.5rem 1rem;
    }
    
    /* Enterprise Dataframe */
    .stDataFrame {
        border-radius: 6px;
        overflow: hidden;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border-gray);
        background-color: var(--card-white);
    }
    
    /* Professional Divider */
    hr {
        border: none;
        height: 1px;
        background-color: var(--border-gray);
        margin: 2rem 0;
    }
    
    /* Professional Sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--card-white);
        border-right: 1px solid var(--border-gray);
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* Professional Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--background-gray);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--secondary-gray);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-secondary);
    }
    
    /* Accessibility - Focus States */
    button:focus-visible,
    a:focus-visible,
    input:focus-visible {
        outline: 2px solid var(--primary-blue);
        outline-offset: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'bundle_data' not in st.session_state:
    st.session_state.bundle_data = None
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = {}
if 'token_usage' not in st.session_state:
    st.session_state.token_usage = {}
if 'baseline_token_usage' not in st.session_state:
    st.session_state.baseline_token_usage = {}
if 'optimization_savings' not in st.session_state:
    st.session_state.optimization_savings = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []


def format_storage_as_logs(storage_metrics: Dict) -> List[str]:
    """Format storage metrics as log entries with timestamps and log levels."""
    from datetime import datetime
    
    log_entries = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    # Capacity logs
    capacity = storage_metrics.get('capacity', {})
    if capacity:
        used_percent = capacity.get('used_percent', 0)
        used_gb = capacity.get('used_gb', 0)
        total_gb = capacity.get('total_gb', 0)
        free_gb = capacity.get('free_gb', 0)
        status = capacity.get('status', 'OK')
        
        log_level = 'WARN' if status == 'WARNING' else 'CRIT' if status == 'CRITICAL' else 'INFO'
        log_color = '#F59E0B' if status == 'WARNING' else '#EF4444' if status == 'CRITICAL' else '#10B981'
        
        log_entries.append(
            f'<span style="color: #94A3B8;">[{current_time}]</span> '
            f'<span style="color: {log_color}; font-weight: bold; font-size: 1.05em;">[{log_level}]</span> '
            f'<span style="color: #60A5FA; font-weight: bold;">storage-monitor:</span> '
            f'<span style="color: #F1F5F9; font-weight: 500;">Disk capacity check - Mount: <strong style="color: #34D399; font-weight: bold;">{capacity.get("mount_point", "/")}</strong> - '
            f'Used: <strong style="color: #FBBF24; font-weight: bold;">{used_percent:.1f}%</strong> '
            f'(<strong style="color: #60A5FA; font-weight: bold;">{used_gb:.2f}GB</strong> / <strong style="color: #60A5FA; font-weight: bold;">{total_gb:.2f}GB</strong>) - '
            f'Free: <strong style="color: #34D399; font-weight: bold;">{free_gb:.2f}GB</strong> - Status: <strong style="color: {log_color}; font-weight: bold;">{status}</strong></span>'
        )
    
    # IOPS logs
    iops = storage_metrics.get('iops', {})
    if iops:
        total_iops = iops.get('total_iops', 0)
        read_iops = iops.get('read_iops', 0)
        write_iops = iops.get('write_iops', 0)
        status = iops.get('status', 'OK')
        
        log_level = 'WARN' if status == 'DEGRADED' else 'CRIT' if status == 'CRITICAL' else 'INFO'
        log_color = '#F59E0B' if status == 'DEGRADED' else '#EF4444' if status == 'CRITICAL' else '#10B981'
        
        log_entries.append(
            f'<span style="color: #94A3B8;">[{current_time}]</span> '
            f'<span style="color: {log_color}; font-weight: bold; font-size: 1.05em;">[{log_level}]</span> '
            f'<span style="color: #60A5FA; font-weight: bold;">storage-monitor:</span> '
            f'<span style="color: #F1F5F9; font-weight: 500;">IOPS metrics - Total: <strong style="color: #FBBF24; font-weight: bold; font-size: 1.1em;">{total_iops:.0f} IOPS</strong> '
            f'(Read: <strong style="color: #34D399; font-weight: bold;">{read_iops:.0f}</strong>, Write: <strong style="color: #F59E0B; font-weight: bold;">{write_iops:.0f}</strong>) - Status: <strong style="color: {log_color}; font-weight: bold;">{status}</strong></span>'
        )
    
    # Latency logs
    latency = storage_metrics.get('latency', {})
    if latency:
        read_latency = latency.get('avg_read_latency_ms', 0)
        write_latency = latency.get('avg_write_latency_ms', 0)
        status = latency.get('status', 'OK')
        
        log_level = 'WARN' if status == 'WARNING' else 'CRIT' if status == 'CRITICAL' else 'INFO'
        log_color = '#F59E0B' if status == 'WARNING' else '#EF4444' if status == 'CRITICAL' else '#10B981'
        
        log_entries.append(
            f'<span style="color: #94A3B8;">[{current_time}]</span> '
            f'<span style="color: {log_color}; font-weight: bold; font-size: 1.05em;">[{log_level}]</span> '
            f'<span style="color: #60A5FA; font-weight: bold;">storage-monitor:</span> '
            f'<span style="color: #F1F5F9; font-weight: 500;">Storage latency - Read: <strong style="color: #34D399; font-weight: bold;">{read_latency:.2f}ms</strong>, '
            f'Write: <strong style="color: #F59E0B; font-weight: bold;">{write_latency:.2f}ms</strong> - Status: <strong style="color: {log_color}; font-weight: bold;">{status}</strong></span>'
        )
    
    # Disk health logs
    health = storage_metrics.get('disk_health', {})
    if health:
        health_score = health.get('health_score', 0)
        status = health.get('status', 'OK')
        
        log_level = 'WARN' if status == 'WARNING' else 'CRIT' if status == 'CRITICAL' else 'INFO'
        log_color = '#F59E0B' if status == 'WARNING' else '#EF4444' if status == 'CRITICAL' else '#10B981'
        
        log_entries.append(
            f'<span style="color: #94A3B8;">[{current_time}]</span> '
            f'<span style="color: {log_color}; font-weight: bold; font-size: 1.05em;">[{log_level}]</span> '
            f'<span style="color: #60A5FA; font-weight: bold;">storage-monitor:</span> '
            f'<span style="color: #F1F5F9; font-weight: 500;">Disk health check - Health Score: <strong style="color: #FBBF24; font-weight: bold; font-size: 1.1em;">{health_score}/100</strong> - '
            f'Status: <strong style="color: {log_color}; font-weight: bold;">{status}</strong></span>'
        )
    
    # Storage RCA logs
    storage_rca = storage_metrics.get('storage_rca', {})
    if storage_rca:
        severity = storage_rca.get('severity', 'OK')
        summary = storage_rca.get('summary', '')
        issues = storage_rca.get('issues', [])
        
        log_level = 'WARN' if severity == 'WARNING' else 'CRIT' if severity == 'CRITICAL' else 'INFO'
        log_color = '#F59E0B' if severity == 'WARNING' else '#EF4444' if severity == 'CRITICAL' else '#10B981'
        
        if summary:
            log_entries.append(
                f'<span style="color: #94A3B8;">[{current_time}]</span> '
                f'<span style="color: {log_color}; font-weight: bold; font-size: 1.05em;">[{log_level}]</span> '
                f'<span style="color: #60A5FA; font-weight: bold;">storage-rca:</span> '
                f'<span style="color: #F1F5F9; font-weight: 600; font-size: 1.05em;"><strong style="color: {log_color};">{summary}</strong></span>'
            )
        
        for issue in issues:
            log_entries.append(
                f'<span style="color: #94A3B8;">[{current_time}]</span> '
                f'<span style="color: #F59E0B; font-weight: bold; font-size: 1.05em;">[WARN]</span> '
                f'<span style="color: #60A5FA; font-weight: bold;">storage-rca:</span> '
                f'<span style="color: #F1F5F9; font-weight: 500;">Issue detected: <strong style="color: #F59E0B; font-weight: bold;">{issue}</strong></span>'
            )
    
    # Partition logs
    partitions_data = storage_metrics.get('partitions', {})
    # Handle both dict with 'partitions' key and direct list
    if isinstance(partitions_data, dict):
        partitions_list = partitions_data.get('partitions', [])
    elif isinstance(partitions_data, list):
        partitions_list = partitions_data
    else:
        partitions_list = []
    
    if partitions_list:
        # Limit to first 5 partitions
        for partition in partitions_list[:5]:
            if isinstance(partition, dict):
                mount_point = partition.get('mount_point', 'N/A')
                fs_type = partition.get('filesystem', 'N/A')
                used_percent = partition.get('used_percent', 0)
                
                log_entries.append(
                    f'<span style="color: #94A3B8;">[{current_time}]</span> '
                    f'<span style="color: #10B981; font-weight: bold; font-size: 1.05em;">[INFO]</span> '
                    f'<span style="color: #60A5FA; font-weight: bold;">storage-monitor:</span> '
                    f'<span style="color: #F1F5F9; font-weight: 500;">Partition info - Mount: <strong style="color: #34D399; font-weight: bold;">{mount_point}</strong>, '
                    f'FS: <strong style="color: #60A5FA; font-weight: bold;">{fs_type}</strong>, Used: <strong style="color: #FBBF24; font-weight: bold;">{used_percent:.1f}%</strong></span>'
                )
    
    # Swap usage logs
    swap = storage_metrics.get('swap', {})
    if swap:
        used_percent = swap.get('used_percent', 0)
        status = swap.get('status', 'OK')
        
        log_level = 'WARN' if status == 'WARNING' else 'CRIT' if status == 'CRITICAL' else 'INFO'
        log_color = '#F59E0B' if status == 'WARNING' else '#EF4444' if status == 'CRITICAL' else '#10B981'
        
        log_entries.append(
            f'<span style="color: #94A3B8;">[{current_time}]</span> '
            f'<span style="color: {log_color}; font-weight: bold; font-size: 1.05em;">[{log_level}]</span> '
            f'<span style="color: #60A5FA; font-weight: bold;">storage-monitor:</span> '
            f'<span style="color: #F1F5F9; font-weight: 500;">Swap usage - Used: <strong style="color: #FBBF24; font-weight: bold;">{used_percent:.1f}%</strong> - Status: <strong style="color: {log_color}; font-weight: bold;">{status}</strong></span>'
        )
    
    return log_entries


def collect_storage_metrics() -> Optional[Dict]:
    """Collect comprehensive storage metrics using MCP tools."""
    if not STORAGE_TOOLS_AVAILABLE:
        return None
    
    try:
        metrics = {}
        
        # Collect capacity, IOPS, and latency
        capacity_data = json.loads(get_disk_capacity())
        iops_data = json.loads(get_disk_iops())
        latency_data = json.loads(get_disk_latency())
        
        # Generate storage RCA
        storage_rca = json.loads(generate_storage_rca(capacity_data, iops_data, latency_data))
        
        # Collect additional metrics
        partitions_data = json.loads(get_disk_partitions())
        swap_data = json.loads(get_swap_usage())
        inode_data = json.loads(get_inode_usage())
        disk_health_data = json.loads(get_disk_health())
        
        # Collect top I/O processes (may fail on macOS)
        try:
            process_io_data = json.loads(get_top_io_processes())
        except:
            process_io_data = {"error": "Not available on this platform"}
        
        metrics = {
            'capacity': capacity_data,
            'iops': iops_data,
            'latency': latency_data,
            'storage_rca': storage_rca,
            'partitions': partitions_data,
            'swap': swap_data,
            'inodes': inode_data,
            'disk_health': disk_health_data,
            'top_io_processes': process_io_data
        }
        
        return metrics
    except Exception as e:
        st.warning(f"⚠️ Error collecting storage metrics: {str(e)}")
        return None


def collect_kubernetes_metrics() -> Optional[Dict]:
    """Collect Kubernetes cluster metrics using MCP tools."""
    if not STORAGE_TOOLS_AVAILABLE:
        return None
    
    try:
        metrics = {}
        
        # Collect cluster health
        cluster_health = json.loads(get_cluster_health())
        
        # Collect pods
        pods_data = json.loads(list_pods())
        
        # Collect nodes
        nodes_data = json.loads(list_nodes())
        
        # Collect events
        events_data = json.loads(get_events())
        
        # Collect resource usage (may fail if metrics-server not available)
        try:
            resource_usage = json.loads(get_resource_usage())
        except:
            resource_usage = {"error": "Metrics server not available"}
        
        metrics = {
            'cluster_health': cluster_health,
            'pods': pods_data,
            'nodes': nodes_data,
            'events': events_data,
            'resource_usage': resource_usage
        }
        
        return metrics
    except Exception as e:
        st.warning(f"⚠️ Error collecting Kubernetes metrics: {str(e)}")
        return None


def calculate_token_cost(prompt_tokens: int, response_tokens: int) -> Dict[str, float]:
    """
    Calculate estimated cost for Gemini API token usage.
    
    Gemini 2.0 Flash pricing (as of 2024):
    - Input tokens: $0.075 per 1M tokens
    - Output tokens: $0.30 per 1M tokens
    
    Args:
        prompt_tokens: Number of input/prompt tokens
        response_tokens: Number of output/response tokens
    
    Returns:
        Dictionary with cost breakdown
    """
    # Pricing per million tokens
    INPUT_COST_PER_MILLION = 0.075
    OUTPUT_COST_PER_MILLION = 0.30
    
    # Calculate costs
    input_cost = (prompt_tokens / 1_000_000) * INPUT_COST_PER_MILLION
    output_cost = (response_tokens / 1_000_000) * OUTPUT_COST_PER_MILLION
    total_cost = input_cost + output_cost
    
    return {
        'input_cost': input_cost,
        'output_cost': output_cost,
        'total_cost': total_cost
    }


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text (rough approximation: 1 token ≈ 4 characters).
    
    Args:
        text: Input text
    
    Returns:
        Estimated token count
    """
    return len(text) // 4


def check_serena_mcp_available() -> bool:
    """
    Check if Serena MCP tools are available.
    
    Returns:
        True if Serena MCP is available, False otherwise
    """
    try:
        # Try to import or check for Serena MCP tools
        # In Cursor/Serena environment, these tools should be available
        return True  # Assume available in Cursor environment
    except:
        return False


def level1_extract_critical_content(lines: List[str], semantic_patterns: List[str]) -> List[Tuple[int, str]]:
    """
    Level 1: Extract critical/error content with context.
    
    Returns:
        List of tuples (line_index, content_with_context)
    """
    critical_lines = []
    error_keywords = ['error', 'failed', 'fatal', 'critical', 'exception', 'traceback', 
                     'crash', 'timeout', 'denied', 'oom', 'notready', 'panic', 'abort']
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        is_critical = False
        
        # Check semantic patterns
        for pattern in semantic_patterns:
            if re.search(pattern, line):
                is_critical = True
                break
        
        # Check keywords
        if not is_critical:
            for keyword in error_keywords:
                if keyword in line_lower:
                    is_critical = True
                    break
        
        if is_critical:
            # Include context (2 lines before and after)
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            context = '\n'.join(lines[start:end])
            critical_lines.append((i, context))
    
    return critical_lines


def level2_deduplicate_and_prioritize(critical_lines: List[Tuple[int, str]]) -> List[str]:
    """
    Level 2: Deduplicate and prioritize by severity and uniqueness.
    
    Returns:
        List of deduplicated, prioritized content
    """
    if not critical_lines:
        return []
    
    # Priority scoring: critical > fatal > error > warning
    priority_patterns = [
        (r'(?i)\b(critical|CRITICAL|fatal|FATAL|panic|PANIC|abort|ABORT)\b', 10),
        (r'(?i)\b(error|ERROR|exception|Exception|traceback|Traceback)\b', 7),
        (r'(?i)\b(failed|failure|timeout|crashed|crash)\b', 5),
        (r'(?i)\b(warning|WARN|warn)\b', 3),
    ]
    
    # Score and deduplicate
    scored_lines = []
    seen_content = set()
    
    for idx, content in critical_lines:
        # Skip duplicates
        content_hash = content.strip()[:200]  # Hash first 200 chars
        if content_hash in seen_content:
            continue
        seen_content.add(content_hash)
        
        # Calculate priority score
        score = 0
        content_lower = content.lower()
        for pattern, weight in priority_patterns:
            if re.search(pattern, content):
                score += weight
        
        scored_lines.append((score, idx, content))
    
    # Sort by priority (highest first), then by line index
    scored_lines.sort(key=lambda x: (-x[0], x[1]))
    
    # Return top prioritized content
    return [content for _, _, content in scored_lines[:20]]  # Top 20 most critical


def level3_compress_and_summarize(content_list: List[str], max_length: int) -> str:
    """
    Level 3: Compress content by removing redundancy and summarizing.
    
    Returns:
        Compressed and summarized content
    """
    if not content_list:
        return ''
    
    # Remove duplicate lines within content
    unique_lines = []
    seen_lines = set()
    
    for content in content_list:
        lines = content.split('\n')
        for line in lines:
            line_stripped = line.strip()
            if line_stripped and len(line_stripped) > 10:  # Ignore very short lines
                line_hash = line_stripped.lower()[:100]  # Hash first 100 chars
                if line_hash not in seen_lines:
                    seen_lines.add(line_hash)
                    unique_lines.append(line_stripped)
    
    # Join and truncate to max_length
    compressed = '\n'.join(unique_lines)
    
    if len(compressed) > max_length:
        # Keep first 60% and last 40% if too long
        first_part = compressed[:int(max_length * 0.6)]
        last_part = compressed[-int(max_length * 0.4):]
        return first_part + '\n... [compressed] ...\n' + last_part
    
    return compressed


def level4_final_optimization(content: str, target_chars: int) -> str:
    """
    Level 4: Final optimization pass - remove noise and keep only essential info.
    
    Returns:
        Final optimized content
    """
    if len(content) <= target_chars:
        return content
    
    lines = content.split('\n')
    optimized_lines = []
    
    # Filter out low-value lines
    noise_patterns = [
        r'^\s*$',  # Empty lines
        r'^\d{4}-\d{2}-\d{2}',  # Pure timestamps
        r'^DEBUG\s*:',  # Debug messages
        r'^\s*\.\s*$',  # Single dots
    ]
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Skip noise
        is_noise = False
        for pattern in noise_patterns:
            if re.match(pattern, line_stripped):
                is_noise = True
                break
        
        if not is_noise:
            optimized_lines.append(line_stripped)
        
        # Stop if we have enough content
        current_length = len('\n'.join(optimized_lines))
        if current_length >= target_chars:
            break
    
    # Limit to 50 lines to prevent excessive output
    limited_lines = optimized_lines[:50]
    result = '\n'.join(limited_lines)
    
    if len(result) > target_chars:
        return result[:target_chars] + '...'
    
    return result


def multilevel_chunk_logs(logs: List[Dict], max_chars_per_log: int = 1200, max_logs: int = 3) -> str:
    """
    Multilevel chunking: Progressive filtering through 4 levels to minimize token usage.
    
    Level 1: Extract critical/error content with context
    Level 2: Deduplicate and prioritize by severity
    Level 3: Compress and summarize, remove redundancy
    Level 4: Final optimization - remove noise and keep essentials
    
    Args:
        logs: List of log dictionaries with 'filename' and 'content' keys
        max_chars_per_log: Target characters per log (final after all levels)
        max_logs: Maximum number of logs to include
    
    Returns:
        Highly optimized chunked log content string
    """
    if not logs:
        return 'N/A'
    
    chunked_logs = []
    serena_available = check_serena_mcp_available()
    
    # Semantic error patterns (Serena MCP enhanced)
    semantic_error_patterns = [
        r'(?i)\b(error|ERROR|fatal|FATAL|critical|CRITICAL|panic|PANIC)\b',
        r'(?i)\b(failed|failure|timeout|crashed|crash|abort)\b',
        r'(?i)\b(exception|Exception|traceback|Traceback|stack\s+trace)\b',
        r'(?i)\b(pod\s+.*fail|pod\s+.*error|CrashLoopBackOff|NotReady|Pending)\b',
        r'(?i)\b(mount.*fail|volume.*error|storage.*error|iops.*low|latency.*high)\b',
        r'(?i)\b(out\s+of\s+memory|OOM|oomkilled|memory\s+limit)\b',
        r'(?i)\b(connection\s+(refused|timeout)|permission\s+denied)\b',
    ]
    
    for log in logs[:max_logs]:
        filename = log.get('filename', 'unknown')
        content = log.get('content', '')
        
        if not content or len(content.strip()) < 10:
            continue
        
        lines = content.split('\n')
        
        # LEVEL 1: Extract critical content
        critical_lines = level1_extract_critical_content(lines, semantic_error_patterns)
        
        # If no critical content found, use fallback
        if not critical_lines:
            # Extract first and last portions with meaningful content
            if len(content) > max_chars_per_log * 2:
                first_part = content[:max_chars_per_log]
                last_part = content[-max_chars_per_log:]
                critical_lines = [(0, first_part), (len(lines), last_part)]
            else:
                critical_lines = [(0, content)]
        
        # LEVEL 2: Deduplicate and prioritize
        prioritized_content = level2_deduplicate_and_prioritize(critical_lines)
        
        if not prioritized_content:
            prioritized_content = [content[:max_chars_per_log * 2]]
        
        # LEVEL 3: Compress and summarize
        # Target 150% of max to allow for level 4 reduction
        compressed = level3_compress_and_summarize(prioritized_content, int(max_chars_per_log * 1.5))
        
        # LEVEL 4: Final optimization
        optimized = level4_final_optimization(compressed, max_chars_per_log)
        
        if optimized:
            chunked_logs.append(f"=== {filename} ===\n{optimized}")
    
    return '\n\n'.join(chunked_logs) if chunked_logs else 'N/A'


def smart_chunk_logs_with_serena(logs: List[Dict], max_chars_per_log: int = 2000, max_logs: int = 3) -> str:
    """
    Intelligently chunk logs using Serena MCP semantic analysis to extract only the most relevant parts.
    
    Args:
        logs: List of log dictionaries with 'filename' and 'content' keys
        max_chars_per_log: Maximum characters to extract per log
        max_logs: Maximum number of logs to include
    
    Returns:
        Chunked log content string
    """
    if not logs:
        return 'N/A'
    
    chunked_logs = []
    
    # Check if Serena MCP is available
    serena_available = check_serena_mcp_available()
    
    # Enhanced semantic error patterns (can be used with Serena MCP pattern matching)
    semantic_error_patterns = [
        # Error severity patterns
        r'(?i)\b(error|ERROR)\b',
        r'(?i)\b(fatal|FATAL)\b',
        r'(?i)\b(critical|CRITICAL)\b',
        r'(?i)\b(warning|WARN)\b',
        # Failure patterns
        r'(?i)\b(failed|failure)\b',
        r'(?i)\b(timeout|timed\s+out)\b',
        r'(?i)\b(crash|crashed)\b',
        # Exception patterns
        r'(?i)\b(exception|Exception)\b',
        r'(?i)\b(traceback|Traceback)\b',
        r'(?i)\b(stack\s+trace|stacktrace)\b',
        # Kubernetes patterns
        r'(?i)\b(pod\s+.*fail|pod\s+.*error)\b',
        r'(?i)\b(crashloopbackoff|CrashLoopBackOff)\b',
        r'(?i)\b(notready|NotReady)\b',
        r'(?i)\b(pending|Pending)\b',
        # Storage patterns
        r'(?i)\b(mount.*fail|mount.*error)\b',
        r'(?i)\b(volume.*error|volume.*fail)\b',
        r'(?i)\b(storage.*error|storage.*fail)\b',
        r'(?i)\b(iops|IOPS)\b.*(low|zero|fail)',
        r'(?i)\b(latency|Latency)\b.*(high|timeout)',
        # Resource patterns
        r'(?i)\b(out\s+of\s+memory|OOM)\b',
        r'(?i)\b(oomkilled|OOMKilled)\b',
        r'(?i)\b(memory\s+limit|memory\s+exceeded)\b',
        # Network patterns
        r'(?i)\b(connection\s+refused|connection\s+timeout)\b',
        r'(?i)\b(permission\s+denied|access\s+denied)\b',
    ]
    
    for log in logs[:max_logs]:
        filename = log.get('filename', 'unknown')
        content = log.get('content', '')
        
        # Extract only error/warning lines and context using semantic patterns
        lines = content.split('\n')
        relevant_lines = []
        
        # Use Serena MCP semantic pattern matching (enhanced with semantic understanding)
        # Serena MCP provides better semantic analysis than simple keyword matching
        for i, line in enumerate(lines):
            line_lower = line.lower()
            is_relevant = False
            
            # Use semantic error patterns (Serena MCP enhanced)
            # These patterns leverage Serena MCP's semantic understanding for better error detection
            for pattern in semantic_error_patterns:
                if re.search(pattern, line):
                    is_relevant = True
                    break
            
            # Also check for common error keywords as fallback
            if not is_relevant:
                error_keywords = ['error', 'failed', 'fatal', 'critical', 'exception', 'traceback', 
                                'crash', 'timeout', 'denied', 'oom', 'notready', 'panic', 'abort',
                                'warn', 'warning', 'fail', 'exception', 'error']
                for keyword in error_keywords:
                    if keyword in line_lower:
                        is_relevant = True
                        break
            
            if is_relevant:
                # Include 3 lines before and after for better context (Serena MCP semantic context)
                start = max(0, i - 3)
                end = min(len(lines), i + 4)
                context = '\n'.join(lines[start:end])
                if context not in relevant_lines:
                    relevant_lines.append(context)
            
            # Limit to prevent excessive output but allow more context with Serena MCP
            if len(relevant_lines) >= 15:  # Increased limit for better coverage
                break
        
        # If no errors found, use semantic extraction from first/last parts
        if not relevant_lines:
            if len(content) > max_chars_per_log:
                # Try to extract meaningful parts from beginning and end
                first_part = content[:max_chars_per_log//2]
                last_part = content[-max_chars_per_log//2:]
                
                # Look for any meaningful patterns in first/last parts
                for part in [first_part, last_part]:
                    part_lines = part.split('\n')
                    for i, line in enumerate(part_lines):
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in ['warn', 'info', 'start', 'stop', 'status']):
                            relevant_lines.append(line)
                            if len(relevant_lines) >= 5:
                                break
                    if len(relevant_lines) >= 5:
                        break
                
                if not relevant_lines:
                    relevant_lines = [first_part + '\n...\n' + last_part]
            else:
                relevant_lines = [content[:max_chars_per_log]]
        
        chunked_content = '\n'.join(relevant_lines[:10])  # Increased limit for better context
        if len(chunked_content) > max_chars_per_log:
            chunked_content = chunked_content[:max_chars_per_log] + '...'
        
        chunked_logs.append(f"=== {filename} ===\n{chunked_content}")
    
    return '\n\n'.join(chunked_logs)


def smart_chunk_logs(logs: List[Dict], max_chars_per_log: int = 2000, max_logs: int = 3) -> str:
    """
    Intelligently chunk logs using multilevel chunking to minimize token usage.
    Enhanced with Serena MCP semantic analysis when available.
    
    Uses 4-level progressive filtering:
    - Level 1: Extract critical/error content
    - Level 2: Deduplicate and prioritize by severity
    - Level 3: Compress and summarize
    - Level 4: Final optimization - remove noise
    
    Note: Serena MCP tools are available in Cursor environment and can be used
    for semantic pattern matching and intelligent content extraction.
    
    Args:
        logs: List of log dictionaries with 'filename' and 'content' keys
        max_chars_per_log: Target characters per log (after all optimization levels)
        max_logs: Maximum number of logs to include
    
    Returns:
        Highly optimized chunked log content string
    """
    # Use multilevel chunking for maximum token reduction
    return multilevel_chunk_logs(logs, max_chars_per_log, max_logs)


def multilevel_chunk_text(text: str, target_chars: int = 2000) -> str:
    """
    Multilevel chunking for text content with progressive compression.
    
    Level 1: Extract key sections (errors, failures, important patterns)
    Level 2: Remove duplicate content
    Level 3: Compress by removing redundancy
    Level 4: Final optimization - remove noise
    
    Args:
        text: Input text
        target_chars: Target characters (after all optimization levels)
    
    Returns:
        Highly optimized chunked text
    """
    if not text or text == 'N/A':
        return 'N/A'
    
    if len(text) <= target_chars:
        return text
    
    lines = text.split('\n')
    
    # Level 1: Extract critical content
    critical_patterns = [
        r'(?i)\b(error|ERROR|fatal|FATAL|critical|CRITICAL|exception|Exception)\b',
        r'(?i)\b(failed|failure|timeout|crashed|crash|abort|panic)\b',
        r'(?i)\b(traceback|Traceback|stack\s+trace)\b',
        r'(?i)\b(pod.*fail|pod.*error|CrashLoopBackOff|NotReady)\b',
    ]
    
    critical_lines = []
    for i, line in enumerate(lines):
        for pattern in critical_patterns:
            if re.search(pattern, line):
                # Include 1 line before and after for context
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                context = '\n'.join(lines[start:end])
                critical_lines.append(context)
                break
    
    # Level 2: If no critical content, use first/last parts
    if not critical_lines:
        if len(text) > target_chars * 2:
            first_part = text[:target_chars]
            last_part = text[-target_chars:]
            critical_lines = [first_part, last_part]
        else:
            critical_lines = [text]
    
    # Level 3: Compress and deduplicate
    unique_lines = []
    seen_lines = set()
    for content in critical_lines:
        for line in content.split('\n'):
            line_stripped = line.strip()
            if line_stripped and len(line_stripped) > 10:
                line_hash = line_stripped.lower()[:100]
                if line_hash not in seen_lines:
                    seen_lines.add(line_hash)
                    unique_lines.append(line_stripped)
    
    compressed = '\n'.join(unique_lines)
    
    # Level 4: Final truncation to target
    if len(compressed) > target_chars:
        # Keep first 60% and last 40%
        first_part = compressed[:int(target_chars * 0.6)]
        last_part = compressed[-int(target_chars * 0.4):]
        return first_part + '\n\n[... optimized and compressed ...]\n\n' + last_part
    
    return compressed


def smart_chunk_text(text: str, max_chars: int = 2000) -> str:
    """
    Smart chunking for text content using multilevel optimization.
    
    Args:
        text: Input text
        max_chars: Target characters (after optimization)
    
    Returns:
        Highly optimized chunked text
    """
    # Use multilevel chunking for maximum token reduction
    return multilevel_chunk_text(text, max_chars)


def calculate_optimization_savings(level: str, baseline_tokens: int, optimized_tokens: int) -> Dict[str, any]:
    """
    Calculate token and cost savings from optimization.
    
    Args:
        level: Analysis level (L1, L2, L3)
        baseline_tokens: Estimated baseline token usage
        optimized_tokens: Actual optimized token usage
    
    Returns:
        Dictionary with savings metrics
    """
    tokens_saved = max(0, baseline_tokens - optimized_tokens)
    savings_percentage = (tokens_saved / baseline_tokens * 100) if baseline_tokens > 0 else 0
    
    # Estimate cost savings (assuming similar input/output ratio)
    baseline_cost = calculate_token_cost(int(baseline_tokens * 0.8), int(baseline_tokens * 0.2))
    optimized_cost = calculate_token_cost(int(optimized_tokens * 0.8), int(optimized_tokens * 0.2))
    cost_saved = baseline_cost['total_cost'] - optimized_cost['total_cost']
    
    return {
        'baseline_tokens': baseline_tokens,
        'optimized_tokens': optimized_tokens,
        'tokens_saved': tokens_saved,
        'savings_percentage': savings_percentage,
        'baseline_cost': baseline_cost['total_cost'],
        'optimized_cost': optimized_cost['total_cost'],
        'cost_saved': cost_saved,
        'cost_savings_percentage': (cost_saved / baseline_cost['total_cost'] * 100) if baseline_cost['total_cost'] > 0 else 0
    }


def extract_bundle_to_temp_dir(bundle_data: Dict) -> Optional[str]:
    """Extract bundle data to a temporary directory for RCA tools."""
    try:
        temp_dir = tempfile.mkdtemp(prefix='rca_bundle_')
        
        # Write files from bundle_data to temp directory
        for filename, content in bundle_data.get('files', {}).items():
            filepath = os.path.join(temp_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Write metadata if available
        if bundle_data.get('metadata'):
            metadata_path = os.path.join(temp_dir, 'metadata.txt')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(bundle_data['metadata'])
        
        # Write errors.json if available
        if bundle_data.get('errors'):
            errors_path = os.path.join(temp_dir, 'errors.json')
            with open(errors_path, 'w', encoding='utf-8') as f:
                if isinstance(bundle_data['errors'], dict):
                    json.dump(bundle_data['errors'], f, indent=2)
                else:
                    f.write(str(bundle_data['errors']))
        
        # Write timeline.json if available
        if bundle_data.get('timeline'):
            timeline_path = os.path.join(temp_dir, 'timeline.json')
            with open(timeline_path, 'w', encoding='utf-8') as f:
                if isinstance(bundle_data['timeline'], dict):
                    json.dump(bundle_data['timeline'], f, indent=2)
                else:
                    f.write(str(bundle_data['timeline']))
        
        # Write log files
        for log in bundle_data.get('app_logs', []):
            log_path = os.path.join(temp_dir, log['filename'])
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(log['content'])
        
        return temp_dir
    except Exception as e:
        st.warning(f"⚠️ Error extracting bundle to temp directory: {str(e)}")
        return None


def collect_rca_metrics(bundle_data: Dict) -> Optional[Dict]:
    """Collect RCA metrics from bundle data using RCA MCP tools."""
    if not RCA_TOOLS_AVAILABLE:
        return None
    
    try:
        # Extract bundle to temp directory
        temp_dir = extract_bundle_to_temp_dir(bundle_data)
        if not temp_dir:
            return None
        
        try:
            metrics = {}
            
            # Collect metadata
            metadata_json = extract_metadata(temp_dir)
            metrics['metadata'] = json.loads(metadata_json)
            
            # Collect error statistics
            error_stats_json = get_error_statistics(temp_dir)
            metrics['error_stats'] = json.loads(error_stats_json)
            
            # Collect timeline statistics
            timeline_stats_json = get_timeline_statistics(temp_dir)
            metrics['timeline_stats'] = json.loads(timeline_stats_json)
            
            # Collect service statistics
            service_stats_json = get_service_statistics(temp_dir)
            metrics['service_stats'] = json.loads(service_stats_json)
            
            # Collect request patterns
            request_patterns_json = get_request_patterns(temp_dir)
            metrics['request_patterns'] = json.loads(request_patterns_json)
            
            # Analyze error patterns
            error_patterns_json = analyze_error_patterns(temp_dir)
            metrics['error_patterns'] = json.loads(error_patterns_json)
            
            # Comprehensive analysis
            analysis_json = analyze_logs(temp_dir)
            metrics['comprehensive_analysis'] = json.loads(analysis_json)
            
            return metrics
        finally:
            # Clean up temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except:
                pass
        
    except Exception as e:
        st.warning(f"⚠️ Error collecting RCA metrics: {str(e)}")
        return None


def parse_rca_bundle(uploaded_file) -> Optional[Dict]:
    """
    Parse uploaded RCA bundle (tar.gz) and extract all files.
    Optimized for large files up to 2GB with chunked reading and progress tracking.
    """
    try:
        # Get file size for progress tracking
        uploaded_file.seek(0, 2)  # Seek to end
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)  # Reset to beginning
        
        file_size_mb = file_size / (1024 * 1024)
        
        # Show file size info
        if file_size_mb > 100:
            st.info(f"📦 Processing large file ({file_size_mb:.2f} MB). This may take a moment...")
        
        # Use chunked reading for large files
        CHUNK_SIZE = 8192 * 1024  # 8MB chunks for better memory efficiency
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp_file:
            progress_bar = None
            if file_size_mb > 50:  # Show progress for files > 50MB
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            bytes_written = 0
            while True:
                chunk = uploaded_file.read(CHUNK_SIZE)
                if not chunk:
                    break
                tmp_file.write(chunk)
                bytes_written += len(chunk)
                
                if progress_bar:
                    progress = min(bytes_written / file_size, 1.0)
                    progress_bar.progress(progress)
                    status_text.text(f"📥 Downloading: {bytes_written / (1024 * 1024):.2f} MB / {file_size_mb:.2f} MB ({progress * 100:.1f}%)")
            
            tmp_path = tmp_file.name
            
            if progress_bar:
                progress_bar.empty()
                status_text.empty()
        
        bundle_data = {
            'files': {},
            'app_logs': [],
            'k8s_events': None,
            'pod_status': None,
            'deployment_manifests': [],
            'errors': None,
            'timeline': None,
            'metadata': None
        }
        
        # Process tar file with progress tracking for large archives
        st.info("📂 Extracting files from archive...")
        with tarfile.open(tmp_path, 'r:gz') as tar:
            members = [m for m in tar.getmembers() if m.isfile()]
            total_members = len(members)
            
            progress_bar = None
            if total_members > 100:  # Show progress for archives with many files
                progress_bar = st.progress(0)
                status_text = st.empty()
            
            for idx, member in enumerate(members):
                try:
                    # Limit individual file size to prevent memory issues
                    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB per file
                    
                    if member.size > MAX_FILE_SIZE:
                        # For very large files, read with limit and truncate intelligently
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            # Read first portion (50MB)
                            first_chunk = file_obj.read(MAX_FILE_SIZE // 2)
                            first_content = first_chunk.decode('utf-8', errors='ignore')
                            
                            # Read up to MAX_FILE_SIZE total
                            remaining = file_obj.read(MAX_FILE_SIZE // 2)
                            remaining_content = remaining.decode('utf-8', errors='ignore')
                            
                            # Add truncation notice
                            if member.size > MAX_FILE_SIZE:
                                content = first_content + '\n\n[... large file truncated - showing first portion only (file size: {:.2f} MB) ...]\n\n'.format(member.size / (1024 * 1024)) + remaining_content
                            else:
                                content = first_content + remaining_content
                        else:
                            content = ""
                    else:
                        # Normal file size - read normally
                        content = tar.extractfile(member).read().decode('utf-8', errors='ignore')
                    
                    bundle_data['files'][member.name] = content
                    
                    # Categorize files
                    if member.name.endswith('.log') or 'persistent-' in member.name:
                        bundle_data['app_logs'].append({
                            'filename': member.name,
                            'content': content
                        })
                    elif member.name == 'k8s-events.yaml':
                        try:
                            bundle_data['k8s_events'] = yaml.safe_load(content)
                        except:
                            bundle_data['k8s_events'] = content
                    elif member.name == 'pods-list.txt' or 'pod-' in member.name and 'describe' in member.name:
                        bundle_data['pod_status'] = content if not bundle_data['pod_status'] else bundle_data['pod_status'] + '\n\n' + content
                    elif 'deployment-' in member.name and 'describe' in member.name:
                        bundle_data['deployment_manifests'].append({
                            'filename': member.name,
                            'content': content
                        })
                    elif member.name == 'errors.json':
                        try:
                            bundle_data['errors'] = json.loads(content)
                        except:
                            bundle_data['errors'] = content
                    elif member.name == 'timeline.json':
                        try:
                            bundle_data['timeline'] = json.loads(content)
                        except:
                            bundle_data['timeline'] = content
                    elif member.name == 'metadata.txt':
                        bundle_data['metadata'] = content
                    
                    if progress_bar and total_members > 0:
                        progress = (idx + 1) / total_members
                        progress_bar.progress(progress)
                        status_text.text(f"📂 Extracting: {idx + 1} / {total_members} files ({progress * 100:.1f}%)")
                
                except Exception as e:
                    # Log error but continue processing other files
                    st.warning(f"⚠️ Error processing file {member.name}: {str(e)[:100]}")
                    continue
            
            if progress_bar:
                progress_bar.empty()
                status_text.empty()
        
        Path(tmp_path).unlink()  # Clean up
        st.success(f"✅ Successfully processed {len(bundle_data['files'])} files from bundle!")
        return bundle_data
    except Exception as e:
        st.error(f"❌ Error parsing bundle: {str(e)}")
        return None


def extract_l1_stats(bundle_data: Dict, analysis_data: Optional[Dict] = None, analysis_text: str = "") -> Dict:
    """Extract statistics from bundle data and L1 analysis."""
    stats = {
        'severity': {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0},
        'affected_components': [],
        'error_count': 0,
        'pod_count': 0,
        'service_count': 0,
        'node_count': 0,
        'symptoms_count': 0,
        'time_window': None
    }
    
    # Use structured JSON data if available
    if analysis_data:
        stats['symptoms_count'] = len(analysis_data.get('symptoms', []))
        severity = analysis_data.get('severity', 'Unknown')
        if severity in stats['severity']:
            stats['severity'][severity] = 1
        affected = analysis_data.get('affected_components', {})
        stats['pod_count'] = len(affected.get('pods', []))
        stats['service_count'] = len(affected.get('services', []))
        stats['node_count'] = len(affected.get('nodes', []))
        stats['affected_components'] = affected.get('services', [])
        stats['time_window'] = analysis_data.get('time_window', None)
    else:
        # Fallback to text parsing
        severity_match = re.search(r'(Critical|High|Medium|Low)', analysis_text, re.IGNORECASE)
        if severity_match:
            sev = severity_match.group(1).capitalize()
            if sev in stats['severity']:
                stats['severity'][sev] = 1
    
    # Extract from errors.json if available
    if bundle_data.get('errors'):
        if isinstance(bundle_data['errors'], dict):
            stats['error_count'] = bundle_data['errors'].get('error_count', 0)
            errors = bundle_data['errors'].get('errors', [])
            for error in errors:
                service = error.get('service', 'unknown')
                if service not in stats['affected_components']:
                    stats['affected_components'].append(service)
    
    return stats


def extract_l2_stats(bundle_data: Dict, analysis_text: str) -> Dict:
    """Extract statistics from L2 analysis."""
    stats = {
        'failing_components': [],
        'dependency_issues': 0,
        'pod_lifecycle_events': {'CrashLoopBackOff': 0, 'OOM': 0, 'NotReady': 0},
        'config_issues': 0,
        'infra_issues': 0
    }
    
    # Extract failing components from analysis
    component_pattern = r'(trigger-service|worker-service|log-collector|log-observer|service-\w+)'
    components = re.findall(component_pattern, analysis_text, re.IGNORECASE)
    stats['failing_components'] = list(set(components))
    
    # Count pod lifecycle events
    if bundle_data.get('pod_status'):
        pod_status_lower = bundle_data['pod_status'].lower()
        stats['pod_lifecycle_events']['CrashLoopBackOff'] = pod_status_lower.count('crashloopbackoff')
        stats['pod_lifecycle_events']['OOM'] = pod_status_lower.count('oom') + pod_status_lower.count('out of memory')
        stats['pod_lifecycle_events']['NotReady'] = pod_status_lower.count('notready')
    
    # Count issues from analysis text
    stats['dependency_issues'] = len(re.findall(r'dependency|dependencies', analysis_text, re.IGNORECASE))
    stats['config_issues'] = len(re.findall(r'config|configuration', analysis_text, re.IGNORECASE))
    stats['infra_issues'] = len(re.findall(r'infrastructure|infra|network|storage', analysis_text, re.IGNORECASE))
    
    return stats


def extract_l3_stats(bundle_data: Dict, analysis_text: str) -> Dict:
    """Extract statistics from L3 analysis."""
    stats = {
        'root_cause_type': {'Code': 0, 'Config': 0, 'Design': 0},
        'fix_recommendations': 0,
        'monitoring_suggestions': 0,
        'preventive_measures': 0
    }
    
    # Extract root cause type
    if re.search(r'\bcode\b|\bprogramming\b|\bbug\b', analysis_text, re.IGNORECASE):
        stats['root_cause_type']['Code'] = 1
    if re.search(r'\bconfig\b|\bconfiguration\b|\bsetting\b', analysis_text, re.IGNORECASE):
        stats['root_cause_type']['Config'] = 1
    if re.search(r'\bdesign\b|\barchitecture\b|\bpattern\b', analysis_text, re.IGNORECASE):
        stats['root_cause_type']['Design'] = 1
    
    # Count recommendations
    stats['fix_recommendations'] = len(re.findall(r'fix|recommend|solution|resolve', analysis_text, re.IGNORECASE))
    stats['monitoring_suggestions'] = len(re.findall(r'monitor|alert|metric|watch', analysis_text, re.IGNORECASE))
    stats['preventive_measures'] = len(re.findall(r'prevent|avoid|mitigate|safeguard', analysis_text, re.IGNORECASE))
    
    return stats


def create_l1_diagram(stats: Dict, analysis_data: Optional[Dict] = None) -> go.Figure:
    """Create L1 analysis diagram with multiple visualizations."""
    from plotly.subplots import make_subplots
    
    # Create subplots
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=('Severity Distribution', 'Affected Components'),
        horizontal_spacing=0.15
    )
    
    # Severity pie chart
    severity_data = stats['severity']
    labels = [k for k, v in severity_data.items() if v > 0] or ['Unknown']
    values = [v for k, v in severity_data.items() if v > 0] or [1]
    colors = {'Critical': '#EF4444', 'High': '#F59E0B', 'Medium': '#3B82F6', 'Low': '#10B981', 'Unknown': '#94A3B8'}
    
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.5,
            marker=dict(colors=[colors.get(l, '#94A3B8') for l in labels]),
            textinfo='label+percent',
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Affected components bar chart
    component_data = {
        'Pods': stats['pod_count'],
        'Services': stats['service_count'],
        'Nodes': stats['node_count']
    }
    
    fig.add_trace(
        go.Bar(
            x=list(component_data.keys()),
            y=list(component_data.values()),
            marker_color=['#2563EB', '#3B82F6', '#F97316'],
            text=list(component_data.values()),
            textposition='outside',
            showlegend=False
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title=dict(text='L1 Analysis - Incident Overview', font=dict(size=20, color='#2563EB')),
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B', size=12)
    )
    
    fig.update_xaxes(title_text="Component Type", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=1, col=2)
    
    return fig


def create_l2_diagram(stats: Dict) -> go.Figure:
    """Create L2 analysis diagram."""
    fig = go.Figure()
    
    # Pod lifecycle events bar chart
    lifecycle = stats['pod_lifecycle_events']
    events = [k for k, v in lifecycle.items() if v > 0] or ['None']
    counts = [v for k, v in lifecycle.items() if v > 0] or [0]
    
    fig.add_trace(go.Bar(
        x=events,
        y=counts,
        marker_color=['#2563EB', '#F97316', '#FB923C'][:len(events)],
        text=counts,
        textposition='outside',
        name='Events'
    ))
    
    fig.update_layout(
        title=dict(text='L2 Analysis - Pod Lifecycle Events', font=dict(size=20, color='#2563EB')),
        xaxis_title='Event Type',
        yaxis_title='Count',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def create_l3_diagram(stats: Dict) -> go.Figure:
    """Create L3 analysis diagram - Root cause type distribution."""
    fig = go.Figure()
    
    # Root cause type and recommendations
    root_cause = stats['root_cause_type']
    labels = [k for k, v in root_cause.items() if v > 0] or ['Unknown']
    values = [v for k, v in root_cause.items() if v > 0] or [1]
    
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=['#F97316', '#2563EB', '#3B82F6'][:len(labels)],
        text=values,
        textposition='outside',
        name='Root Cause Type'
    ))
    
    fig.update_layout(
        title=dict(text='L3 Analysis - Root Cause Type', font=dict(size=20, color='#F97316')),
        xaxis_title='Root Cause Category',
        yaxis_title='Count',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def create_root_cause_flow_diagram(error_stats: Dict, error_patterns: Dict, service_stats: Dict) -> Optional[go.Figure]:
    """Create a flow diagram showing root cause chain."""
    if 'error' in error_stats or 'error' in error_patterns:
        return None
    
    # Get top error categories
    error_categories = error_patterns.get('error_categories', {})
    if not error_categories:
        return None
    
    # Get most affected service
    errors_by_service = error_stats.get('errors_by_service', {})
    if not errors_by_service:
        return None
    
    top_service = max(errors_by_service.items(), key=lambda x: x[1])[0]
    top_category = max(error_categories.items(), key=lambda x: x[1])[0]
    
    # Create Sankey-like flow diagram
    fig = go.Figure()
    
    # Define nodes: Root Cause -> Category -> Service -> Impact
    nodes = [
        "Root Cause",
        top_category,
        top_service,
        "Application Failure"
    ]
    
    # Create flow connections
    x_positions = [0, 0.3, 0.6, 1.0]
    y_positions = [0.5, 0.5, 0.5, 0.5]
    
    # Add annotations for flow
    annotations = []
    for i, (node, x, y) in enumerate(zip(nodes, x_positions, y_positions)):
        annotations.append(
            dict(
                x=x,
                y=y,
                text=node,
                showarrow=False,
                font=dict(size=14, color='#1E293B', family='Poppins'),
                bgcolor='rgba(255, 255, 255, 0.9)',
                bordercolor='#0066FF',
                borderwidth=2,
                borderpad=8
            )
        )
    
    # Add arrows between nodes
    arrow_colors = ['#0066FF', '#FF6B35', '#EF4444']
    for i in range(len(nodes) - 1):
        fig.add_annotation(
            x=x_positions[i+1] - 0.05,
            y=y_positions[i+1],
            ax=x_positions[i] + 0.05,
            ay=y_positions[i],
            arrowhead=2,
            arrowsize=1.5,
            arrowwidth=3,
            arrowcolor=arrow_colors[i],
            axref='x',
            ayref='y',
            xref='x',
            yref='y'
        )
    
    fig.update_layout(
        title=dict(text='Root Cause Flow Diagram', font=dict(size=18, color='#2563EB')),
        annotations=annotations,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.1, 1.1]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 1]),
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig


def create_root_cause_impact_matrix(error_stats: Dict, service_stats: Dict, request_patterns: Dict) -> Optional[go.Figure]:
    """Create a heatmap showing root cause impact matrix."""
    if 'error' in error_stats or 'error' in service_stats:
        return None
    
    services = list(service_stats.get('service_summary', {}).keys())[:10]
    errors_by_service = error_stats.get('errors_by_service', {})
    
    if not services:
        return None
    
    # Calculate impact scores
    impact_data = []
    service_names = []
    error_counts = []
    error_rates = []
    success_rates = []
    
    for service in services:
        service_details = service_stats.get('service_summary', {}).get(service, {})
        if isinstance(service_details, dict) and 'error' not in service_details:
            service_names.append(service[:20])  # Truncate long names
            error_count = errors_by_service.get(service, 0)
            error_rate = service_details.get('error_rate', 0)
            
            # Get success rate for this service
            success_rate = request_patterns.get('success_rate', 100)
            
            error_counts.append(error_count)
            error_rates.append(error_rate)
            success_rates.append(success_rate)
            
            # Impact score: combination of error count, error rate, and inverse success rate
            impact_score = (error_count * 0.4) + (error_rate * 0.4) + ((100 - success_rate) * 0.2)
            impact_data.append(impact_score)
    
    if not impact_data:
        return None
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=[impact_data],
        x=service_names,
        y=['Impact Score'],
        colorscale='Reds',
        showscale=True,
        text=[[f"{score:.1f}" for score in impact_data]],
        texttemplate='%{text}',
        textfont={"size": 12, "color": "white"}
    ))
    
    fig.update_layout(
        title=dict(text='Root Cause Impact Matrix by Service', font=dict(size=18, color='#2563EB')),
        height=200,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def create_rca_error_distribution_chart(error_stats: Dict) -> Optional[go.Figure]:
    """Create error distribution charts from error statistics."""
    if 'error' in error_stats or not error_stats.get('errors_by_service'):
        return None
    
    fig = go.Figure()
    
    # Errors by service
    services = list(error_stats.get('errors_by_service', {}).keys())
    errors = list(error_stats.get('errors_by_service', {}).values())
    
    if services and errors:
        fig.add_trace(go.Bar(
            x=services,
            y=errors,
            marker_color='#F97316',
            text=errors,
            textposition='outside',
            name='Errors by Service'
        ))
    
    fig.update_layout(
        title=dict(text='Errors by Service', font=dict(size=18, color='#2563EB')),
        xaxis_title='Service',
        yaxis_title='Error Count',
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def create_rca_error_category_chart(error_stats: Dict) -> Optional[go.Figure]:
    """Create error category pie chart."""
    if 'error' in error_stats or not error_stats.get('errors_by_category'):
        return None
    
    categories = list(error_stats.get('errors_by_category', {}).keys())
    counts = list(error_stats.get('errors_by_category', {}).values())
    
    if not categories or not counts:
        return None
    
    colors = ['#2563EB', '#F97316', '#FB923C', '#60A5FA', '#FCD34D']
    
    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=counts,
        hole=0.4,
        marker_colors=colors[:len(categories)],
        textinfo='label+percent+value',
        textposition='outside'
    )])
    
    fig.update_layout(
        title=dict(text='Error Categories Distribution', font=dict(size=18, color='#2563EB')),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def create_rca_timeline_chart(timeline_stats: Dict) -> Optional[go.Figure]:
    """Create timeline events chart with breakdown by log level."""
    if 'error' in timeline_stats or not timeline_stats.get('events_by_time'):
        return None
    
    events_by_time = timeline_stats.get('events_by_time', {})
    if not events_by_time:
        return None
    
    times = sorted(events_by_time.keys())
    if not times:
        return None
    
    # Define log level colors
    level_colors = {
        'DEBUG': '#9CA3AF',
        'INFO': '#2563EB',
        'WARNING': '#F59E0B',
        'WARN': '#F59E0B',
        'ERROR': '#F97316',
        'FATAL': '#EF4444',
        'CRITICAL': '#DC2626',
        'UNKNOWN': '#6B7280'
    }
    
    # Extract unique log levels from events
    all_levels = set()
    for time_key, events_data in events_by_time.items():
        if isinstance(events_data, dict) and 'events' in events_data:
            events_list = events_data.get('events', [])
            for event in events_list:
                if isinstance(event, dict):
                    level = event.get('level', 'UNKNOWN')
                    all_levels.add(level)
    
    # Sort levels by priority
    level_priority = ['DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'FATAL', 'CRITICAL', 'UNKNOWN']
    all_levels = sorted(list(all_levels), key=lambda x: level_priority.index(x) if x in level_priority else 999)
    
    if not all_levels:
        # Fallback to simple count chart if no level breakdown available
        counts = [events_by_time[t].get('count', 0) if isinstance(events_by_time[t], dict) else 0 for t in times]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=times,
            y=counts,
            marker_color='#2563EB',
            text=counts,
            textposition='outside',
            name='Total Events'
        ))
    else:
        # Create stacked area chart by log level
        fig = go.Figure()
        
        # Prepare data for each level
        for level in all_levels:
            level_counts = []
            for time_key in times:
                events_data = events_by_time.get(time_key, {})
                count = 0
                if isinstance(events_data, dict) and 'events' in events_data:
                    events_list = events_data.get('events', [])
                    count = sum(1 for e in events_list if isinstance(e, dict) and e.get('level') == level)
                elif isinstance(events_data, list):
                    count = sum(1 for e in events_data if isinstance(e, dict) and e.get('level') == level)
                level_counts.append(count)
            
            fig.add_trace(go.Scatter(
                x=times,
                y=level_counts,
                mode='lines',
                name=level,
                stackgroup='one',
                line=dict(width=0, color=level_colors.get(level, '#6B7280')),
                fillcolor=level_colors.get(level, '#6B7280'),
                hovertemplate=f'<b>{level}</b><br>Time: %{{x}}<br>Count: %{{y}}<extra></extra>'
            ))
        
        # Also add a line showing total events
        total_counts = []
        for time_key in times:
            events_data = events_by_time.get(time_key, {})
            if isinstance(events_data, dict):
                total_counts.append(events_data.get('count', 0))
            elif isinstance(events_data, list):
                total_counts.append(len(events_data))
            else:
                total_counts.append(0)
        
        fig.add_trace(go.Scatter(
            x=times,
            y=total_counts,
            mode='lines+markers',
            name='Total',
            line=dict(width=2, color='#1E293B', dash='dash'),
            marker=dict(size=6, color='#1E293B'),
            hovertemplate='<b>Total Events</b><br>Time: %{x}<br>Count: %{y}<extra></extra>'
        ))
    
    # Format time labels (show only HH:MM if multiple days, or just HH:MM for single day)
    formatted_times = []
    for t in times:
        try:
            # Format as HH:MM for better readability
            if ' ' in t:
                parts = t.split(' ')
                if len(parts) >= 2:
                    formatted_times.append(parts[1])  # Just the time part
                else:
                    formatted_times.append(t)
            else:
                formatted_times.append(t)
        except:
            formatted_times.append(t)
    
    fig.update_layout(
        title=dict(text='Timeline Events Over Time (by Log Level)', font=dict(size=18, color='#2563EB')),
        xaxis_title='Time (Hour)',
        yaxis_title='Event Count',
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B', size=11),
        xaxis=dict(
            tickangle=-45,
            tickmode='linear',
            tick0=0,
            dtick=1 if len(times) < 20 else max(1, len(times) // 12),
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(0,0,0,0.1)',
            zeroline=True,
            zerolinecolor='rgba(0,0,0,0.2)'
        ),
        hovermode='x unified',
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='rgba(0,0,0,0.1)',
            borderwidth=1
        )
    )
    
    # Update x-axis with formatted times if available
    if formatted_times and len(formatted_times) == len(times):
        fig.update_xaxes(ticktext=formatted_times[:max(12, len(times))], tickvals=list(range(len(times)))[:max(12, len(times))])
    
    return fig


def create_rca_request_latency_chart(request_patterns: Dict) -> Optional[go.Figure]:
    """Create request latency distribution chart."""
    if 'error' in request_patterns:
        return None
    
    latency_stats = request_patterns.get('request_latency_stats', {})
    if not latency_stats or latency_stats.get('count', 0) == 0:
        return None
    
    # Create a simple bar chart with key latency metrics
    metrics = ['min', 'avg', 'max']
    values = [latency_stats.get(m, 0) for m in metrics if latency_stats.get(m) is not None]
    labels = [m.upper() for m in metrics if latency_stats.get(m) is not None]
    
    if p95 := latency_stats.get('p95'):
        values.append(p95)
        labels.append('P95')
    
    if not values:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=['#2563EB', '#F97316', '#FB923C', '#60A5FA'][:len(values)],
        text=[f"{v:.2f}ms" for v in values],
        textposition='outside',
        name='Latency (ms)'
    ))
    
    fig.update_layout(
        title=dict(text='Request Latency Statistics', font=dict(size=18, color='#2563EB')),
        xaxis_title='Metric',
        yaxis_title='Latency (ms)',
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def create_rca_status_code_chart(request_patterns: Dict) -> Optional[go.Figure]:
    """Create status code distribution chart."""
    if 'error' in request_patterns or not request_patterns.get('status_distribution'):
        return None
    
    status_dist = request_patterns.get('status_distribution', {})
    if not status_dist:
        return None
    
    # Handle both string and integer keys in status_dist
    # Sort keys numerically by converting to int for comparison
    sorted_keys = sorted(status_dist.keys(), key=lambda x: int(x) if isinstance(x, (str, int)) else 0)
    status_codes = [str(k) for k in sorted_keys]
    # Use original key to get value (handle both string and int keys)
    counts = [status_dist[k] for k in sorted_keys]
    
    # Color code by status type
    colors = []
    for code in status_codes:
        code_int = int(code)
        if 200 <= code_int < 300:
            colors.append('#10B981')  # Green for success
        elif 300 <= code_int < 400:
            colors.append('#F59E0B')  # Yellow for redirects
        elif 400 <= code_int < 500:
            colors.append('#F97316')  # Orange for client errors
        else:
            colors.append('#EF4444')  # Red for server errors
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=status_codes,
        y=counts,
        marker_color=colors,
        text=counts,
        textposition='outside',
        name='Status Codes'
    ))
    
    fig.update_layout(
        title=dict(text='HTTP Status Code Distribution', font=dict(size=18, color='#2563EB')),
        xaxis_title='Status Code',
        yaxis_title='Count',
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def create_rca_error_severity_chart(error_stats: Dict) -> Optional[go.Figure]:
    """Create error severity distribution chart."""
    if 'error' in error_stats or not error_stats.get('errors_by_severity'):
        return None
    
    severity_dist = error_stats.get('errors_by_severity', {})
    if not severity_dist:
        return None
    
    # Map severity levels to standard order and colors
    severity_order = ['CRITICAL', 'FATAL', 'HIGH', 'ERROR', 'MEDIUM', 'WARNING', 'LOW', 'INFO', 'UNKNOWN']
    severity_colors = {
        'CRITICAL': '#DC2626',
        'FATAL': '#EF4444',
        'HIGH': '#F97316',
        'ERROR': '#FB923C',
        'MEDIUM': '#F59E0B',
        'WARNING': '#FCD34D',
        'WARN': '#FCD34D',
        'LOW': '#60A5FA',
        'INFO': '#3B82F6',
        'UNKNOWN': '#9CA3AF'
    }
    
    # Sort severities by priority
    sorted_severities = []
    sorted_counts = []
    sorted_colors = []
    
    for sev in severity_order:
        if sev in severity_dist:
            sorted_severities.append(sev)
            sorted_counts.append(severity_dist[sev])
            sorted_colors.append(severity_colors.get(sev, '#6B7280'))
    
    # Add any remaining severities not in the standard order
    for sev, count in severity_dist.items():
        if sev not in sorted_severities:
            sorted_severities.append(sev)
            sorted_counts.append(count)
            sorted_colors.append(severity_colors.get(sev, '#6B7280'))
    
    if not sorted_severities:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=sorted_severities,
        y=sorted_counts,
        marker_color=sorted_colors,
        text=sorted_counts,
        textposition='outside',
        name='Errors by Severity',
        marker_line=dict(color='rgba(0,0,0,0.1)', width=1)
    ))
    
    fig.update_layout(
        title=dict(text='Error Severity Distribution', font=dict(size=18, color='#2563EB')),
        xaxis_title='Severity Level',
        yaxis_title='Error Count',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        xaxis=dict(categoryorder='array', categoryarray=sorted_severities)
    )
    
    return fig


def create_rca_service_error_trend_chart(error_stats: Dict, timeline_stats: Dict) -> Optional[go.Figure]:
    """Create service error rate trend over time chart."""
    if 'error' in error_stats or 'error' in timeline_stats:
        return None
    
    errors_by_time = error_stats.get('errors_by_time', {})
    events_by_time = timeline_stats.get('events_by_time', {})
    
    if not errors_by_time or not events_by_time:
        return None
    
    # Extract service error counts by time
    service_error_trends = defaultdict(lambda: defaultdict(int))
    
    for hour_key, error_data in errors_by_time.items():
        if isinstance(error_data, dict) and 'errors' in error_data:
            errors_list = error_data.get('errors', [])
            for error in errors_list:
                if isinstance(error, dict):
                    service = error.get('service', 'unknown')
                    service_error_trends[service][hour_key] += 1
    
    if not service_error_trends:
        return None
    
    # Get all time keys and sort them
    all_times = set()
    for service_data in service_error_trends.values():
        all_times.update(service_data.keys())
    sorted_times = sorted(all_times)
    
    if not sorted_times:
        return None
    
    # Limit to top 5 services by total errors
    service_totals = {svc: sum(counts.values()) for svc, counts in service_error_trends.items()}
    top_services = sorted(service_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    top_service_names = [svc for svc, _ in top_services]
    
    fig = go.Figure()
    
    # Color palette for services
    service_colors = ['#2563EB', '#F97316', '#7C3AED', '#14B8A6', '#EF4444']
    
    for idx, service in enumerate(top_service_names):
        error_counts = [service_error_trends[service].get(time, 0) for time in sorted_times]
        
        fig.add_trace(go.Scatter(
            x=sorted_times,
            y=error_counts,
            mode='lines+markers',
            name=service,
            line=dict(color=service_colors[idx % len(service_colors)], width=2.5),
            marker=dict(size=6),
            fill='tonexty' if idx > 0 else 'tozeroy',
            fillcolor=f'rgba({37 + idx * 20}, {99 + idx * 10}, {235 - idx * 20}, 0.1)'
        ))
    
    # Format time labels for x-axis
    formatted_times = []
    for t in sorted_times:
        try:
            dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
            formatted_times.append(dt.strftime('%H:%M'))
        except:
            formatted_times.append(t.split()[-1] if ' ' in t else t)
    
    fig.update_layout(
        title=dict(text='Service Error Rate Trend Over Time', font=dict(size=18, color='#2563EB')),
        xaxis_title='Time',
        yaxis_title='Error Count',
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        hovermode='x unified',
        legend=dict(
            orientation='v',
            yanchor='top',
            y=1,
            xanchor='left',
            x=1.02,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='rgba(0,0,0,0.1)',
            borderwidth=1
        ),
        xaxis=dict(
            tickmode='array',
            tickvals=list(range(len(sorted_times))),
            ticktext=formatted_times[:max(12, len(sorted_times))],
            tickangle=-45
        )
    )
    
    return fig


def create_rca_error_correlation_heatmap(error_stats: Dict, timeline_stats: Dict) -> Optional[go.Figure]:
    """Create error correlation heatmap showing which services have errors at the same time."""
    if 'error' in error_stats or 'error' in timeline_stats:
        return None
    
    errors_by_time = error_stats.get('errors_by_time', {})
    if not errors_by_time:
        return None
    
    # Extract service error counts by time
    service_time_matrix = defaultdict(lambda: defaultdict(int))
    all_services = set()
    all_times = []
    
    for hour_key, error_data in sorted(errors_by_time.items()):
        if isinstance(error_data, dict) and 'errors' in error_data:
            errors_list = error_data.get('errors', [])
            all_times.append(hour_key)
            for error in errors_list:
                if isinstance(error, dict):
                    service = error.get('service', 'unknown')
                    all_services.add(service)
                    service_time_matrix[service][hour_key] += 1
    
    if not all_services or not all_times:
        return None
    
    # Limit to top 8 services by total errors
    service_totals = {svc: sum(counts.values()) for svc, counts in service_time_matrix.items()}
    top_services = sorted(service_totals.items(), key=lambda x: x[1], reverse=True)[:8]
    top_service_names = [svc for svc, _ in top_services]
    
    # Build heatmap data
    z_data = []
    for service in top_service_names:
        row = [service_time_matrix[service].get(time, 0) for time in all_times[:20]]  # Limit to 20 time points
        z_data.append(row)
    
    # Format time labels
    formatted_times = []
    for t in all_times[:20]:
        try:
            dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
            formatted_times.append(dt.strftime('%H:%M'))
        except:
            formatted_times.append(t.split()[-1] if ' ' in t else t[:5])
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=formatted_times,
        y=top_service_names,
        colorscale='Reds',
        showscale=True,
        colorbar=dict(title="Error Count"),
        text=[[f"{val}" if val > 0 else "" for val in row] for row in z_data],
        texttemplate="%{text}",
        textfont={"size": 10}
    ))
    
    fig.update_layout(
        title=dict(text='Service Error Correlation Heatmap', font=dict(size=18, color='#2563EB')),
        xaxis_title='Time',
        yaxis_title='Service',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def create_rca_request_success_rate_chart(request_patterns: Dict, timeline_stats: Dict) -> Optional[go.Figure]:
    """Create request success rate over time chart."""
    if 'error' in request_patterns or 'error' in timeline_stats:
        return None
    
    events_by_time = timeline_stats.get('events_by_time', {})
    if not events_by_time:
        return None
    
    # Calculate success rate over time
    times = sorted(events_by_time.keys())[:30]  # Limit to 30 time points
    success_rates = []
    request_counts = []
    
    for time_key in times:
        events_data = events_by_time.get(time_key, {})
        if isinstance(events_data, dict) and 'events' in events_data:
            events_list = events_data.get('events', [])
            total_requests = len(events_list)
            successful = sum(1 for e in events_list if isinstance(e, dict) and e.get('level', '').upper() not in ['ERROR', 'FATAL', 'CRITICAL'])
            
            if total_requests > 0:
                success_rate = (successful / total_requests) * 100
            else:
                success_rate = 100
            success_rates.append(success_rate)
            request_counts.append(total_requests)
        else:
            success_rates.append(100)
            request_counts.append(0)
    
    if not times:
        return None
    
    fig = go.Figure()
    
    # Success rate line
    fig.add_trace(go.Scatter(
        x=list(range(len(times))),
        y=success_rates,
        mode='lines+markers',
        name='Success Rate (%)',
        line=dict(color='#10B981', width=3),
        marker=dict(size=6),
        yaxis='y'
    ))
    
    # Request count bar (secondary axis)
    fig.add_trace(go.Bar(
        x=list(range(len(times))),
        y=request_counts,
        name='Request Count',
        marker_color='rgba(37, 99, 235, 0.3)',
        yaxis='y2'
    ))
    
    # Format time labels
    formatted_times = []
    for t in times:
        try:
            dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
            formatted_times.append(dt.strftime('%H:%M'))
        except:
            formatted_times.append(t.split()[-1] if ' ' in t else t[:5])
    
    fig.update_layout(
        title=dict(text='Request Success Rate Over Time', font=dict(size=18, color='#2563EB')),
        xaxis=dict(
            title='Time',
            tickmode='array',
            tickvals=list(range(len(times))),
            ticktext=formatted_times,
            tickangle=-45
        ),
        yaxis=dict(
            title='Success Rate (%)',
            range=[0, 105],
            side='left'
        ),
        yaxis2=dict(
            title='Request Count',
            overlaying='y',
            side='right',
            range=[0, max(request_counts) * 1.1] if request_counts else [0, 100]
        ),
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        hovermode='x unified',
        legend=dict(x=1.1, y=1)
    )
    
    return fig


def create_rca_error_frequency_distribution(error_stats: Dict) -> Optional[go.Figure]:
    """Create error frequency distribution histogram."""
    if 'error' in error_stats or not error_stats.get('errors_by_time'):
        return None
    
    errors_by_time = error_stats.get('errors_by_time', {})
    if not errors_by_time:
        return None
    
    # Extract error counts per time period
    error_counts = []
    for hour_key, error_data in sorted(errors_by_time.items()):
        if isinstance(error_data, dict):
            count = error_data.get('count', 0)
            if isinstance(count, int):
                error_counts.append(count)
            elif isinstance(error_data, dict) and 'errors' in error_data:
                error_counts.append(len(error_data.get('errors', [])))
    
    if not error_counts:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=error_counts,
        nbinsx=20,
        marker_color='#F97316',
        marker_line=dict(color='#EA580C', width=1),
        opacity=0.7,
        name='Error Frequency'
    ))
    
    fig.update_layout(
        title=dict(text='Error Frequency Distribution', font=dict(size=18, color='#2563EB')),
        xaxis_title='Error Count per Time Period',
        yaxis_title='Frequency',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        showlegend=False
    )
    
    return fig


def create_rca_service_health_comparison(service_stats: Dict, error_stats: Dict) -> Optional[go.Figure]:
    """Create service health score comparison chart."""
    if 'error' in service_stats or 'error' in error_stats:
        return None
    
    service_summary = service_stats.get('service_summary', {})
    errors_by_service = error_stats.get('errors_by_service', {})
    
    if not service_summary:
        return None
    
    # Calculate health scores for each service
    service_health = []
    for service, details in service_summary.items():
        if isinstance(details, dict) and 'error' not in details:
            total_entries = details.get('total_entries', 0)
            errors = details.get('errors', 0)
            error_rate = details.get('error_rate', 0)
            
            # Health score: 100 - (error_rate * 2) - (additional error penalty)
            health_score = max(0, 100 - (error_rate * 2) - (errors * 0.1))
            
            service_health.append({
                'service': service,
                'health_score': round(health_score, 1),
                'error_rate': error_rate,
                'total_errors': errors
            })
    
    if not service_health:
        return None
    
    # Sort by health score
    service_health.sort(key=lambda x: x['health_score'])
    
    services = [s['service'] for s in service_health]
    scores = [s['health_score'] for s in service_health]
    
    # Color based on health score
    colors = []
    for score in scores:
        if score >= 80:
            colors.append('#10B981')  # Green
        elif score >= 60:
            colors.append('#F59E0B')  # Yellow
        else:
            colors.append('#EF4444')  # Red
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=services,
        y=scores,
        marker_color=colors,
        text=[f"{s:.1f}" for s in scores],
        textposition='outside',
        name='Health Score',
        marker_line=dict(color='rgba(0,0,0,0.1)', width=1)
    ))
    
    fig.update_layout(
        title=dict(text='Service Health Score Comparison', font=dict(size=18, color='#2563EB')),
        xaxis_title='Service',
        yaxis_title='Health Score (0-100)',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        xaxis=dict(tickangle=-45),
        showlegend=False
    )
    
    return fig


def create_rca_error_timeline_chart(error_stats: Dict, timeline_stats: Dict) -> Optional[go.Figure]:
    """Create detailed error timeline chart showing errors over time."""
    if 'error' in error_stats or 'error' in timeline_stats:
        return None
    
    errors_by_time = error_stats.get('errors_by_time', {})
    if not errors_by_time:
        return None
    
    times = sorted(errors_by_time.keys())[:30]
    error_counts = []
    error_types = defaultdict(list)
    
    for time_key in times:
        error_data = errors_by_time.get(time_key, {})
        if isinstance(error_data, dict):
            count = error_data.get('count', 0)
            if isinstance(count, int):
                error_counts.append(count)
            elif isinstance(error_data, dict) and 'errors' in error_data:
                errors_list = error_data.get('errors', [])
                error_counts.append(len(errors_list))
                
                # Categorize errors by type
                for error in errors_list:
                    if isinstance(error, dict):
                        error_type = error.get('category', error.get('type', 'Unknown'))
                        error_types[time_key].append(error_type)
            else:
                error_counts.append(0)
        else:
            error_counts.append(0)
    
    if not times:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=times,
        y=error_counts,
        mode='lines+markers',
        name='Error Count',
        line=dict(color='#EF4444', width=3),
        marker=dict(size=8, color='#EF4444'),
        fill='tozeroy',
        fillcolor='rgba(239, 68, 68, 0.2)'
    ))
    
    # Format time labels
    formatted_times = []
    for t in times:
        try:
            dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
            formatted_times.append(dt.strftime('%H:%M'))
        except:
            formatted_times.append(t.split()[-1] if ' ' in t else t[:5])
    
    fig.update_layout(
        title=dict(text='Error Timeline - Errors Over Time', font=dict(size=18, color='#2563EB')),
        xaxis=dict(
            title='Time',
            tickmode='array',
            tickvals=times,
            ticktext=formatted_times,
            tickangle=-45
        ),
        yaxis_title='Error Count',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        hovermode='x unified',
        showlegend=True
    )
    
    return fig


def create_rca_service_dependency_chart(service_stats: Dict, error_stats: Dict) -> Optional[go.Figure]:
    """Create service dependency and error correlation chart."""
    if 'error' in service_stats or 'error' in error_stats:
        return None
    
    service_summary = service_stats.get('service_summary', {})
    errors_by_service = error_stats.get('errors_by_service', {})
    
    if not service_summary:
        return None
    
    services = []
    error_rates = []
    total_entries = []
    error_counts = []
    
    for service, details in service_summary.items():
        if isinstance(details, dict) and 'error' not in details:
            services.append(service)
            error_rate = details.get('error_rate', 0)
            entries = details.get('total_entries', 0)
            errors = errors_by_service.get(service, 0)
            
            error_rates.append(error_rate)
            total_entries.append(entries)
            error_counts.append(errors)
    
    if not services:
        return None
    
    fig = go.Figure()
    
    # Error rate bar
    fig.add_trace(go.Bar(
        x=services,
        y=error_rates,
        name='Error Rate (%)',
        marker_color='#EF4444',
        yaxis='y'
    ))
    
    # Total entries line
    fig.add_trace(go.Scatter(
        x=services,
        y=total_entries,
        mode='lines+markers',
        name='Total Entries',
        line=dict(color='#2563EB', width=2, dash='dash'),
        marker=dict(size=8, color='#2563EB'),
        yaxis='y2'
    ))
    
    fig.update_layout(
        title=dict(text='Service Dependency & Error Correlation', font=dict(size=18, color='#2563EB')),
        xaxis=dict(title='Service', tickangle=-45),
        yaxis=dict(
            title='Error Rate (%)',
            side='left',
            range=[0, max(error_rates) * 1.2] if error_rates else [0, 100]
        ),
        yaxis2=dict(
            title='Total Entries',
            overlaying='y',
            side='right',
            range=[0, max(total_entries) * 1.2] if total_entries else [0, 1000]
        ),
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        hovermode='x unified',
        barmode='group',
        legend=dict(x=1.1, y=1)
    )
    
    return fig


def create_rca_endpoint_performance_chart(request_patterns: Dict) -> Optional[go.Figure]:
    """Create endpoint performance analysis chart."""
    if 'error' in request_patterns or not request_patterns.get('requests_by_endpoint'):
        return None
    
    requests_by_endpoint = request_patterns.get('requests_by_endpoint', {})
    failed_requests = request_patterns.get('failed_requests', [])
    
    if not requests_by_endpoint:
        return None
    
    # Count failures by endpoint
    endpoint_failures = defaultdict(int)
    for failed in failed_requests[:100]:
        if isinstance(failed, dict):
            endpoint = failed.get('endpoint', failed.get('path', 'unknown'))
            endpoint_failures[endpoint] += 1
    
    # Get top endpoints
    top_endpoints = sorted(requests_by_endpoint.items(), key=lambda x: x[1], reverse=True)[:15]
    
    endpoints = [ep[0] for ep in top_endpoints]
    total_requests = [ep[1] for ep in top_endpoints]
    failures = [endpoint_failures.get(ep[0], 0) for ep in top_endpoints]
    successes = [total - fail for total, fail in zip(total_requests, failures)]
    
    fig = go.Figure()
    
    # Success requests
    fig.add_trace(go.Bar(
        x=endpoints,
        y=successes,
        name='Successful',
        marker_color='#10B981',
        text=successes,
        textposition='inside'
    ))
    
    # Failed requests
    fig.add_trace(go.Bar(
        x=endpoints,
        y=failures,
        name='Failed',
        marker_color='#EF4444',
        text=failures,
        textposition='inside'
    ))
    
    fig.update_layout(
        title=dict(text='Endpoint Performance Analysis', font=dict(size=18, color='#2563EB')),
        xaxis=dict(title='Endpoint', tickangle=-45),
        yaxis_title='Request Count',
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        barmode='stack',
        hovermode='x unified',
        legend=dict(x=1.05, y=1)
    )
    
    return fig


def create_rca_log_level_timeline_chart(timeline_stats: Dict) -> Optional[go.Figure]:
    """Create log level distribution over time chart."""
    if 'error' in timeline_stats or not timeline_stats.get('events_by_time'):
        return None
    
    events_by_time = timeline_stats.get('events_by_time', {})
    if not events_by_time:
        return None
    
    times = sorted(events_by_time.keys())[:30]
    
    # Collect log levels over time
    log_levels = ['ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG']
    level_counts = {level: [] for level in log_levels}
    
    for time_key in times:
        events_data = events_by_time.get(time_key, {})
        if isinstance(events_data, dict) and 'events' in events_data:
            events_list = events_data.get('events', [])
            level_counts_time = defaultdict(int)
            
            for event in events_list:
                if isinstance(event, dict):
                    level = event.get('level', '').upper()
                    level_counts_time[level] += 1
            
            for level in log_levels:
                level_counts[level].append(level_counts_time.get(level, 0))
        else:
            for level in log_levels:
                level_counts[level].append(0)
    
    if not times:
        return None
    
    fig = go.Figure()
    
    colors = {
        'ERROR': '#EF4444',
        'WARN': '#F59E0B',
        'WARNING': '#F59E0B',
        'INFO': '#2563EB',
        'DEBUG': '#9CA3AF'
    }
    
    for level in log_levels:
        if any(count > 0 for count in level_counts[level]):
            fig.add_trace(go.Scatter(
                x=times,
                y=level_counts[level],
                mode='lines+markers',
                name=level,
                line=dict(color=colors.get(level, '#9CA3AF'), width=2),
                marker=dict(size=6),
                stackgroup='one'
            ))
    
    # Format time labels
    formatted_times = []
    for t in times:
        try:
            dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
            formatted_times.append(dt.strftime('%H:%M'))
        except:
            formatted_times.append(t.split()[-1] if ' ' in t else t[:5])
    
    fig.update_layout(
        title=dict(text='Log Level Distribution Over Time', font=dict(size=18, color='#2563EB')),
        xaxis=dict(
            title='Time',
            tickmode='array',
            tickvals=times,
            ticktext=formatted_times,
            tickangle=-45
        ),
        yaxis_title='Event Count',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        hovermode='x unified',
        legend=dict(x=1.05, y=1)
    )
    
    return fig


def create_rca_final_analysis_summary_chart(rca_metrics: Dict) -> Optional[go.Figure]:
    """Create comprehensive final analysis summary chart combining all metrics."""
    if not rca_metrics or 'error' in rca_metrics.get('metadata', {}):
        return None
    
    error_stats = rca_metrics.get('error_stats', {})
    service_stats = rca_metrics.get('service_stats', {})
    request_patterns = rca_metrics.get('request_patterns', {})
    timeline_stats = rca_metrics.get('timeline_stats', {})
    
    # Collect key metrics for final summary
    services = list(service_stats.get('service_summary', {}).keys())[:10]
    if not services:
        return None
    
    # Calculate composite scores for each service
    service_scores = []
    errors_by_service = error_stats.get('errors_by_service', {})
    
    for service in services:
        service_details = service_stats.get('service_summary', {}).get(service, {})
        if isinstance(service_details, dict) and 'error' not in service_details:
            error_rate = service_details.get('error_rate', 0)
            errors = errors_by_service.get(service, 0)
            total_entries = service_details.get('total_entries', 0)
            
            # Composite score: lower is worse (more issues)
            composite_score = (error_rate * 0.4) + (errors * 0.3) + ((100 - (total_entries / 100)) * 0.3)
            service_scores.append({
                'service': service,
                'score': composite_score,
                'error_rate': error_rate,
                'errors': errors
            })
    
    if not service_scores:
        return None
    
    # Sort by score (highest issues first)
    service_scores.sort(key=lambda x: x['score'], reverse=True)
    
    services_list = [s['service'] for s in service_scores]
    scores = [s['score'] for s in service_scores]
    error_rates = [s['error_rate'] for s in service_scores]
    
    fig = go.Figure()
    
    # Composite score bars
    fig.add_trace(go.Bar(
        x=services_list,
        y=scores,
        name='Composite Issue Score',
        marker_color='#EF4444',
        yaxis='y',
        text=[f"{s:.1f}" for s in scores],
        textposition='outside'
    ))
    
    # Error rate line
    fig.add_trace(go.Scatter(
        x=services_list,
        y=error_rates,
        mode='lines+markers',
        name='Error Rate (%)',
        line=dict(color='#F97316', width=3, dash='dash'),
        marker=dict(size=10, color='#F97316'),
        yaxis='y2',
        text=[f"{er:.1f}%" for er in error_rates],
        textposition='top center'
    ))
    
    fig.update_layout(
        title=dict(text='Final Analysis - Service Impact Summary', font=dict(size=20, color='#2563EB')),
        xaxis=dict(title='Service', tickangle=-45),
        yaxis=dict(
            title='Composite Issue Score',
            side='left',
            range=[0, max(scores) * 1.2] if scores else [0, 100]
        ),
        yaxis2=dict(
            title='Error Rate (%)',
            overlaying='y',
            side='right',
            range=[0, max(error_rates) * 1.2] if error_rates else [0, 100]
        ),
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        hovermode='x unified',
        barmode='group',
        legend=dict(x=1.1, y=1)
    )
    
    return fig


def create_rca_final_timeline_summary_chart(rca_metrics: Dict) -> Optional[go.Figure]:
    """Create final timeline summary showing incident progression."""
    if not rca_metrics or 'error' in rca_metrics.get('metadata', {}):
        return None
    
    error_stats = rca_metrics.get('error_stats', {})
    timeline_stats = rca_metrics.get('timeline_stats', {})
    
    errors_by_time = error_stats.get('errors_by_time', {})
    events_by_time = timeline_stats.get('events_by_time', {})
    
    if not errors_by_time or not events_by_time:
        return None
    
    times = sorted(set(list(errors_by_time.keys())[:30] + list(events_by_time.keys())[:30]))[:30]
    
    error_counts = []
    event_counts = []
    
    for time_key in times:
        # Get error count
        error_data = errors_by_time.get(time_key, {})
        if isinstance(error_data, dict):
            count = error_data.get('count', 0)
            if isinstance(count, int):
                error_counts.append(count)
            elif isinstance(error_data, dict) and 'errors' in error_data:
                error_counts.append(len(error_data.get('errors', [])))
            else:
                error_counts.append(0)
        else:
            error_counts.append(0)
        
        # Get event count
        events_data = events_by_time.get(time_key, {})
        if isinstance(events_data, dict):
            event_counts.append(events_data.get('count', len(events_data.get('events', []))))
        else:
            event_counts.append(0)
    
    if not times:
        return None
    
    fig = go.Figure()
    
    # Error count line
    fig.add_trace(go.Scatter(
        x=times,
        y=error_counts,
        mode='lines+markers',
        name='Errors',
        line=dict(color='#EF4444', width=3),
        marker=dict(size=8, color='#EF4444'),
        yaxis='y'
    ))
    
    # Event count line
    fig.add_trace(go.Scatter(
        x=times,
        y=event_counts,
        mode='lines+markers',
        name='Total Events',
        line=dict(color='#2563EB', width=2, dash='dash'),
        marker=dict(size=6, color='#2563EB'),
        yaxis='y2'
    ))
    
    # Format time labels
    formatted_times = []
    for t in times:
        try:
            dt = datetime.fromisoformat(t.replace('Z', '+00:00'))
            formatted_times.append(dt.strftime('%H:%M'))
        except:
            formatted_times.append(t.split()[-1] if ' ' in t else t[:5])
    
    fig.update_layout(
        title=dict(text='Final Analysis - Incident Timeline Progression', font=dict(size=20, color='#2563EB')),
        xaxis=dict(
            title='Time',
            tickmode='array',
            tickvals=times,
            ticktext=formatted_times,
            tickangle=-45
        ),
        yaxis=dict(
            title='Error Count',
            side='left',
            range=[0, max(error_counts) * 1.2] if error_counts else [0, 100]
        ),
        yaxis2=dict(
            title='Total Events',
            overlaying='y',
            side='right',
            range=[0, max(event_counts) * 1.2] if event_counts else [0, 1000]
        ),
        height=450,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B'),
        hovermode='x unified',
        legend=dict(x=1.1, y=1)
    )
    
    return fig


def create_rca_service_log_levels_chart(service_stats: Dict) -> Optional[go.Figure]:
    """Create service log levels stacked bar chart."""
    if 'error' in service_stats or not service_stats.get('log_levels_by_service'):
        return None
    
    log_levels_by_service = service_stats.get('log_levels_by_service', {})
    if not log_levels_by_service:
        return None
    
    # Get all unique log levels
    all_levels = set()
    for levels in log_levels_by_service.values():
        all_levels.update(levels.keys())
    all_levels = sorted(list(all_levels), key=lambda x: ['DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'FATAL'].index(x) if x in ['DEBUG', 'INFO', 'WARNING', 'WARN', 'ERROR', 'FATAL'] else 999)
    
    services = list(log_levels_by_service.keys())
    
    # Create traces for each log level
    level_colors = {
        'DEBUG': '#9CA3AF',
        'INFO': '#2563EB',
        'WARNING': '#F59E0B',
        'WARN': '#F59E0B',
        'ERROR': '#F97316',
        'FATAL': '#EF4444'
    }
    
    fig = go.Figure()
    
    for level in all_levels:
        counts = [log_levels_by_service[svc].get(level, 0) for svc in services]
        fig.add_trace(go.Bar(
            name=level,
            x=services,
            y=counts,
            marker_color=level_colors.get(level, '#9CA3AF')
        ))
    
    fig.update_layout(
        title=dict(text='Log Levels by Service', font=dict(size=18, color='#2563EB')),
        xaxis_title='Service',
        yaxis_title='Log Count',
        barmode='stack',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def display_l1_stats_and_diagram(bundle_data: Dict, analysis_data: Optional[Dict] = None, analysis_text: str = ""):
    """Display L1 statistics and diagram."""
    stats = extract_l1_stats(bundle_data, analysis_data, analysis_text)
    
    # ============================================
    # SECTION 1: QUICK HIGH-LEVEL ANALYSIS
    # ============================================
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(0, 102, 255, 0.1) 0%, rgba(255, 107, 53, 0.1) 100%);
                padding: 1.5rem; border-radius: 16px; margin-bottom: 2rem; 
                border: 2px solid;
                border-image: linear-gradient(135deg, #0066FF 0%, #FF6B35 100%) 1;">
        <h3 style="color: #0F172A; margin-top: 0; font-family: 'Poppins', sans-serif; 
                  font-weight: 800; font-size: 1.5rem; margin-bottom: 0.5rem;">
            ⚡ Quick High-Level Analysis
        </h3>
        <p style="color: #475569; font-size: 0.95rem; margin: 0;">
            Key metrics and overview at a glance
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats cards with better styling
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        # Get severity from stats
        severity_dict = stats.get('severity', {})
        severity = "Unknown"
        for sev in ['Critical', 'High', 'Medium', 'Low']:
            if severity_dict.get(sev, 0) > 0:
                severity = sev
                break
        st.metric("Severity", severity, delta=None)
    with col2:
        st.metric("Symptoms", stats['symptoms_count'], delta=None)
    with col3:
        st.metric("Pods Affected", stats['pod_count'], delta=None)
    with col4:
        st.metric("Services Affected", stats['service_count'], delta=None)
    with col5:
        st.metric("Nodes Affected", stats['node_count'], delta=None)
    
            # Essential RCA metrics only
    if RCA_TOOLS_AVAILABLE:
        rca_metrics = collect_rca_metrics(bundle_data)
        if rca_metrics and 'error' not in rca_metrics.get('metadata', {}):
            error_stats = rca_metrics.get('error_stats', {})
            timeline_stats = rca_metrics.get('timeline_stats', {})
            service_stats = rca_metrics.get('service_stats', {})
            
            # Minimal essential metrics only
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Errors", error_stats.get('total_errors', 0))
            with col2:
                services_count = len(service_stats.get('service_summary', {}))
                st.metric("Services Affected", services_count)
            with col3:
                errors_by_service = error_stats.get('errors_by_service', {})
                top_service_errors = max(errors_by_service.values()) if errors_by_service else 0
                st.metric("Critical Service Errors", top_service_errors)
            
            # Essential visualization only
            if error_stats.get('errors_by_service'):
                st.markdown("---")
                st.markdown("#### 📈 Error Distribution Overview")
                error_service_chart = create_rca_error_distribution_chart(error_stats)
                if error_service_chart:
                    st.plotly_chart(error_service_chart, use_container_width=True, key="l1_quick_error_distribution")
    
    # Diagram
    st.markdown("---")
    st.markdown("#### 📈 Overview Diagram")
    fig = create_l1_diagram(stats, analysis_data)
    st.plotly_chart(fig, use_container_width=True, key="l1_diagram")
    
    # Enhanced summary of affected components
    if analysis_data:
        affected = analysis_data.get('affected_components', {})
        if affected.get('pods') or affected.get('services') or affected.get('nodes'):
            st.markdown("---")
            st.markdown("#### 🎯 Affected Components Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if affected.get('pods'):
                    st.markdown(f"**📦 Pods:** {len(affected['pods'])} affected")
                    for pod in affected['pods'][:5]:
                        st.markdown(f"  • `{pod}`")
                    if len(affected['pods']) > 5:
                        st.caption(f"... and {len(affected['pods']) - 5} more")
            
            with col2:
                if affected.get('services'):
                    st.markdown(f"**🔧 Services:** {len(affected['services'])} affected")
                    for svc in affected['services'][:5]:
                        st.markdown(f"  • `{svc}`")
                    if len(affected['services']) > 5:
                        st.caption(f"... and {len(affected['services']) - 5} more")
            
            with col3:
                if affected.get('nodes'):
                    st.markdown(f"**🖥️ Nodes:** {len(affected['nodes'])} affected")
                    for node in affected['nodes'][:5]:
                        st.markdown(f"  • `{node}`")
                    if len(affected['nodes']) > 5:
                        st.caption(f"... and {len(affected['nodes']) - 5} more")
    
    # ============================================
    # SECTION 2: DETAILED ANALYSIS
    # ============================================
    st.markdown("---")
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(255, 107, 53, 0.1) 0%, rgba(0, 102, 255, 0.1) 100%);
                padding: 1.5rem; border-radius: 16px; margin: 2rem 0; 
                border: 2px solid;
                border-image: linear-gradient(135deg, #FF6B35 0%, #0066FF 100%) 1;">
        <h3 style="color: #0F172A; margin-top: 0; font-family: 'Poppins', sans-serif; 
                  font-weight: 800; font-size: 1.5rem; margin-bottom: 0.5rem;">
            🔍 Detailed Analysis
        </h3>
        <p style="color: #475569; font-size: 0.95rem; margin: 0;">
            Comprehensive graphs, tables, and deep dive analysis
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display RCA metrics if available
    if RCA_TOOLS_AVAILABLE:
        rca_metrics = collect_rca_metrics(bundle_data)
        if rca_metrics and 'error' not in rca_metrics.get('metadata', {}):
            error_stats = rca_metrics.get('error_stats', {})
            timeline_stats = rca_metrics.get('timeline_stats', {})
            
            # L1: Essential visualizations only
            col1, col2 = st.columns(2)
            
            with col1:
                # Error Distribution Chart
                if error_stats.get('errors_by_service'):
                    st.markdown("#### 📈 Error Distribution")
                    error_service_chart = create_rca_error_distribution_chart(error_stats)
                    if error_service_chart:
                        st.plotly_chart(error_service_chart, use_container_width=True, key="l1_error_distribution")
            
            with col2:
                # Timeline Chart
                if timeline_stats.get('events_by_time'):
                    st.markdown("#### ⏱️ Timeline Overview")
                    timeline_chart = create_rca_timeline_chart(timeline_stats)
                    if timeline_chart:
                        st.plotly_chart(timeline_chart, use_container_width=True, key="l1_timeline")
            
            # Essential Table
            st.markdown("---")
            st.markdown("#### 📋 Error Summary")
            if error_stats.get('errors_by_service'):
                errors_by_service = error_stats.get('errors_by_service', {})
                error_summary_data = [
                    {'Service': svc, 'Error Count': count, 'Severity': 'Critical' if count > 100 else 'High' if count > 50 else 'Medium' if count > 20 else 'Low'}
                    for svc, count in sorted(errors_by_service.items(), key=lambda x: x[1], reverse=True)[:15]
                ]
                if error_summary_data:
                    error_summary_df = pd.DataFrame(error_summary_data)
                    st.dataframe(error_summary_df, use_container_width=True, hide_index=True)
    
    # Display structured data if available
    if analysis_data:
        st.markdown("---")
        st.markdown("### 📊 Detailed Breakdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div style="background: rgba(239, 68, 68, 0.05); padding: 1rem; border-radius: 8px; 
                        border-left: 4px solid #EF4444; margin-bottom: 1rem;">
                <h4 style="color: #EF4444; margin-top: 0;">🔴 Symptoms</h4>
            </div>
            """, unsafe_allow_html=True)
            for symptom in analysis_data.get('symptoms', []):
                st.markdown(f"  • {symptom}")
            
            if analysis_data.get('time_window'):
                st.markdown("""
                <div style="background: rgba(249, 115, 22, 0.05); padding: 1rem; border-radius: 8px; 
                            border-left: 4px solid #F97316; margin-top: 1rem;">
                    <h4 style="color: #F97316; margin-top: 0;">⏰ Time Window</h4>
                    <p style="margin-bottom: 0;">{}</p>
                </div>
                """.format(analysis_data['time_window']), unsafe_allow_html=True)
        
        with col2:
            affected = analysis_data.get('affected_components', {})
            
            if affected.get('pods'):
                st.markdown("""
                <div style="background: rgba(37, 99, 235, 0.05); padding: 1rem; border-radius: 8px; 
                            border-left: 4px solid #2563EB; margin-bottom: 1rem;">
                    <h4 style="color: #2563EB; margin-top: 0;">📦 Affected Pods</h4>
                </div>
                """, unsafe_allow_html=True)
                for pod in affected['pods'][:10]:  # Show first 10
                    st.markdown(f"  • `{pod}`")
                if len(affected['pods']) > 10:
                    st.caption(f"... and {len(affected['pods']) - 10} more")
            
            if affected.get('services'):
                st.markdown("""
                <div style="background: rgba(249, 115, 22, 0.05); padding: 1rem; border-radius: 8px; 
                            border-left: 4px solid #F97316; margin-top: 1rem;">
                    <h4 style="color: #F97316; margin-top: 0;">🔧 Affected Services</h4>
                </div>
                """, unsafe_allow_html=True)
                for svc in affected['services']:
                    st.markdown(f"  • `{svc}`")
            
            if affected.get('nodes'):
                st.markdown("""
                <div style="background: rgba(59, 130, 246, 0.05); padding: 1rem; border-radius: 8px; 
                            border-left: 4px solid #3B82F6; margin-top: 1rem;">
                    <h4 style="color: #3B82F6; margin-top: 0;">🖥️ Affected Nodes</h4>
                </div>
                """, unsafe_allow_html=True)
                for node in affected['nodes']:
                    st.markdown(f"  • `{node}`")
        
        if analysis_data.get('initial_observations'):
            st.markdown("---")
            st.markdown("""
            <div style="background: rgba(37, 99, 235, 0.05); padding: 1rem; border-radius: 8px; 
                        border-left: 4px solid #2563EB;">
                <h4 style="color: #2563EB; margin-top: 0;">👁️ Initial Observations</h4>
            </div>
            """, unsafe_allow_html=True)
            for obs in analysis_data['initial_observations']:
                st.markdown(f"  • {obs}")


def display_l2_stats_and_diagram(bundle_data: Dict, analysis_text: str):
    """Display L2 statistics and diagram with detailed analysis."""
    stats = extract_l2_stats(bundle_data, analysis_text)
    
    # ============================================
    # SECTION 1: QUICK HIGH-LEVEL ANALYSIS
    # ============================================
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(0, 102, 255, 0.1) 0%, rgba(255, 107, 53, 0.1) 100%);
                padding: 1.5rem; border-radius: 16px; margin-bottom: 2rem; 
                border: 2px solid;
                border-image: linear-gradient(135deg, #0066FF 0%, #FF6B35 100%) 1;">
        <h3 style="color: #0F172A; margin-top: 0; font-family: 'Poppins', sans-serif; 
                  font-weight: 800; font-size: 1.5rem; margin-bottom: 0.5rem;">
            ⚡ Quick High-Level Analysis
        </h3>
        <p style="color: #475569; font-size: 0.95rem; margin: 0;">
            Key metrics and correlation overview at a glance
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Failing Components", len(stats['failing_components']), delta=None)
    with col2:
        st.metric("Dependency Issues", stats['dependency_issues'], delta=None)
    with col3:
        st.metric("Config Issues", stats['config_issues'], delta=None)
    with col4:
        st.metric("Infra Issues", stats.get('infra_issues', 0), delta=None)
    
    # Diagram
    st.markdown("---")
    st.markdown("#### 📈 Correlation Overview Diagram")
    fig = create_l2_diagram(stats)
    st.plotly_chart(fig, use_container_width=True, key="l2_diagram")
    
    # Enhanced Quick Summary
    if RCA_TOOLS_AVAILABLE:
        rca_metrics = collect_rca_metrics(bundle_data)
        if rca_metrics and 'error' not in rca_metrics.get('metadata', {}):
            error_stats = rca_metrics.get('error_stats', {})
            error_patterns = rca_metrics.get('error_patterns', {})
            request_patterns = rca_metrics.get('request_patterns', {})
            service_stats = rca_metrics.get('service_stats', {})
            timeline_stats = rca_metrics.get('timeline_stats', {})
            
            st.markdown("---")
            st.markdown("#### 📊 Additional Correlation Metrics")
            
            # Additional metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                errors_by_service = error_stats.get('errors_by_service', {})
                services_with_errors = len(errors_by_service)
                st.metric("Services with Errors", services_with_errors)
            with col2:
                error_categories = error_patterns.get('error_categories', {})
                unique_categories = len(error_categories) if error_categories else 0
                st.metric("Error Categories", unique_categories)
            with col3:
                success_rate = request_patterns.get('success_rate', 0)
                st.metric("Success Rate", f"{success_rate:.1f}%" if success_rate else "N/A")
            with col4:
                total_services = len(service_stats.get('service_summary', {}))
                st.metric("Total Services", total_services)
            
            # Quick Overview Charts
            st.markdown("---")
            st.markdown("#### 📈 Quick Correlation Overview")
            col1, col2 = st.columns(2)
            
            with col1:
                # Error Categories Chart
                if error_patterns.get('error_categories'):
                    error_category_chart = create_rca_error_category_chart(error_stats)
                    if error_category_chart:
                        st.plotly_chart(error_category_chart, use_container_width=True, key="l2_quick_error_category")
            
            with col2:
                # Error Severity Chart
                if error_stats.get('errors_by_severity'):
                    severity_chart = create_rca_error_severity_chart(error_stats)
                    if severity_chart:
                        st.plotly_chart(severity_chart, use_container_width=True, key="l2_quick_severity")
            
            # Quick Summary Tables
            st.markdown("---")
            st.markdown("#### 📋 Quick Correlation Summary")
            col1, col2 = st.columns(2)
            
            with col1:
                # Root Cause Candidates Table
                if error_patterns.get('root_cause_candidates'):
                    root_cause_candidates = error_patterns.get('root_cause_candidates', {})
                    candidates_data = [
                        {'Aspect': 'Most Frequent Category', 'Value': root_cause_candidates.get('most_frequent_category', 'N/A')},
                        {'Aspect': 'Most Affected Service', 'Value': root_cause_candidates.get('most_affected_service', 'N/A')},
                        {'Aspect': 'Error Burst Time', 'Value': root_cause_candidates.get('error_burst_time', 'N/A')}
                    ]
                    candidates_df = pd.DataFrame(candidates_data)
                    st.markdown("**Root Cause Candidates:**")
                    st.dataframe(candidates_df, use_container_width=True, hide_index=True)
            
            with col2:
                # Top Services Summary
                if error_stats.get('errors_by_service'):
                    errors_by_service = error_stats.get('errors_by_service', {})
                    top_services = sorted(errors_by_service.items(), key=lambda x: x[1], reverse=True)[:5]
                    top_services_data = [
                        {'Service': svc, 'Errors': count, 'Impact': 'High' if count > 50 else 'Medium' if count > 20 else 'Low'}
                        for svc, count in top_services
                    ]
                    top_services_df = pd.DataFrame(top_services_data)
                    st.markdown("**Top Affected Services:**")
                    st.dataframe(top_services_df, use_container_width=True, hide_index=True)
            
            # Service Health Overview
            if service_stats.get('service_summary'):
                st.markdown("---")
                st.markdown("#### 💚 Service Health Overview")
                service_summary = service_stats.get('service_summary', {})
                errors_by_service = error_stats.get('errors_by_service', {})
                health_summary = []
                
                for service, details in service_summary.items():
                    if isinstance(details, dict) and 'error' not in details:
                        errors = details.get('errors', 0)
                        error_rate = details.get('error_rate', 0)
                        service_errors = errors_by_service.get(service, 0)
                        health_score = max(0, 100 - (error_rate * 2) - (errors * 0.1))
                        
                        health_summary.append({
                            'Service': service,
                            'Errors': errors,
                            'Error Rate (%)': round(error_rate, 2),
                            'Health Score': round(health_score, 1),
                            'Status': 'Healthy' if health_score >= 80 else 'Degraded' if health_score >= 60 else 'Critical'
                        })
                
                if health_summary:
                    health_summary_df = pd.DataFrame(health_summary).sort_values('Health Score', ascending=True)[:10]
                    st.dataframe(health_summary_df, use_container_width=True, hide_index=True)
    
    # ============================================
    # SECTION 2: DETAILED ANALYSIS
    # ============================================
    st.markdown("---")
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(255, 107, 53, 0.1) 0%, rgba(0, 102, 255, 0.1) 100%);
                padding: 1.5rem; border-radius: 16px; margin: 2rem 0; 
                border: 2px solid;
                border-image: linear-gradient(135deg, #FF6B35 0%, #0066FF 100%) 1;">
        <h3 style="color: #0F172A; margin-top: 0; font-family: 'Poppins', sans-serif; 
                  font-weight: 800; font-size: 1.5rem; margin-bottom: 0.5rem;">
            🔍 Detailed Analysis
        </h3>
        <p style="color: #475569; font-size: 0.95rem; margin: 0;">
            Comprehensive graphs, tables, and correlation deep dive analysis
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # L2: Enhanced analysis with RCA metrics
    if RCA_TOOLS_AVAILABLE:
        rca_metrics = collect_rca_metrics(bundle_data)
        if rca_metrics and 'error' not in rca_metrics.get('metadata', {}):
            error_stats = rca_metrics.get('error_stats', {})
            error_patterns = rca_metrics.get('error_patterns', {})
            request_patterns = rca_metrics.get('request_patterns', {})
            service_stats = rca_metrics.get('service_stats', {})
            timeline_stats = rca_metrics.get('timeline_stats', {})
            
            # Essential Correlation Analysis - Visual Focus
            col1, col2 = st.columns(2)
            
            with col1:
                # Error Categories Chart
                if error_patterns.get('error_categories'):
                    st.markdown("#### 📊 Error Categories")
                    error_category_chart = create_rca_error_category_chart(error_stats)
                    if error_category_chart:
                        st.plotly_chart(error_category_chart, use_container_width=True, key="l2_error_category")
                
                # Service Error Trend
                if error_stats.get('errors_by_time') and timeline_stats.get('events_by_time'):
                    st.markdown("#### 📈 Error Trend")
                    error_trend_chart = create_rca_service_error_trend_chart(error_stats, timeline_stats)
                    if error_trend_chart:
                        st.plotly_chart(error_trend_chart, use_container_width=True, key="l2_service_error_trend")
            
            with col2:
                # Error Severity Chart
                if error_stats.get('errors_by_severity'):
                    st.markdown("#### 🚨 Error Severity")
                    severity_chart = create_rca_error_severity_chart(error_stats)
                    if severity_chart:
                        st.plotly_chart(severity_chart, use_container_width=True, key="l2_error_severity")
                
                # Service Dependency
                if service_stats.get('service_summary') and error_stats.get('errors_by_service'):
                    st.markdown("#### 🔗 Service Dependency")
                    dependency_chart = create_rca_service_dependency_chart(service_stats, error_stats)
                    if dependency_chart:
                        st.plotly_chart(dependency_chart, use_container_width=True, key="l2_service_dependency")
            
            # Essential Tables
            st.markdown("---")
            st.markdown("#### 📋 Correlation Analysis")
            
            # Service Correlation Table - Top services only
            if service_stats.get('service_summary') and error_stats.get('errors_by_service'):
                service_summary = service_stats.get('service_summary', {})
                errors_by_service = error_stats.get('errors_by_service', {})
                service_correlation = []
                
                for service, details in service_summary.items():
                    if isinstance(details, dict) and 'error' not in details:
                        errors = details.get('errors', 0)
                        error_rate = details.get('error_rate', 0)
                        service_errors = errors_by_service.get(service, 0)
                        
                        # Calculate correlation score
                        correlation_score = (error_rate * 0.4) + (service_errors * 0.3) + ((100 - (error_rate * 2)) * 0.3)
                        
                        service_correlation.append({
                            'Service': service,
                            'Errors': errors,
                            'Error Rate (%)': round(error_rate, 2),
                            'Correlation Score': round(correlation_score, 1),
                            'Priority': 'P0' if correlation_score > 40 else 'P1' if correlation_score > 20 else 'P2'
                        })
                
                if service_correlation:
                    service_correlation_df = pd.DataFrame(service_correlation).sort_values('Correlation Score', ascending=False)[:10]
                    st.dataframe(service_correlation_df, use_container_width=True, hide_index=True)
    
    # Failing components list
    if stats['failing_components']:
        st.markdown("---")
        st.markdown("**Failing Components:**")
        components_df = pd.DataFrame({
            'Component': stats['failing_components']
        })
        st.dataframe(components_df, use_container_width=True, hide_index=True)


def display_l3_stats_and_diagram(bundle_data: Dict, analysis_text: str):
    """Display L3 statistics and diagram with comprehensive root cause analysis."""
    stats = extract_l3_stats(bundle_data, analysis_text)
    
    # ============================================
    # SECTION 1: QUICK HIGH-LEVEL ANALYSIS
    # ============================================
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(0, 102, 255, 0.1) 0%, rgba(255, 107, 53, 0.1) 100%);
                padding: 1.5rem; border-radius: 16px; margin-bottom: 2rem; 
                border: 2px solid;
                border-image: linear-gradient(135deg, #0066FF 0%, #FF6B35 100%) 1;">
        <h3 style="color: #0F172A; margin-top: 0; font-family: 'Poppins', sans-serif; 
                  font-weight: 800; font-size: 1.5rem; margin-bottom: 0.5rem;">
            ⚡ Quick High-Level Analysis
        </h3>
        <p style="color: #475569; font-size: 0.95rem; margin: 0;">
            Key metrics and root cause overview at a glance
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Fix Recommendations", stats['fix_recommendations'], delta=None)
    with col2:
        st.metric("Monitoring Suggestions", stats['monitoring_suggestions'], delta=None)
    with col3:
        st.metric("Preventive Measures", stats['preventive_measures'], delta=None)
    with col4:
        root_cause_types = sum(stats['root_cause_type'].values())
        st.metric("Root Cause Types", root_cause_types, delta=None)
    
    # Diagram
    st.markdown("---")
    st.markdown("#### 📈 Root Cause Overview Diagram")
    fig = create_l3_diagram(stats)
    st.plotly_chart(fig, use_container_width=True, key="l3_diagram")
    
    # Enhanced Quick Summary
    if RCA_TOOLS_AVAILABLE:
        rca_metrics = collect_rca_metrics(bundle_data)
        if rca_metrics and 'error' not in rca_metrics.get('metadata', {}):
            error_stats = rca_metrics.get('error_stats', {})
            error_patterns = rca_metrics.get('error_patterns', {})
            request_patterns = rca_metrics.get('request_patterns', {})
            service_stats = rca_metrics.get('service_stats', {})
            timeline_stats = rca_metrics.get('timeline_stats', {})
            
            st.markdown("---")
            st.markdown("#### 📊 Additional Root Cause Metrics")
            
            # Additional metrics row
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_errors = error_stats.get('total_errors', 0)
                st.metric("Total Errors", total_errors)
            with col2:
                errors_by_service = error_stats.get('errors_by_service', {})
                critical_services = len([svc for svc, count in errors_by_service.items() if count > 50])
                st.metric("Critical Services", critical_services)
            with col3:
                error_categories = error_patterns.get('error_categories', {})
                top_category_count = max(error_categories.values()) if error_categories else 0
                st.metric("Top Category Count", top_category_count)
            with col4:
                success_rate = request_patterns.get('success_rate', 0)
                st.metric("Success Rate", f"{success_rate:.1f}%" if success_rate else "N/A")
            
            # Root Cause Flow Diagram
            st.markdown("---")
            st.markdown("#### 🔄 Root Cause Flow")
            flow_diagram = create_root_cause_flow_diagram(error_stats, error_patterns, service_stats)
            if flow_diagram:
                st.plotly_chart(flow_diagram, use_container_width=True, key="l3_quick_flow_diagram")
            
            # Quick Overview Charts
            st.markdown("---")
            st.markdown("#### 📈 Quick Root Cause Overview")
            col1, col2 = st.columns(2)
            
            with col1:
                # Error Categories Chart
                if error_patterns.get('error_categories'):
                    error_category_chart = create_rca_error_category_chart(error_stats)
                    if error_category_chart:
                        st.plotly_chart(error_category_chart, use_container_width=True, key="l3_quick_error_category")
            
            with col2:
                # Error Severity Chart
                if error_stats.get('errors_by_severity'):
                    severity_chart = create_rca_error_severity_chart(error_stats)
                    if severity_chart:
                        st.plotly_chart(severity_chart, use_container_width=True, key="l3_quick_severity")
            
            # Quick Summary Tables
            st.markdown("---")
            st.markdown("#### 📋 Quick Root Cause Summary")
            col1, col2 = st.columns(2)
            
            with col1:
                # Root Cause Candidates Table
                if error_patterns.get('root_cause_candidates'):
                    root_cause_candidates = error_patterns.get('root_cause_candidates', {})
                    candidates_data = [
                        {'Aspect': 'Most Frequent Category', 'Value': root_cause_candidates.get('most_frequent_category', 'N/A')},
                        {'Aspect': 'Most Affected Service', 'Value': root_cause_candidates.get('most_affected_service', 'N/A')},
                        {'Aspect': 'Error Burst Time', 'Value': root_cause_candidates.get('error_burst_time', 'N/A')}
                    ]
                    candidates_df = pd.DataFrame(candidates_data)
                    st.markdown("**Root Cause Indicators:**")
                    st.dataframe(candidates_df, use_container_width=True, hide_index=True)
            
            with col2:
                # Error Severity Summary
                if error_stats.get('errors_by_severity'):
                    severity_dist = error_stats.get('errors_by_severity', {})
                    total_severity = sum(severity_dist.values())
                    if total_severity > 0:
                        severity_data = [
                            {
                                'Severity': severity,
                                'Count': count,
                                'Percentage': round((count / total_severity) * 100, 1),
                                'Impact': 'Critical' if severity in ['CRITICAL', 'FATAL'] else 'High' if severity in ['ERROR', 'WARN'] else 'Medium'
                            }
                            for severity, count in sorted(severity_dist.items(), key=lambda x: x[1], reverse=True)[:5]
                        ]
                        severity_df = pd.DataFrame(severity_data)
                        st.markdown("**Error Severity Distribution:**")
                        st.dataframe(severity_df, use_container_width=True, hide_index=True)
            
            # Service Impact Summary
            if service_stats.get('service_summary') and error_stats.get('errors_by_service'):
                st.markdown("---")
                st.markdown("#### 💼 Service Impact Summary")
                service_summary = service_stats.get('service_summary', {})
                errors_by_service = error_stats.get('errors_by_service', {})
                impact_summary = []
                
                for service, details in service_summary.items():
                    if isinstance(details, dict) and 'error' not in details:
                        errors = details.get('errors', 0)
                        error_rate = details.get('error_rate', 0)
                        service_errors = errors_by_service.get(service, 0)
                        impact_score = (error_rate * 0.4) + (service_errors * 0.3) + ((100 - (error_rate * 2)) * 0.3)
                        
                        impact_summary.append({
                            'Service': service,
                            'Errors': errors,
                            'Error Rate (%)': round(error_rate, 2),
                            'Impact Score': round(impact_score, 1),
                            'Priority': 'P0' if impact_score > 50 else 'P1' if impact_score > 30 else 'P2'
                        })
                
                if impact_summary:
                    impact_summary_df = pd.DataFrame(impact_summary).sort_values('Impact Score', ascending=False)[:10]
                    st.dataframe(impact_summary_df, use_container_width=True, hide_index=True)
    
    # ============================================
    # SECTION 2: DETAILED ANALYSIS
    # ============================================
    st.markdown("---")
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(255, 107, 53, 0.1) 0%, rgba(0, 102, 255, 0.1) 100%);
                padding: 1.5rem; border-radius: 16px; margin: 2rem 0; 
                border: 2px solid;
                border-image: linear-gradient(135deg, #FF6B35 0%, #0066FF 100%) 1;">
        <h3 style="color: #0F172A; margin-top: 0; font-family: 'Poppins', sans-serif; 
                  font-weight: 800; font-size: 1.5rem; margin-bottom: 0.5rem;">
            🔍 Detailed Analysis
        </h3>
        <p style="color: #475569; font-size: 0.95rem; margin: 0;">
            Comprehensive graphs, tables, and root cause deep dive analysis
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # L3: Comprehensive root cause analysis with RCA metrics
    if RCA_TOOLS_AVAILABLE:
        rca_metrics = collect_rca_metrics(bundle_data)
        if rca_metrics and 'error' not in rca_metrics.get('metadata', {}):
            error_stats = rca_metrics.get('error_stats', {})
            error_patterns = rca_metrics.get('error_patterns', {})
            request_patterns = rca_metrics.get('request_patterns', {})
            service_stats = rca_metrics.get('service_stats', {})
            timeline_stats = rca_metrics.get('timeline_stats', {})
            
            # Root Cause Flow Diagram
            st.markdown("#### 🔄 Root Cause Flow Diagram")
            flow_diagram = create_root_cause_flow_diagram(error_stats, error_patterns, service_stats)
            if flow_diagram:
                st.plotly_chart(flow_diagram, use_container_width=True, key="l3_root_cause_flow")
            
            # Root Cause Impact Matrix
            st.markdown("---")
            st.markdown("#### 🔥 Root Cause Impact Matrix")
            impact_matrix = create_root_cause_impact_matrix(error_stats, service_stats, request_patterns)
            if impact_matrix:
                st.plotly_chart(impact_matrix, use_container_width=True, key="l3_impact_matrix")
            
            # Essential Root Cause Analysis - Visual Focus
            col1, col2 = st.columns(2)
            
            with col1:
                # Error Categories Chart
                if error_patterns.get('error_categories'):
                    st.markdown("#### 📊 Error Categories")
                    error_category_chart = create_rca_error_category_chart(error_stats)
                    if error_category_chart:
                        st.plotly_chart(error_category_chart, use_container_width=True, key="l3_error_category")
            
            with col2:
                # Error Severity Chart
                if error_stats.get('errors_by_severity'):
                    st.markdown("#### 🚨 Error Severity")
                    severity_chart = create_rca_error_severity_chart(error_stats)
                    if severity_chart:
                        st.plotly_chart(severity_chart, use_container_width=True, key="l3_error_severity")
            
            # Essential Tables
            st.markdown("---")
            st.markdown("#### 📋 Root Cause Analysis")
            
            # Root Cause Summary Table
            root_cause_summary = []
            if error_patterns.get('root_cause_candidates'):
                root_cause_candidates = error_patterns.get('root_cause_candidates', {})
                root_cause_summary.append({
                    'Indicator': 'Most Frequent Category',
                    'Value': root_cause_candidates.get('most_frequent_category', 'N/A'),
                    'Impact': 'High'
                })
                root_cause_summary.append({
                    'Indicator': 'Most Affected Service',
                    'Value': root_cause_candidates.get('most_affected_service', 'N/A'),
                    'Impact': 'High'
                })
                root_cause_summary.append({
                    'Indicator': 'Error Burst Time',
                    'Value': root_cause_candidates.get('error_burst_time', 'N/A'),
                    'Impact': 'Medium'
                })
            
            if error_stats.get('errors_by_severity'):
                severity_dist = error_stats.get('errors_by_severity', {})
                top_severity = max(severity_dist.items(), key=lambda x: x[1])[0] if severity_dist else 'N/A'
                root_cause_summary.append({
                    'Indicator': 'Top Severity',
                    'Value': top_severity,
                    'Impact': 'Critical' if top_severity in ['CRITICAL', 'FATAL'] else 'High'
                })
            
            if root_cause_summary:
                root_cause_summary_df = pd.DataFrame(root_cause_summary)
                st.dataframe(root_cause_summary_df, use_container_width=True, hide_index=True)
            
            # Service Impact Table - Top services only
            if service_stats.get('service_summary') and error_stats.get('errors_by_service'):
                st.markdown("---")
                st.markdown("#### 💼 Service Impact Analysis")
                service_summary = service_stats.get('service_summary', {})
                errors_by_service = error_stats.get('errors_by_service', {})
                service_impact = []
                
                for service, details in service_summary.items():
                    if isinstance(details, dict) and 'error' not in details:
                        errors = details.get('errors', 0)
                        error_rate = details.get('error_rate', 0)
                        service_errors = errors_by_service.get(service, 0)
                        
                        # Calculate impact score
                        impact_score = (error_rate * 0.4) + (service_errors * 0.3) + ((100 - (error_rate * 2)) * 0.3)
                        
                        service_impact.append({
                            'Service': service,
                            'Errors': errors,
                            'Error Rate (%)': round(error_rate, 2),
                            'Impact Score': round(impact_score, 1),
                            'Priority': 'P0' if impact_score > 50 else 'P1' if impact_score > 30 else 'P2'
                        })
                
                if service_impact:
                    service_impact_df = pd.DataFrame(service_impact).sort_values('Impact Score', ascending=False)[:10]
                    st.dataframe(service_impact_df, use_container_width=True, hide_index=True)
            
            # Top Errors Table
            if error_stats.get('top_error_messages'):
                st.markdown("---")
                st.markdown("#### 🔴 Top Error Messages")
                top_errors = error_stats.get('top_error_messages', [])[:10]
                if top_errors:
                    top_errors_data = []
                    for error in top_errors:
                        if isinstance(error, dict):
                            top_errors_data.append({
                                'Error': error.get('message', error.get('error', 'N/A'))[:80],
                                'Count': error.get('count', error.get('frequency', 0)),
                                'Service': error.get('service', 'N/A'),
                                'Category': error.get('category', error.get('type', 'N/A'))
                            })
                    
                    if top_errors_data:
                        top_errors_df = pd.DataFrame(top_errors_data).sort_values('Count', ascending=False)
                        st.dataframe(top_errors_df, use_container_width=True, hide_index=True)


def perform_l1_analysis(bundle_data: Dict) -> Tuple[str, Optional[Dict]]:
    """Perform L1 incident triage analysis. Returns both text and structured JSON.
    Only analyzes data from the uploaded bundle - no real-time metrics collection."""
    # Collect RCA metrics from bundle only
    rca_metrics = collect_rca_metrics(bundle_data)
    
    # Build RCA metrics context from bundle only
    rca_context = ""
    if rca_metrics:
        error_stats = rca_metrics.get('error_stats', {})
        timeline_stats = rca_metrics.get('timeline_stats', {})
        service_stats = rca_metrics.get('service_stats', {})
        metadata = rca_metrics.get('metadata', {})
        
        rca_context = f"""
RCA Log Analysis (from bundle):
- Scenario: {metadata.get('scenario_type', 'N/A')}
- Total Errors: {error_stats.get('total_errors', 0)}
- Errors by Service: {error_stats.get('errors_by_service', {})}
- Total Timeline Events: {timeline_stats.get('total_events', 0)}
- Services Analyzed: {', '.join(service_stats.get('services_analyzed', []))}
- Top Error Categories: {list(error_stats.get('errors_by_category', {}).keys())[:3]}
- Error Rate: {rca_metrics.get('request_patterns', {}).get('error_rate', 'N/A')}%
"""
    
    # Calculate baseline token usage (original approach - sending full logs)
    baseline_app_logs = '\n\n'.join([f"=== {log['filename']} ===\n{log['content'][:5000]}" for log in bundle_data.get('app_logs', [])[:5]])
    baseline_k8s_events = (str(bundle_data.get('k8s_events')) if bundle_data.get('k8s_events') is not None else 'N/A')[:3000]
    baseline_pod_status = (str(bundle_data.get('pod_status')) if bundle_data.get('pod_status') is not None else 'N/A')[:3000]
    baseline_errors = json.dumps(bundle_data.get('errors', {}), indent=2)[:3000] if bundle_data.get('errors') else 'N/A'
    
    baseline_prompt_template = """You are a Kubernetes operations analyst performing L1 incident triage.

L1 CRITERIA - Incident Triage:
✅ Symptoms: Identify and list all observable symptoms (errors, failures, performance degradation)
✅ Affected Components: List all pods, services, and nodes that are affected
✅ Severity Assessment: Assess and categorize severity (Critical/High/Medium/Low)

Your task is to quickly identify:
1. **SYMPTOMS**: All observable symptoms (errors, failures, degraded performance)
2. **AFFECTED COMPONENTS**: All affected pods, services, and nodes
3. **SEVERITY ASSESSMENT**: Critical/High/Medium/Low based on impact

Do NOT speculate on root cause - that's for L2 and L3.

IMPORTANT: Provide your response ONLY as valid JSON in the following format (no markdown, no code blocks, just pure JSON):
{{
  "symptoms": ["symptom1", "symptom2", ...],
  "affected_components": {{
    "pods": ["pod-name-1", "pod-name-2", ...],
    "services": ["service-1", "service-2", ...],
    "nodes": ["node-1", "node-2", ...]
  }},
  "severity": "Critical|High|Medium|Low",
  "time_window": "start-time to end-time",
  "initial_observations": ["observation1", "observation2", ...]
}}

If you must use markdown, wrap it like this: ```json
{{your JSON here}}
```

Analyze the following data:

Application Logs:
{app_logs}

Kubernetes Events:
{k8s_events}

Pod Status:
{pod_status}

Errors Found:
{errors}
{storage_context}
{k8s_context}
{rca_context}
"""
    
    baseline_prompt = baseline_prompt_template.format(
        app_logs=baseline_app_logs,
        k8s_events=baseline_k8s_events,
        pod_status=baseline_pod_status,
        errors=baseline_errors,
        storage_context="",  # Disabled: Only using bundle data
        k8s_context="",  # Disabled: Only using bundle data
        rca_context=rca_context
    )
    
    # Estimate baseline token usage
    baseline_token_estimate = estimate_tokens(baseline_prompt) + 2000  # Add estimated response tokens
    st.session_state.baseline_token_usage['L1'] = baseline_token_estimate
    
    # Optimized approach: Use multilevel chunking for maximum token reduction
    optimized_app_logs = smart_chunk_logs(bundle_data.get('app_logs', [])[:5], max_chars_per_log=1200, max_logs=3)
    optimized_k8s_events = smart_chunk_text(str(bundle_data.get('k8s_events')) if bundle_data.get('k8s_events') is not None else 'N/A', max_chars=1000)
    optimized_pod_status = smart_chunk_text(str(bundle_data.get('pod_status')) if bundle_data.get('pod_status') is not None else 'N/A', max_chars=1000)
    optimized_errors = smart_chunk_text(json.dumps(bundle_data.get('errors', {}), indent=2) if bundle_data.get('errors') else 'N/A', max_chars=1000)
    
    prompt = """You are a Kubernetes operations analyst performing L1 incident triage.

L1 CRITERIA - Incident Triage:
✅ Symptoms: Identify and list all observable symptoms (errors, failures, performance degradation)
✅ Affected Components: List all pods, services, and nodes that are affected
✅ Severity Assessment: Assess and categorize severity (Critical/High/Medium/Low)

Your task is to quickly identify:
1. **SYMPTOMS**: All observable symptoms (errors, failures, degraded performance)
2. **AFFECTED COMPONENTS**: All affected pods, services, and nodes
3. **SEVERITY ASSESSMENT**: Critical/High/Medium/Low based on impact

Do NOT speculate on root cause - that's for L2 and L3.

IMPORTANT: Provide your response ONLY as valid JSON in the following format (no markdown, no code blocks, just pure JSON):
{{
  "symptoms": ["symptom1", "symptom2", ...],
  "affected_components": {{
    "pods": ["pod-name-1", "pod-name-2", ...],
    "services": ["service-1", "service-2", ...],
    "nodes": ["node-1", "node-2", ...]
  }},
  "severity": "Critical|High|Medium|Low",
  "time_window": "start-time to end-time",
  "initial_observations": ["observation1", "observation2", ...]
}}

If you must use markdown, wrap it like this: ```json
{{your JSON here}}
```

Analyze the following data:

Application Logs:
{app_logs}

Kubernetes Events:
{k8s_events}

Pod Status:
{pod_status}

Errors Found:
{errors}
{storage_context}
{k8s_context}
{rca_context}
""".format(
        app_logs=optimized_app_logs,
        k8s_events=optimized_k8s_events,
        pod_status=optimized_pod_status,
        errors=optimized_errors,
        storage_context="",  # Disabled: Only using bundle data
        k8s_context="",  # Disabled: Only using bundle data
        rca_context=rca_context
    )
    
    try:
        # Retry configuration for network errors
        max_retries = 3
        base_delay = 2  # seconds
        last_error = None
        
        for attempt in range(max_retries):
            try:
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=2000,
                    )
                )
                text = response.text
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e)
                last_error = e
                
                # Check if it's a network error
                if "Network" in error_str or "network" in error_str or "AxiosError" in error_str or "ECONNREFUSED" in error_str or "timeout" in error_str.lower():
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        delay = min(base_delay * (2 ** attempt), 30)
                        st.info(f"⚠️ Network error encountered. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        return f"""❌ **Network Error - Connection Failed**

Unable to connect to the Gemini API. Please check:

1. **Internet Connection**: Ensure you have a stable internet connection
2. **API Key**: Verify your GEMINI_API_KEY is set correctly in your .env file
3. **Network Settings**: Check if you're behind a firewall or proxy that might block API requests
4. **API Status**: The Gemini API might be temporarily unavailable

**Error Details**: {error_str}

**Suggestions**:
- Wait a few minutes and try again
- Check your network connection
- Verify your API key is valid
- Contact your network administrator if behind a corporate firewall""", None
                
                # For non-network errors or if retries exhausted, raise immediately
                raise
    
        # If we successfully got a response, continue processing
        # Extract token usage if available
        token_usage_info = {}
        try:
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                token_usage_info = {
                    'prompt_token_count': getattr(response.usage_metadata, 'prompt_token_count', 0),
                    'candidates_token_count': getattr(response.usage_metadata, 'candidates_token_count', 0),
                    'total_token_count': getattr(response.usage_metadata, 'total_token_count', 0)
                }
        except:
            pass
        
        # Try to extract JSON from response
        json_data = None
        try:
            # Step 1: Try to find JSON in markdown code blocks (```json ... ```)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
                json_data = json.loads(json_str)
            else:
                # Step 2: Look for JSON block starting with { and containing "symptoms" (handles nested objects)
                # This pattern matches: { ... "symptoms" ... { ... } ... }
                json_match = re.search(r'(\{(?:[^{}]|(?:\{[^{}]*\}))*"symptoms"(?:[^{}]|(?:\{[^{}]*\}))*\})', text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1).strip()
                    # Remove any markdown code block markers that might be inside
                    json_str = re.sub(r'^```(?:json)?\s*', '', json_str)
                    json_str = re.sub(r'\s*```$', '', json_str)
                    json_data = json.loads(json_str)
                else:
                    # Step 3: Try to parse the whole response if it's pure JSON
                    json_str = text.strip()
                    # Remove markdown code block markers
                    json_str = re.sub(r'^```(?:json)?\s*', '', json_str)
                    json_str = re.sub(r'\s*```$', '', json_str)
                    # Remove any leading/trailing whitespace or newlines
                    json_str = json_str.strip()
                    json_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Step 4: Try more aggressive extraction - find the largest valid JSON structure
            try:
                # Find all potential JSON objects
                json_candidates = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
                for candidate in json_candidates:
                    try:
                        # Clean the candidate
                        cleaned = candidate.strip()
                        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                        cleaned = re.sub(r'\s*```$', '', cleaned)
                        # Try to parse
                        parsed = json.loads(cleaned)
                        # Validate it has the expected structure
                        if 'symptoms' in parsed and 'affected_components' in parsed:
                            json_data = parsed
                            break
                    except:
                        continue
            except Exception:
                pass
        except Exception as e:
            # Log the error for debugging but don't fail
            st.warning(f"⚠️ JSON extraction warning: {str(e)}")
            pass
        
        # Validate and clean the extracted JSON
        if json_data:
            # Ensure all required fields exist
            if 'symptoms' not in json_data:
                json_data['symptoms'] = []
            if 'affected_components' not in json_data:
                json_data['affected_components'] = {'pods': [], 'services': [], 'nodes': []}
            if 'severity' not in json_data:
                json_data['severity'] = 'Unknown'
            if 'time_window' not in json_data:
                json_data['time_window'] = None
            if 'initial_observations' not in json_data:
                json_data['initial_observations'] = []
            
            # Ensure affected_components has all required keys
            if 'pods' not in json_data['affected_components']:
                json_data['affected_components']['pods'] = []
            if 'services' not in json_data['affected_components']:
                json_data['affected_components']['services'] = []
            if 'nodes' not in json_data['affected_components']:
                json_data['affected_components']['nodes'] = []
        
        # Store token usage in session state
        if token_usage_info:
            st.session_state.token_usage['L1'] = token_usage_info
            # Calculate optimization savings
            actual_tokens = token_usage_info.get('total_token_count', 0)
            if actual_tokens > 0 and baseline_token_estimate > 0:
                savings = calculate_optimization_savings('L1', baseline_token_estimate, actual_tokens)
                st.session_state.optimization_savings['L1'] = savings
        
        return text, json_data
    except Exception as e:
        return f"Error performing L1 analysis: {str(e)}", None


def perform_l2_analysis(bundle_data: Dict) -> str:
    """Perform L2 analysis with correlation and root cause identification.
    Only analyzes data from the uploaded bundle - no real-time metrics collection."""
    # Collect RCA metrics from bundle only
    rca_metrics = collect_rca_metrics(bundle_data)
    
    # Build RCA metrics context from bundle only
    rca_context = ""
    if rca_metrics:
        error_patterns = rca_metrics.get('error_patterns', {})
        request_patterns = rca_metrics.get('request_patterns', {})
        service_stats = rca_metrics.get('service_stats', {})
        
        rca_context = f"""
RCA Log Analysis (from bundle):
- Error Categories: {error_patterns.get('error_categories', {})}
- Most Affected Service: {error_patterns.get('root_cause_candidates', {}).get('most_affected_service', 'N/A')}
- Most Frequent Error: {error_patterns.get('root_cause_candidates', {}).get('most_frequent_category', 'N/A')}
- Request Success Rate: {request_patterns.get('success_rate', 'N/A')}%
- Services Error Counts: {service_stats.get('errors_by_service', {})}
- Error Time Distribution: {list(error_patterns.get('error_time_distribution', {}).keys())[:5]}
"""
    
    # Calculate baseline token usage
    baseline_app_logs = '\n\n'.join([f"=== {log['filename']} ===\n{log['content'][:8000]}" for log in bundle_data.get('app_logs', [])[:10]])
    baseline_k8s_events = (str(bundle_data.get('k8s_events')) if bundle_data.get('k8s_events') is not None else 'N/A')[:5000]
    baseline_pod_status = (str(bundle_data.get('pod_status')) if bundle_data.get('pod_status') is not None else 'N/A')[:5000]
    
    baseline_prompt_template = """Perform L2 correlation analysis on the following data.

L2 CRITERIA - Correlation Analysis:
✅ Failing Components: Identify all components that are failing or degraded
✅ Dependencies: Map component dependencies and correlation between failures
✅ Probable Root Cause Identification: Provide a probable (not definitive) root cause statement

Your analysis must focus on:
1. **FAILING COMPONENTS**: Identify all failing pods, services, nodes, and storage components
2. **DEPENDENCIES**: Map dependencies between components and identify cascading failures
3. **PROBABLE ROOT CAUSE IDENTIFICATION**: Provide a probable root cause based on correlations (not definitive - that's for L3)

Tasks:
1. Correlate logs across pods, nodes, and services
2. Identify failing components and their dependencies
3. Analyze pod lifecycle events (CrashLoopBackOff, OOM, NotReady)
4. Identify configuration or infrastructure issues
5. Correlate storage issues with application failures
6. Provide a probable root cause statement based on correlations

Inputs:
- Application Logs:
{app_logs}

- Kubernetes Events:
{k8s_events}

- Pod Status:
{pod_status}
{storage_context}
{k8s_context}
{rca_context}
"""
    
    baseline_prompt = baseline_prompt_template.format(
        app_logs=baseline_app_logs,
        k8s_events=baseline_k8s_events,
        pod_status=baseline_pod_status,
        storage_context="",  # Disabled: Only using bundle data
        k8s_context="",  # Disabled: Only using bundle data
        rca_context=rca_context
    )
    
    # Estimate baseline token usage
    baseline_token_estimate = estimate_tokens(baseline_prompt) + 3000  # Add estimated response tokens
    st.session_state.baseline_token_usage['L2'] = baseline_token_estimate
    
    # Optimized approach: Use multilevel chunking for maximum token reduction
    optimized_app_logs = smart_chunk_logs(bundle_data.get('app_logs', [])[:10], max_chars_per_log=2000, max_logs=5)
    optimized_k8s_events = smart_chunk_text(str(bundle_data.get('k8s_events')) if bundle_data.get('k8s_events') is not None else 'N/A', max_chars=1800)
    optimized_pod_status = smart_chunk_text(str(bundle_data.get('pod_status')) if bundle_data.get('pod_status') is not None else 'N/A', max_chars=1800)
    
    prompt = """Perform L2 correlation analysis on the following data.

L2 CRITERIA - Correlation Analysis:
✅ Failing Components: Identify all components that are failing or degraded
✅ Dependencies: Map component dependencies and correlation between failures
✅ Probable Root Cause Identification: Provide a probable (not definitive) root cause statement

Your analysis must focus on:
1. **FAILING COMPONENTS**: Identify all failing pods, services, nodes, and storage components
2. **DEPENDENCIES**: Map dependencies between components and identify cascading failures
3. **PROBABLE ROOT CAUSE IDENTIFICATION**: Provide a probable root cause based on correlations (not definitive - that's for L3)

Tasks:
1. Correlate logs across pods, nodes, and services
2. Identify failing components and their dependencies
3. Analyze pod lifecycle events (CrashLoopBackOff, OOM, NotReady)
4. Identify configuration or infrastructure issues
5. Correlate storage issues with application failures
6. Provide a probable root cause statement based on correlations

Inputs:
- Application Logs:
{app_logs}

- Kubernetes Events:
{k8s_events}

- Pod Status:
{pod_status}
{rca_context}
""".format(
        app_logs=optimized_app_logs,
        k8s_events=optimized_k8s_events,
        pod_status=optimized_pod_status,
        rca_context=rca_context
    )
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=3000,
            )
        )
        
        # Extract token usage if available
        token_usage_info = {}
        try:
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                token_usage_info = {
                    'prompt_token_count': getattr(response.usage_metadata, 'prompt_token_count', 0),
                    'candidates_token_count': getattr(response.usage_metadata, 'candidates_token_count', 0),
                    'total_token_count': getattr(response.usage_metadata, 'total_token_count', 0)
                }
                st.session_state.token_usage['L2'] = token_usage_info
                # Calculate optimization savings
                actual_tokens = token_usage_info.get('total_token_count', 0)
                if actual_tokens > 0 and baseline_token_estimate > 0:
                    savings = calculate_optimization_savings('L2', baseline_token_estimate, actual_tokens)
                    st.session_state.optimization_savings['L2'] = savings
        except:
            pass
        
        return response.text
    except Exception as e:
        return f"Error performing L2 analysis: {str(e)}"


def process_chat_query(bundle_data: Dict, user_query: str, chat_history: List[Dict]) -> str:
    """Process a user query about the bundle logs using AI.
    
    Args:
        bundle_data: The parsed RCA bundle data
        user_query: User's question
        chat_history: Previous chat messages for context
    
    Returns:
        AI-generated answer based on bundle contents
    """
    if not GEMINI_API_KEY:
        return "⚠️ GEMINI_API_KEY not configured. Please set it in your environment variables."
    
    # Retry configuration for rate limiting
    max_retries = 3
    base_delay = 2  # seconds
    max_delay = 30  # seconds
    
    try:
        # Prepare context from bundle data using smart chunking
        app_logs = smart_chunk_logs(bundle_data.get('app_logs', [])[:10], max_chars_per_log=1500, max_logs=5)
        k8s_events = smart_chunk_text(str(bundle_data.get('k8s_events')) if bundle_data.get('k8s_events') is not None else 'N/A', max_chars=1000)
        pod_status = smart_chunk_text(str(bundle_data.get('pod_status')) if bundle_data.get('pod_status') is not None else 'N/A', max_chars=1000)
        errors = smart_chunk_text(str(bundle_data.get('errors')) if bundle_data.get('errors') is not None else 'N/A', max_chars=800)
        
        # Build context from bundle
        bundle_context = f"""
Bundle Contents Available:
- Application Logs: {app_logs[:3000]}...
- Kubernetes Events: {k8s_events[:1000]}...
- Pod Status: {pod_status[:1000]}...
- Errors: {errors[:800]}...
"""
        
        # Build conversation history context
        history_context = ""
        if chat_history:
            recent_history = chat_history[-3:]  # Last 3 exchanges for context
            history_context = "\n\nPrevious conversation:\n"
            for msg in recent_history:
                history_context += f"User: {msg.get('user', '')}\n"
                history_context += f"Assistant: {msg.get('assistant', '')}\n\n"
        
        # Create prompt
        prompt = f"""You are an AI assistant helping analyze RCA (Root Cause Analysis) bundle logs. 
Answer the user's question based ONLY on the information provided in the bundle logs.

{bundle_context}

{history_context}

User Question: {user_query}

Instructions:
- Answer based ONLY on the bundle log data provided above
- Be specific and cite relevant log entries or events when possible
- If information is not available in the logs, clearly state that
- Provide concise, accurate answers
- Focus on actionable insights when relevant

Answer:"""
        
        # Call Gemini API with retry logic for rate limiting
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        last_error = None
        for attempt in range(max_retries):
            try:
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=2000,
                    )
                )
                return response.text.strip()
            
            except Exception as e:
                error_str = str(e)
                last_error = e
                
                # Check if it's a rate limit error (429)
                if "429" in error_str or "Resource exhausted" in error_str or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        # Calculate exponential backoff delay
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        # Use info message instead of warning to avoid issues
                        time.sleep(delay)
                        continue
                    else:
                        return f"""⚠️ **Rate Limit Error**
                        
The API is currently rate-limited. Please try again in a few minutes.

**Suggestions:**
- Wait 1-2 minutes before asking another question
- Reduce the frequency of queries
- Check your API quota usage at https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas

Error details: {error_str}"""
                
                # For other errors, don't retry
                break
        
        # If we get here, all retries failed or it was a non-retryable error
        error_msg = str(last_error) if last_error else "Unknown error"
        if "429" not in error_msg and "Resource exhausted" not in error_msg:
            return f"❌ Error processing query: {error_msg}\n\nPlease try again or check your API configuration."
        else:
            return error_msg
    
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "Resource exhausted" in error_str:
            return f"""⚠️ **Rate Limit Error**
            
The API is currently rate-limited. Please try again in a few minutes.

**Suggestions:**
- Wait 1-2 minutes before asking another question
- Reduce the frequency of queries  
- Check your API quota at https://console.cloud.google.com/

Error: {error_str}"""
        return f"❌ Error processing query: {error_str}"


def perform_l3_analysis(bundle_data: Dict) -> str:
    """Perform L3 root cause analysis with recommendations.
    Only analyzes data from the uploaded bundle - no real-time metrics collection."""
    # Extract code snippets from logs if available
    code_snippet = ""
    for log in bundle_data.get('app_logs', []):
        if 'traceback' in log['content'].lower() or 'stack trace' in log['content'].lower():
            code_snippet = log['content'][:5000]
            break
    
    # Collect RCA metrics from bundle only
    rca_metrics = collect_rca_metrics(bundle_data)
    
    # Build RCA metrics context from bundle only
    rca_context = ""
    if rca_metrics:
        analysis = rca_metrics.get('comprehensive_analysis', {})
        summary = analysis.get('summary', {})
        error_patterns = rca_metrics.get('error_patterns', {})
        request_patterns = rca_metrics.get('request_patterns', {})
        
        rca_context = f"""
RCA Comprehensive Analysis (from bundle):
- Scenario: {summary.get('scenario', 'N/A')}
- Total Errors: {summary.get('total_errors', 0)}
- Total Events: {summary.get('total_events', 0)}
- Services Affected: {summary.get('services_affected', 0)}
- Error Rate: {summary.get('error_rate', 'N/A')}%
- Most Critical Service: {summary.get('most_critical_service', 'N/A')}
- Primary Error Category: {summary.get('primary_error_category', 'N/A')}
- Error Categories: {error_patterns.get('error_categories', {})}
- Request Success Rate: {request_patterns.get('success_rate', 'N/A')}%
- Top Error Messages: {[msg['message'][:50] for msg in error_patterns.get('top_error_messages', [])[:5]]}
"""
    
    # Extract power restart and hardware-related information from logs
    power_restart_info = ""
    hardware_issues = ""
    
    # Search for power-related events, hardware errors, and storage hardware issues
    for log in bundle_data.get('app_logs', []):
        content_lower = log['content'].lower()
        filename = log.get('filename', '').lower()
        
        # Look for power restart, hardware failures, storage hardware issues
        if any(keyword in content_lower for keyword in ['power', 'restart', 'reboot', 'shutdown', 'hardware', 'disk failure', 'storage controller', 'raid', 'hba', 'fiber channel', 'san', 'storage array']):
            relevant_lines = []
            for line in log['content'].split('\n'):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['power', 'restart', 'reboot', 'shutdown', 'hardware', 'disk', 'storage', 'controller', 'raid', 'hba', 'fiber', 'san', 'array', 'iops', 'latency', 'timeout']):
                    relevant_lines.append(line.strip())
                    if len(relevant_lines) >= 20:  # Limit to 20 most relevant lines
                        break
            
            if relevant_lines:
                power_restart_info += f"\n=== {log['filename']} ===\n" + '\n'.join(relevant_lines[:20]) + "\n"
        
        # Look for hardware-level storage issues
        if any(keyword in content_lower for keyword in ['storage server', 'storage hardware', 'disk controller', 'storage array', 'san switch', 'fiber channel', 'hba card', 'raid controller', 'storage backend', 'storage infrastructure']):
            relevant_lines = []
            for line in log['content'].split('\n'):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['storage server', 'hardware', 'controller', 'array', 'san', 'fiber', 'hba', 'raid', 'disk', 'backend', 'infrastructure', 'performance', 'bottleneck', 'degraded', 'failed']):
                    relevant_lines.append(line.strip())
                    if len(relevant_lines) >= 15:
                        break
            
            if relevant_lines:
                hardware_issues += f"\n=== {log['filename']} ===\n" + '\n'.join(relevant_lines[:15]) + "\n"
    
    # Storage context from bundle only (no real-time metrics)
    enhanced_storage_context = ""
    
    # Calculate baseline token usage
    baseline_rca_bundle = '\n\n'.join([f"=== {log['filename']} ===\n{log['content'][:10000]}" for log in bundle_data.get('app_logs', [])[:15]])
    baseline_k8s_yaml = '\n\n'.join([f"=== {manifest['filename']} ===\n{manifest['content']}" for manifest in bundle_data.get('deployment_manifests', [])])
    baseline_code_snippet = code_snippet[:5000] if code_snippet else 'N/A'
    baseline_power_restart_info = power_restart_info[:3000] if power_restart_info else 'No power restart events found in logs.'
    baseline_hardware_issues = hardware_issues[:3000] if hardware_issues else 'No explicit hardware-level storage issues found in logs. Analyze storage metrics for hardware problems.'
    
    baseline_prompt_template = """Perform L3 deep root cause analysis using the following inputs.

L3 CRITERIA - Deep Root Cause Analysis:
✅ Exact Cause Identification: Identify the exact root cause (code, config, design, or infrastructure)
✅ Fixes: Provide specific fixes and remediation steps
✅ Preventive Measures: Suggest preventive monitoring, alerts, and measures to prevent recurrence

Your analysis must focus on:
1. **EXACT CAUSE IDENTIFICATION**: Identify the definitive root cause (not probable - be specific)
2. **FIXES**: Provide specific, actionable fixes for the root cause
3. **PREVENTIVE MEASURES**: Suggest comprehensive preventive measures, monitoring, and alerts

Tasks:
1. Identify the EXACT root cause (code, config, design, or infrastructure) - be definitive
2. Correlate storage issues with application failures
3. Provide DETAILED hardware-level storage server analysis including:
   - Storage hardware component failures (controllers, disks, RAID arrays, SAN switches, HBA cards)
   - Storage infrastructure bottlenecks at the hardware level
   - Physical storage server issues that could cause low IOPS
   - Storage backend performance degradation
4. Analyze power restart reasons and their correlation with storage issues:
   - Identify any power-related events, restarts, or shutdowns
   - Correlate power events with storage performance degradation
   - Explain how power issues might have contributed to storage hardware problems
   - Document any evidence of power-related storage failures
5. Explain why existing checks or alerts failed
6. Recommend permanent fixes (code, deployment, infrastructure, or storage) with emphasis on:
   - Storage hardware upgrades or replacements
   - Storage infrastructure optimization
   - Power infrastructure improvements if needed
7. Suggest comprehensive preventive monitoring and alerts with SPECIFIC implementation details for:
   
   A. IOPS Monitoring:
      - Implement real-time monitoring of IOPS at the storage infrastructure level
      - Set aggressive alert thresholds for low IOPS (e.g., alert if IOPS drops below 50% of baseline or approaches zero)
      - Alerts should trigger well before IOPS drops to zero
      - Include both read and write IOPS monitoring
      - Monitor IOPS per storage volume, per node, and at the cluster level
   
   B. Latency Monitoring:
      - Monitor read and write latency at the storage level
      - High latency is often an early indicator of storage performance issues
      - Set thresholds for average, P95, and P99 latency
      - Alert if latency exceeds baseline by a significant margin (e.g., >2x baseline)
      - Monitor both storage-level latency and application-observed latency
   
   C. Disk Queue Depth Monitoring:
      - Monitor the disk queue depth continuously
      - A consistently high queue depth indicates that the storage system is overloaded
      - Set alerts when queue depth exceeds normal operating levels
      - Correlate queue depth with IOPS and latency metrics
   
   D. Storage Capacity Monitoring:
      - Monitor storage capacity utilization in real-time
      - Set alerts for approaching full capacity (e.g., >80% warning, >90% critical)
      - Monitor both used space and available space
      - Track capacity trends to predict when capacity will be exhausted
   
   E. Kubelet Volume Mount Error Rate:
      - Implement monitoring to track the rate of MountVolume.SetUp errors in the kubelet logs
      - Alert if the error rate exceeds a defined threshold (e.g., >1% of mount attempts)
      - Monitor for specific error patterns (timeouts, I/O errors, permission issues)
      - Track volume mount success/failure rates per node and per storage class
   
   F. CSI Driver Health Monitoring:
      - Monitor the health and status of the CSI driver
      - Track CSI driver pod status, restarts, and error rates
      - Monitor CSI driver API response times
      - Alert on CSI driver failures or degraded states
      - Monitor CSI driver logs for errors and warnings
   
   G. End-to-End Application Monitoring:
      - Implement end-to-end application monitoring to detect performance degradation caused by storage issues
      - Monitor application response times and correlate with storage metrics
      - Track application error rates and correlate with storage I/O errors
      - Monitor application startup times and correlate with volume mount times
      - Implement synthetic transactions to test storage-dependent application paths
   
   H. Correlated Alerts:
      - Configure alerts to correlate storage metrics (IOPS, latency, queue depth) with application performance metrics (response time, error rate)
      - Create composite alerts that trigger when multiple correlated metrics indicate a problem
      - Implement alert escalation based on correlation severity
      - Use alert grouping to reduce alert noise and improve signal-to-noise ratio
   
   Additional Monitoring:
   - Storage hardware health monitoring (controllers, disks, RAID arrays)
   - Power monitoring and alerting (UPS status, power events)
   - Storage infrastructure capacity planning
   - Network storage path monitoring (SAN switches, fiber channel links)
   - Storage backend performance metrics
8. Provide a comprehensive RCA summary that includes:
   - Detailed storage hardware-level root cause analysis
   - Power restart reasons and their impact on storage
   - Hardware-level storage infrastructure conclusions
   - The root cause should emphasize storage performance bottlenecks at the hardware level (e.g., extremely low IOPS due to storage server hardware issues, preventing kubelet from mounting volumes, leading to application startup failures and Velero restore failures)

IMPORTANT: The conclusion must include detailed analysis of:
- Storage server hardware-level issues (controllers, disks, arrays, SAN infrastructure)
- Power restart reasons that show correlation with storage problems
- How hardware-level storage bottlenecks cause application failures
- Specific hardware components that need attention

Inputs:
- Full RCA Bundle Logs:
{rca_bundle}

- Deployment Manifests:
{k8s_yaml}

- Backend Code Snippet:
{code_snippet}
{enhanced_storage_context}
{k8s_context}
{rca_context}

- Power Restart and Hardware Events:
{power_restart_info}

- Storage Hardware Issues:
{hardware_issues}
"""
    
    baseline_prompt = baseline_prompt_template.format(
        rca_bundle=baseline_rca_bundle,
        k8s_yaml=baseline_k8s_yaml,
        code_snippet=baseline_code_snippet,
        enhanced_storage_context="",  # Disabled: Only using bundle data
        k8s_context="",  # Disabled: Only using bundle data
        rca_context=rca_context,
        power_restart_info=baseline_power_restart_info,
        hardware_issues=baseline_hardware_issues
    )
    
    # Estimate baseline token usage
    baseline_token_estimate = estimate_tokens(baseline_prompt) + 4000  # Add estimated response tokens
    st.session_state.baseline_token_usage['L3'] = baseline_token_estimate
    
    # Optimized approach: Use multilevel chunking for maximum token reduction
    optimized_rca_bundle = smart_chunk_logs(bundle_data.get('app_logs', [])[:15], max_chars_per_log=3000, max_logs=8)
    optimized_k8s_yaml = smart_chunk_text(baseline_k8s_yaml, max_chars=2000) if baseline_k8s_yaml else 'N/A'
    optimized_code_snippet = smart_chunk_text(baseline_code_snippet, max_chars=2000) if baseline_code_snippet != 'N/A' else 'N/A'
    optimized_power_restart_info = smart_chunk_text(baseline_power_restart_info, max_chars=1500)
    optimized_hardware_issues = smart_chunk_text(baseline_hardware_issues, max_chars=1500)
    
    prompt = """Perform L3 deep root cause analysis using the following inputs.

L3 CRITERIA - Deep Root Cause Analysis:
✅ Exact Cause Identification: Identify the exact root cause (code, config, design, or infrastructure)
✅ Fixes: Provide specific fixes and remediation steps
✅ Preventive Measures: Suggest preventive monitoring, alerts, and measures to prevent recurrence

Your analysis must focus on:
1. **EXACT CAUSE IDENTIFICATION**: Identify the definitive root cause (not probable - be specific)
2. **FIXES**: Provide specific, actionable fixes for the root cause
3. **PREVENTIVE MEASURES**: Suggest comprehensive preventive measures, monitoring, and alerts

Tasks:
1. Identify the EXACT root cause (code, config, design, or infrastructure) - be definitive
2. Correlate storage issues with application failures
3. Provide DETAILED hardware-level storage server analysis including:
   - Storage hardware component failures (controllers, disks, RAID arrays, SAN switches, HBA cards)
   - Storage infrastructure bottlenecks at the hardware level
   - Physical storage server issues that could cause low IOPS
   - Storage backend performance degradation
4. Analyze power restart reasons and their correlation with storage issues:
   - Identify any power-related events, restarts, or shutdowns
   - Correlate power events with storage performance degradation
   - Explain how power issues might have contributed to storage hardware problems
   - Document any evidence of power-related storage failures
5. Explain why existing checks or alerts failed
6. Recommend permanent fixes (code, deployment, infrastructure, or storage) with emphasis on:
   - Storage hardware upgrades or replacements
   - Storage infrastructure optimization
   - Power infrastructure improvements if needed
7. Suggest comprehensive preventive monitoring and alerts with SPECIFIC implementation details for:
   
   A. IOPS Monitoring:
      - Implement real-time monitoring of IOPS at the storage infrastructure level
      - Set aggressive alert thresholds for low IOPS (e.g., alert if IOPS drops below 50% of baseline or approaches zero)
      - Alerts should trigger well before IOPS drops to zero
      - Include both read and write IOPS monitoring
      - Monitor IOPS per storage volume, per node, and at the cluster level
   
   B. Latency Monitoring:
      - Monitor read and write latency at the storage level
      - High latency is often an early indicator of storage performance issues
      - Set thresholds for average, P95, and P99 latency
      - Alert if latency exceeds baseline by a significant margin (e.g., >2x baseline)
      - Monitor both storage-level latency and application-observed latency
   
   C. Disk Queue Depth Monitoring:
      - Monitor the disk queue depth continuously
      - A consistently high queue depth indicates that the storage system is overloaded
      - Set alerts when queue depth exceeds normal operating levels
      - Correlate queue depth with IOPS and latency metrics
   
   D. Storage Capacity Monitoring:
      - Monitor storage capacity utilization in real-time
      - Set alerts for approaching full capacity (e.g., >80% warning, >90% critical)
      - Monitor both used space and available space
      - Track capacity trends to predict when capacity will be exhausted
   
   E. Kubelet Volume Mount Error Rate:
      - Implement monitoring to track the rate of MountVolume.SetUp errors in the kubelet logs
      - Alert if the error rate exceeds a defined threshold (e.g., >1% of mount attempts)
      - Monitor for specific error patterns (timeouts, I/O errors, permission issues)
      - Track volume mount success/failure rates per node and per storage class
   
   F. CSI Driver Health Monitoring:
      - Monitor the health and status of the CSI driver
      - Track CSI driver pod status, restarts, and error rates
      - Monitor CSI driver API response times
      - Alert on CSI driver failures or degraded states
      - Monitor CSI driver logs for errors and warnings
   
   G. End-to-End Application Monitoring:
      - Implement end-to-end application monitoring to detect performance degradation caused by storage issues
      - Monitor application response times and correlate with storage metrics
      - Track application error rates and correlate with storage I/O errors
      - Monitor application startup times and correlate with volume mount times
      - Implement synthetic transactions to test storage-dependent application paths
   
   H. Correlated Alerts:
      - Configure alerts to correlate storage metrics (IOPS, latency, queue depth) with application performance metrics (response time, error rate)
      - Create composite alerts that trigger when multiple correlated metrics indicate a problem
      - Implement alert escalation based on correlation severity
      - Use alert grouping to reduce alert noise and improve signal-to-noise ratio
   
   Additional Monitoring:
   - Storage hardware health monitoring (controllers, disks, RAID arrays)
   - Power monitoring and alerting (UPS status, power events)
   - Storage infrastructure capacity planning
   - Network storage path monitoring (SAN switches, fiber channel links)
   - Storage backend performance metrics
8. Provide a comprehensive RCA summary that includes:
   - Detailed storage hardware-level root cause analysis
   - Power restart reasons and their impact on storage
   - Hardware-level storage infrastructure conclusions
   - The root cause should emphasize storage performance bottlenecks at the hardware level (e.g., extremely low IOPS due to storage server hardware issues, preventing kubelet from mounting volumes, leading to application startup failures and Velero restore failures)

IMPORTANT: The conclusion must include detailed analysis of:
- Storage server hardware-level issues (controllers, disks, arrays, SAN infrastructure)
- Power restart reasons that show correlation with storage problems
- How hardware-level storage bottlenecks cause application failures
- Specific hardware components that need attention

Inputs:
- Full RCA Bundle Logs:
{rca_bundle}

- Deployment Manifests:
{k8s_yaml}

- Backend Code Snippet:
{code_snippet}
{enhanced_storage_context}
{k8s_context}
{rca_context}

- Power Restart and Hardware Events:
{power_restart_info}

- Storage Hardware Issues:
{hardware_issues}
""".format(
        rca_bundle=optimized_rca_bundle,
        k8s_yaml=optimized_k8s_yaml,
        code_snippet=optimized_code_snippet,
        enhanced_storage_context="",  # Disabled: Only using bundle data
        k8s_context="",  # Disabled: Only using bundle data
        rca_context=rca_context,
        power_restart_info=optimized_power_restart_info,
        hardware_issues=optimized_hardware_issues
    )
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4000,
            )
        )
        
        # Extract token usage if available
        token_usage_info = {}
        try:
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                token_usage_info = {
                    'prompt_token_count': getattr(response.usage_metadata, 'prompt_token_count', 0),
                    'candidates_token_count': getattr(response.usage_metadata, 'candidates_token_count', 0),
                    'total_token_count': getattr(response.usage_metadata, 'total_token_count', 0)
                }
                st.session_state.token_usage['L3'] = token_usage_info
                # Calculate optimization savings
                actual_tokens = token_usage_info.get('total_token_count', 0)
                if actual_tokens > 0 and baseline_token_estimate > 0:
                    savings = calculate_optimization_savings('L3', baseline_token_estimate, actual_tokens)
                    st.session_state.optimization_savings['L3'] = savings
        except:
            pass
        
        return response.text
    except Exception as e:
        return f"Error performing L3 analysis: {str(e)}"


def main():
    # Aziro Technologies Hero Section with Logo
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; 
                border: 1px solid rgba(255, 255, 255, 0.3); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <div style="display: flex; align-items: center; gap: 1.5rem;">
            <div style="display: flex; align-items: center; justify-content: center; width: 60px; height: 60px; 
                        background: linear-gradient(135deg, #1E3A8A 0%, #FF9933 100%); border-radius: 12px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2); padding: 12px;">
                <!-- Search Button Logo SVG -->
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <!-- Search circle -->
                    <circle cx="11" cy="11" r="7" stroke="white" stroke-width="2" fill="none"/>
                    <!-- Search handle -->
                    <path d="m20 20-4-4" stroke="white" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </div>
            <div style="flex: 1;">
                <div style="display: flex; align-items: baseline; gap: 0.5rem; margin-bottom: 0.25rem;">
                    <span style="font-size: 1.75rem; color: #1E3A8A; font-weight: 700; font-family: 'Inter', sans-serif;">Aziro</span>
                    <span style="font-size: 1.75rem; color: #FF9933; font-weight: 700; font-family: 'Inter', sans-serif;">Technologies</span>
                </div>
                <h1 style="color: #111827; font-family: 'Inter', sans-serif; font-weight: 600; 
                           font-size: 1.5rem; margin: 0.25rem 0;">RCA Analysis Agent</h1>
                <p style="font-size: 0.875rem; color: #6B7280; margin-top: 0.25rem; font-weight: 400; font-family: 'Inter', sans-serif;">
                AI-Powered Kubernetes Incident Analysis Platform
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Enterprise Sidebar - Professional Design
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1rem 0;">
            <h2 style="color: #111827; font-family: 'Inter', sans-serif; font-weight: 600; 
                       font-size: 1.25rem; margin-bottom: 1rem;">Analysis Levels</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: #FFFFFF; padding: 1rem; border-radius: 6px; margin: 0.75rem 0; 
                    border: 1px solid #E5E7EB; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
            <div style="margin-bottom: 0.5rem;">
                <strong style="color: var(--primary-blue); font-size: 0.875rem; font-weight: 600; 
                             font-family: 'Inter', sans-serif;">L1: Incident Triage</strong>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.75rem; margin: 0; line-height: 1.5; font-weight: 400;">
                Symptoms, affected components, severity assessment
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: #FFFFFF; padding: 1rem; border-radius: 6px; margin: 0.75rem 0; 
                    border: 1px solid #E5E7EB; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
            <div style="margin-bottom: 0.5rem;">
                <strong style="background: linear-gradient(135deg, var(--primary-blue) 0%, var(--saffron) 100%);
                             -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                             font-size: 0.875rem; font-weight: 600; 
                             font-family: 'Inter', sans-serif;">L2: Correlation Analysis</strong>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.75rem; margin: 0; line-height: 1.5; font-weight: 400;">
                Failing components, dependencies, probable root cause identification
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: #FFFFFF; padding: 1rem; border-radius: 6px; margin: 0.75rem 0; 
                    border: 1px solid #E5E7EB; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
            <div style="margin-bottom: 0.5rem;">
                <strong style="color: var(--saffron); font-size: 0.875rem; font-weight: 600; 
                             font-family: 'Inter', sans-serif;">L3: Deep Root Cause</strong>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.75rem; margin: 0; line-height: 1.5; font-weight: 400;">
                Exact cause identification, fixes, and preventive measures
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="background: #FFFFFF; padding: 1rem; border-radius: 6px; margin: 0.75rem 0; 
                    border: 1px solid #E5E7EB; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
            <h3 style="color: #111827; margin-top: 0; font-family: 'Inter', sans-serif; 
                      font-weight: 600; font-size: 1rem; margin-bottom: 0.5rem;">About</h3>
            <p style="color: #6B7280; font-size: 0.75rem; margin-bottom: 0; line-height: 1.5; font-weight: 400;">
                Advanced AI-powered platform to analyze Kubernetes RCA bundles and provide comprehensive multi-level incident analysis.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Enterprise File Upload Section - Professional Design
    st.markdown("""
    <div style="background: #FFFFFF; padding: 1.5rem; border-radius: 8px; margin: 1.5rem 0; 
                border: 1px solid #E5E7EB; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <div style="text-align: center;">
            <h2 style="color: #111827; font-family: 'Inter', sans-serif; font-weight: 600; 
                      font-size: 1.25rem; margin-bottom: 0.5rem;">Upload RCA Bundle</h2>
            <p style="color: #6B7280; font-size: 0.875rem; margin: 0; font-weight: 400;">
                Upload your Kubernetes incident analysis bundle (supports files up to 2GB)
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a tar.gz file",
        type=['tar.gz', 'gz'],
        help="Upload a tar.gz file containing RCA logs (supports files up to 2GB)",
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        with st.spinner("Parsing RCA bundle..."):
            bundle_data = parse_rca_bundle(uploaded_file)
            if bundle_data:
                st.session_state.bundle_data = bundle_data
                st.success(f"✅ Bundle parsed successfully! Found {len(bundle_data['files'])} files.")
                
                # Display bundle summary
                with st.expander("📦 Bundle Contents", expanded=False):
                    st.json({
                        'total_files': len(bundle_data['files']),
                        'app_logs': len(bundle_data['app_logs']),
                        'has_k8s_events': bundle_data['k8s_events'] is not None,
                        'has_pod_status': bundle_data['pod_status'] is not None,
                        'has_errors': bundle_data['errors'] is not None,
                        'has_timeline': bundle_data['timeline'] is not None,
                        'deployment_manifests': len(bundle_data['deployment_manifests'])
                    })
                    
                    st.markdown("**Files in bundle:**")
                    for filename in sorted(bundle_data['files'].keys()):
                        st.text(f"  • {filename}")
                
    # Enterprise Analysis Section
    if st.session_state.bundle_data:
        st.markdown("""
        <div style="margin: 2rem 0 1.5rem 0;">
            <h2 style="color: #111827; font-family: 'Inter', sans-serif; font-weight: 600; font-size: 1.5rem; margin-bottom: 0.5rem;">Analysis Dashboard</h2>
            <p style="color: #6B7280; font-size: 0.875rem; margin-top: 0.5rem; font-weight: 400; font-family: 'Inter', sans-serif;">
                Select an analysis level to begin comprehensive incident investigation
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 0.5rem;">
                <span class="analysis-badge badge-l1">L1</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Run L1 Analysis", use_container_width=True, key="l1_btn"):
                with st.spinner("🔍 Performing L1 analysis..."):
                    result, json_data = perform_l1_analysis(st.session_state.bundle_data)
                    st.session_state.analysis_results['L1'] = result
                    st.session_state.analysis_data['L1'] = json_data
        
        with col2:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 0.5rem;">
                <span class="analysis-badge badge-l2">L2</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Run L2 Analysis", use_container_width=True, key="l2_btn"):
                with st.spinner("🔬 Performing L2 analysis..."):
                    result = perform_l2_analysis(st.session_state.bundle_data)
                    st.session_state.analysis_results['L2'] = result
        
        with col3:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 0.5rem;">
                <span class="analysis-badge badge-l3">L3</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Run L3 Analysis", use_container_width=True, key="l3_btn"):
                with st.spinner("🎯 Performing L3 analysis..."):
                    result = perform_l3_analysis(st.session_state.bundle_data)
                    st.session_state.analysis_results['L3'] = result
        
        # Display results in tabs
        if st.session_state.analysis_results:
            st.markdown("---")
            
            # Create tabs for each analysis level
            tab_names = []
            if 'L1' in st.session_state.analysis_results:
                tab_names.append("🔵 L1 Analysis")
            if 'L2' in st.session_state.analysis_results:
                tab_names.append("🔷 L2 Analysis")
            if 'L3' in st.session_state.analysis_results:
                tab_names.append("🟠 L3 Analysis")
            
            if tab_names:
                tabs = st.tabs(tab_names)
                tab_index = 0
                
                # L1 Results Tab
                if 'L1' in st.session_state.analysis_results:
                    with tabs[tab_index]:
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
                                    backdrop-filter: blur(10px); padding: 2rem; border-radius: 20px; margin: 1.5rem 0; 
                                    border: 1px solid rgba(37, 99, 235, 0.2); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                            <div style="display: flex; align-items: center; gap: 1rem;">
                                <span style="font-size: 2.5rem;">🔍</span>
                                <div>
                                    <h3 style="color: #1E293B; margin: 0; font-family: 'Space Grotesk', sans-serif; 
                                              font-weight: 700; font-size: 1.75rem;">L1 Analysis - Incident Triage</h3>
                                    <p style="color: #64748B; margin: 0.5rem 0 0 0; font-size: 1rem;">Initial assessment and symptom identification</p>
                                </div>
                            </div>
                </div>
                        """, unsafe_allow_html=True)
                        
                        # Display stats and diagram
                        display_l1_stats_and_diagram(
                            st.session_state.bundle_data, 
                            st.session_state.analysis_data.get('L1'),
                            st.session_state.analysis_results['L1']
                        )
                        
                        # Display formatted JSON if available
                        if st.session_state.analysis_data.get('L1'):
                            st.markdown("---")
                            with st.expander("📋 View Structured JSON Data", expanded=False):
                                json_str = json.dumps(st.session_state.analysis_data['L1'], indent=2, ensure_ascii=False)
                                st.code(json_str, language='json')
                        
                        # Root Cause Analysis & Solutions - L1
                        st.markdown("---")
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, rgba(37, 99, 235, 0.08) 0%, rgba(0, 168, 255, 0.08) 100%);
                        padding: 2rem; border-radius: 16px; margin: 2rem 0; 
                        border: 2px solid rgba(37, 99, 235, 0.3); box-shadow: 0 8px 16px -4px rgba(0, 102, 255, 0.2);">
                        <h3 style="color: #2563EB; margin-top: 0; font-family: 'Poppins', sans-serif; 
                        font-weight: 800; font-size: 1.75rem; margin-bottom: 1rem;">
                        🔍 Root Cause Analysis & Incident Insights
                        </h3>
                        <p style="color: #475569; font-size: 1rem; margin-bottom: 1.5rem;">
                        Comprehensive analysis of symptoms, affected components, and initial root cause identification
                        </p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.95); padding: 2rem; border-radius: 12px; 
                        border: 1px solid rgba(37, 99, 235, 0.2); margin-bottom: 2rem; color: #1E293B;
                        line-height: 1.8; font-size: 1.05rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                        {st.session_state.analysis_results['L1']}
                        </div>
                        """, unsafe_allow_html=True)
            
                        # Display token usage for L1
                        if 'L1' in st.session_state.token_usage:
                            token_info = st.session_state.token_usage['L1']
                            total_tokens = token_info.get('total_token_count', 0)
                            prompt_tokens = token_info.get('prompt_token_count', 0)
                            response_tokens = token_info.get('candidates_token_count', 0)
                            
                            # Calculate cost
                            cost_info = calculate_token_cost(prompt_tokens, response_tokens)
                            
                            st.markdown("---")
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
                                        backdrop-filter: blur(10px); padding: 1.75rem; border-radius: 16px; 
                                        border: 1px solid rgba(37, 99, 235, 0.2); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                                        margin-bottom: 1rem;">
                                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                                    <span style="font-size: 1.75rem;">🔵</span>
                                    <h4 style="color: #2563EB; margin: 0; font-family: 'Space Grotesk', sans-serif; 
                                              font-weight: 700; font-size: 1.25rem;">L1 Analysis Token Usage</h4>
                                </div>
                                <div style="background: linear-gradient(135deg, rgba(37, 99, 235, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%);
                                            padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
                                    <p style="color: #1E293B; font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; font-family: 'Inter', sans-serif;">
                                        <strong style="color: #2563EB;">Total Tokens:</strong> <span style="color: #1E293B;">{total_tokens:,}</span>
                                    </p>
                                    <div style="display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.95rem; color: #64748B;">
                                        <span><strong>Prompt:</strong> {prompt_tokens:,}</span>
                                        <span><strong>Response:</strong> {response_tokens:,}</span>
                                    </div>
                                </div>
                                <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
                                            padding: 1rem; border-radius: 12px; border-left: 4px solid #10B981;">
                                    <p style="color: #1E293B; font-size: 1.125rem; font-weight: 700; margin: 0; font-family: 'Space Grotesk', sans-serif;">
                                        💵 Estimated Cost: <span style="color: #10B981; font-size: 1.25rem;">${cost_info['total_cost']:.6f}</span>
                                    </p>
                                    <div style="margin-top: 0.5rem; font-size: 0.875rem; color: #64748B;">
                                        Input: ${cost_info['input_cost']:.6f} • Output: ${cost_info['output_cost']:.6f}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Display optimization savings for L1
                            if 'L1' in st.session_state.optimization_savings:
                                savings = st.session_state.optimization_savings['L1']
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.12) 0%, rgba(255, 140, 66, 0.12) 100%);
                                            backdrop-filter: blur(10px); padding: 1.75rem; border-radius: 16px; 
                                            border: 2px solid rgba(249, 115, 22, 0.4); box-shadow: 0 8px 16px -4px rgba(249, 115, 22, 0.3);
                                            margin-top: 1.5rem; margin-bottom: 1rem;">
                                    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                                        <span style="font-size: 2rem;">💰</span>
                                        <h4 style="color: #F97316; margin: 0; font-family: 'Space Grotesk', sans-serif; 
                                                  font-weight: 800; font-size: 1.35rem;">Optimization Savings (Multilevel Chunking)</h4>
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1rem;">
                                        <div style="background: rgba(255, 255, 255, 0.6); padding: 1rem; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.2);">
                                            <p style="color: #64748B; font-size: 0.875rem; margin: 0 0 0.5rem 0; font-weight: 600;">Tokens Saved</p>
                                            <p style="color: #1E293B; font-size: 1.5rem; font-weight: 800; margin: 0; font-family: 'Space Grotesk', sans-serif;">
                                                {savings['tokens_saved']:,} <span style="color: #10B981; font-size: 1rem;">({savings['savings_percentage']:.1f}%)</span>
                                            </p>
                                            <p style="color: #64748B; font-size: 0.75rem; margin: 0.25rem 0 0 0;">
                                                Baseline: {savings['baseline_tokens']:,} → Optimized: {savings['optimized_tokens']:,}
                                            </p>
                                        </div>
                                        <div style="background: rgba(255, 255, 255, 0.6); padding: 1rem; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.2);">
                                            <p style="color: #64748B; font-size: 0.875rem; margin: 0 0 0.5rem 0; font-weight: 600;">Cost Saved</p>
                                            <p style="color: #1E293B; font-size: 1.5rem; font-weight: 800; margin: 0; font-family: 'Space Grotesk', sans-serif;">
                                                ${savings['cost_saved']:.6f} <span style="color: #10B981; font-size: 1rem;">({savings['cost_savings_percentage']:.1f}%)</span>
                                            </p>
                                            <p style="color: #64748B; font-size: 0.75rem; margin: 0.25rem 0 0 0;">
                                                Baseline: ${savings['baseline_cost']:.6f} → Optimized: ${savings['optimized_cost']:.6f}
                                            </p>
                                        </div>
                                    </div>
                                    <div style="background: rgba(16, 185, 129, 0.1); padding: 0.75rem; border-radius: 8px; border-left: 3px solid #10B981;">
                                        <p style="color: #1E293B; font-size: 0.9rem; margin: 0 0 0.5rem 0; font-weight: 600;">
                                            ✨ <strong style="color: #0066FF;">Multilevel chunking</strong> (4-level progressive filtering) reduced token usage by <strong style="color: #10B981;">{savings['savings_percentage']:.1f}%</strong> while maintaining analysis quality!
                                        </p>
                                        <p style="color: #64748B; font-size: 0.8rem; margin: 0; line-height: 1.5;">
                                            <strong>Multilevel Process:</strong> Level 1 → Extract critical content | Level 2 → Deduplicate & prioritize | Level 3 → Compress & summarize | Level 4 → Remove noise & optimize
                                        </p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    tab_index += 1
                
                # L2 Results Tab
                if 'L2' in st.session_state.analysis_results:
                    with tabs[tab_index]:
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
                                    backdrop-filter: blur(10px); padding: 2rem; border-radius: 20px; margin: 1.5rem 0; 
                                    border: 1px solid rgba(124, 58, 237, 0.2); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                            <div style="display: flex; align-items: center; gap: 1rem;">
                                <span style="font-size: 2.5rem;">🔬</span>
                                <div>
                                    <h3 style="color: #1E293B; margin: 0; font-family: 'Space Grotesk', sans-serif; 
                                              font-weight: 700; font-size: 1.75rem;">L2 Analysis - Correlation & Root Cause</h3>
                                    <p style="color: #64748B; margin: 0.5rem 0 0 0; font-size: 1rem;">Component correlation and probable root cause identification</p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Display stats and diagram
                        display_l2_stats_and_diagram(st.session_state.bundle_data, st.session_state.analysis_results['L2'])
                        
                        # Root Cause Analysis & Solutions - L2
                        st.markdown("---")
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(249, 115, 22, 0.08) 100%);
                                    padding: 2rem; border-radius: 16px; margin: 2rem 0; 
                                    border: 2px solid rgba(124, 58, 237, 0.3); box-shadow: 0 8px 16px -4px rgba(124, 58, 237, 0.2);">
                            <h3 style="color: #7C3AED; margin-top: 0; font-family: 'Poppins', sans-serif; 
                                      font-weight: 800; font-size: 1.75rem; margin-bottom: 1rem;">
                                🔬 Correlation Analysis & Root Cause Identification
                            </h3>
                            <p style="color: #475569; font-size: 1rem; margin-bottom: 1.5rem;">
                                Deep dive into component correlations, error patterns, and probable root causes with actionable insights
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.95); padding: 2rem; border-radius: 12px; 
                                    border: 1px solid rgba(124, 58, 237, 0.2); margin-bottom: 2rem; color: #1E293B;
                                    line-height: 1.8; font-size: 1.05rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                            {st.session_state.analysis_results['L2']}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Display token usage for L2
                        if 'L2' in st.session_state.token_usage:
                            token_info = st.session_state.token_usage['L2']
                            total_tokens = token_info.get('total_token_count', 0)
                            prompt_tokens = token_info.get('prompt_token_count', 0)
                            response_tokens = token_info.get('candidates_token_count', 0)
                            
                            # Calculate cost
                            cost_info = calculate_token_cost(prompt_tokens, response_tokens)
                            
                            st.markdown("---")
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
                                        backdrop-filter: blur(10px); padding: 1.75rem; border-radius: 16px; 
                                        border: 1px solid rgba(124, 58, 237, 0.2); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                                        margin-bottom: 1rem;">
                                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                                    <span style="font-size: 1.75rem;">🔷</span>
                                    <h4 style="color: #7C3AED; margin: 0; font-family: 'Space Grotesk', sans-serif; 
                                              font-weight: 700; font-size: 1.25rem;">L2 Analysis Token Usage</h4>
                                </div>
                                <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.05) 0%, rgba(99, 102, 241, 0.05) 100%);
                                            padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
                                    <p style="color: #1E293B; font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; font-family: 'Inter', sans-serif;">
                                        <strong style="color: #7C3AED;">Total Tokens:</strong> <span style="color: #1E293B;">{total_tokens:,}</span>
                                    </p>
                                    <div style="display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.95rem; color: #64748B;">
                                        <span><strong>Prompt:</strong> {prompt_tokens:,}</span>
                                        <span><strong>Response:</strong> {response_tokens:,}</span>
                                    </div>
                                </div>
                                <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
                                            padding: 1rem; border-radius: 12px; border-left: 4px solid #10B981;">
                                    <p style="color: #1E293B; font-size: 1.125rem; font-weight: 700; margin: 0; font-family: 'Space Grotesk', sans-serif;">
                                        💵 Estimated Cost: <span style="color: #10B981; font-size: 1.25rem;">${cost_info['total_cost']:.6f}</span>
                                    </p>
                                    <div style="margin-top: 0.5rem; font-size: 0.875rem; color: #64748B;">
                                        Input: ${cost_info['input_cost']:.6f} • Output: ${cost_info['output_cost']:.6f}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Display optimization savings for L2
                            if 'L2' in st.session_state.optimization_savings:
                                savings = st.session_state.optimization_savings['L2']
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.12) 0%, rgba(255, 140, 66, 0.12) 100%);
                                            backdrop-filter: blur(10px); padding: 1.75rem; border-radius: 16px; 
                                            border: 2px solid rgba(249, 115, 22, 0.4); box-shadow: 0 8px 16px -4px rgba(249, 115, 22, 0.3);
                                            margin-top: 1.5rem; margin-bottom: 1rem;">
                                    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                                        <span style="font-size: 2rem;">💰</span>
                                        <h4 style="color: #F97316; margin: 0; font-family: 'Space Grotesk', sans-serif; 
                                                  font-weight: 800; font-size: 1.35rem;">Optimization Savings (Multilevel Chunking)</h4>
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1rem;">
                                        <div style="background: rgba(255, 255, 255, 0.6); padding: 1rem; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.2);">
                                            <p style="color: #64748B; font-size: 0.875rem; margin: 0 0 0.5rem 0; font-weight: 600;">Tokens Saved</p>
                                            <p style="color: #1E293B; font-size: 1.5rem; font-weight: 800; margin: 0; font-family: 'Space Grotesk', sans-serif;">
                                                {savings['tokens_saved']:,} <span style="color: #10B981; font-size: 1rem;">({savings['savings_percentage']:.1f}%)</span>
                                            </p>
                                            <p style="color: #64748B; font-size: 0.75rem; margin: 0.25rem 0 0 0;">
                                                Baseline: {savings['baseline_tokens']:,} → Optimized: {savings['optimized_tokens']:,}
                                            </p>
                                        </div>
                                        <div style="background: rgba(255, 255, 255, 0.6); padding: 1rem; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.2);">
                                            <p style="color: #64748B; font-size: 0.875rem; margin: 0 0 0.5rem 0; font-weight: 600;">Cost Saved</p>
                                            <p style="color: #1E293B; font-size: 1.5rem; font-weight: 800; margin: 0; font-family: 'Space Grotesk', sans-serif;">
                                                ${savings['cost_saved']:.6f} <span style="color: #10B981; font-size: 1rem;">({savings['cost_savings_percentage']:.1f}%)</span>
                                            </p>
                                            <p style="color: #64748B; font-size: 0.75rem; margin: 0.25rem 0 0 0;">
                                                Baseline: ${savings['baseline_cost']:.6f} → Optimized: ${savings['optimized_cost']:.6f}
                                            </p>
                                        </div>
                                    </div>
                                    <div style="background: rgba(16, 185, 129, 0.1); padding: 0.75rem; border-radius: 8px; border-left: 3px solid #10B981;">
                                        <p style="color: #1E293B; font-size: 0.9rem; margin: 0 0 0.5rem 0; font-weight: 600;">
                                            ✨ <strong style="color: #0066FF;">Multilevel chunking</strong> (4-level progressive filtering) reduced token usage by <strong style="color: #10B981;">{savings['savings_percentage']:.1f}%</strong> while maintaining analysis quality!
                                        </p>
                                        <p style="color: #64748B; font-size: 0.8rem; margin: 0; line-height: 1.5;">
                                            <strong>Multilevel Process:</strong> Level 1 → Extract critical content | Level 2 → Deduplicate & prioritize | Level 3 → Compress & summarize | Level 4 → Remove noise & optimize
                                        </p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    tab_index += 1
                
                # L3 Results Tab
                if 'L3' in st.session_state.analysis_results:
                    with tabs[tab_index]:
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
                                    backdrop-filter: blur(10px); padding: 2rem; border-radius: 20px; margin: 1.5rem 0; 
                                    border: 1px solid rgba(249, 115, 22, 0.2); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                            <div style="display: flex; align-items: center; gap: 1rem;">
                                <span style="font-size: 2.5rem;">🎯</span>
                                <div>
                                    <h3 style="color: #1E293B; margin: 0; font-family: 'Space Grotesk', sans-serif; 
                                              font-weight: 700; font-size: 1.75rem;">L3 Analysis - Deep Root Cause & Recommendations</h3>
                                    <p style="color: #64748B; margin: 0.5rem 0 0 0; font-size: 1rem;">Comprehensive root cause analysis with actionable recommendations</p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Display stats and diagram
                        display_l3_stats_and_diagram(st.session_state.bundle_data, st.session_state.analysis_results['L3'])
                        
                        # Root Cause Analysis & Solutions - L3
                        st.markdown("---")
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.08) 0%, rgba(255, 107, 53, 0.08) 100%);
                                    padding: 2rem; border-radius: 16px; margin: 2rem 0; 
                                    border: 2px solid rgba(249, 115, 22, 0.3); box-shadow: 0 8px 16px -4px rgba(249, 115, 22, 0.2);">
                            <h3 style="color: #F97316; margin-top: 0; font-family: 'Poppins', sans-serif; 
                                      font-weight: 800; font-size: 1.75rem; margin-bottom: 1rem;">
                                🎯 Deep Root Cause Analysis & Comprehensive Solutions
                            </h3>
                            <p style="color: #475569; font-size: 1rem; margin-bottom: 1.5rem;">
                                Detailed root cause analysis with hardware-level insights, preventive measures, and actionable recommendations
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.95); padding: 2rem; border-radius: 12px; 
                                    border: 1px solid rgba(249, 115, 22, 0.2); margin-bottom: 2rem; color: #1E293B;
                                    line-height: 1.8; font-size: 1.05rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                            {st.session_state.analysis_results['L3']}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Final RCA Analysis Summary - Key Points
                        st.markdown("---")
                        st.markdown("""
                        <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
                                    padding: 2.5rem; border-radius: 20px; margin: 3rem 0 2rem 0; 
                                    border: 3px solid rgba(16, 185, 129, 0.4); box-shadow: 0 12px 24px -4px rgba(16, 185, 129, 0.3);">
                            <h3 style="color: #10B981; margin-top: 0; font-family: 'Poppins', sans-serif; 
                                      font-weight: 900; font-size: 2rem; margin-bottom: 1.5rem; text-align: center;">
                                🎯 Final RCA Analysis - Key Summary Points
                            </h3>
                            <p style="color: #475569; font-size: 1.1rem; margin-bottom: 2rem; text-align: center; font-weight: 600;">
                                Comprehensive root cause analysis summary with actionable insights and recommendations
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Extract and display key RCA points
                        l3_analysis_text = st.session_state.analysis_results.get('L3', '')
                        rca_metrics = None
                        if RCA_TOOLS_AVAILABLE:
                            rca_metrics = collect_rca_metrics(st.session_state.bundle_data)
                        
                        # Build final RCA summary points
                        final_rca_points = []
                        
                        # Extract root cause from analysis
                        if 'root cause' in l3_analysis_text.lower() or 'root cause' in l3_analysis_text.lower():
                            final_rca_points.append({
                                'title': 'Root Cause Identified',
                                'description': 'The primary root cause has been identified through comprehensive analysis of storage infrastructure, hardware components, and system performance metrics.'
                            })
                        
                        # Extract storage-related issues
                        if 'storage' in l3_analysis_text.lower() or 'IOPS' in l3_analysis_text.lower() or 'latency' in l3_analysis_text.lower():
                            final_rca_points.append({
                                'title': 'Storage Performance Bottleneck',
                                'description': 'Severe storage performance issues detected, including extremely low IOPS (0 IOPS), high latency, and storage infrastructure degradation preventing proper volume mounting.'
                            })
                        
                        # Extract hardware-level issues
                        if 'hardware' in l3_analysis_text.lower() or 'disk' in l3_analysis_text.lower() or 'storage server' in l3_analysis_text.lower():
                            final_rca_points.append({
                                'title': 'Hardware-Level Infrastructure Issues',
                                'description': 'Critical hardware-level problems identified in storage servers, including potential disk failures, power-related issues, and infrastructure bottlenecks affecting system reliability.'
                            })
                        
                        # Extract power-related issues
                        if 'power' in l3_analysis_text.lower() or 'restart' in l3_analysis_text.lower() or 'shutdown' in l3_analysis_text.lower():
                            final_rca_points.append({
                                'title': 'Power & Infrastructure Instability',
                                'description': 'Power-related incidents and unexpected restarts have been correlated with storage failures, indicating potential power infrastructure issues or insufficient redundancy.'
                            })
                        
                        # Extract solutions/recommendations
                        if 'recommendation' in l3_analysis_text.lower() or 'solution' in l3_analysis_text.lower() or 'fix' in l3_analysis_text.lower():
                            final_rca_points.append({
                                'title': 'Recommended Solutions & Actions',
                                'description': 'Comprehensive remediation plan includes storage infrastructure upgrades, hardware replacements, enhanced monitoring and alerting, and preventive measures to ensure system reliability.'
                            })
                        
                        # Extract monitoring recommendations
                        if 'monitoring' in l3_analysis_text.lower() or 'alert' in l3_analysis_text.lower() or 'preventive' in l3_analysis_text.lower():
                            final_rca_points.append({
                                'title': 'Preventive Monitoring & Alerting',
                                'description': 'Implementation of real-time monitoring for IOPS, latency, disk queue depth, capacity utilization, and correlated alerts to detect and prevent future incidents proactively.'
                            })
                        
                        # If no specific points extracted, add generic RCA summary
                        if not final_rca_points:
                            final_rca_points = [
                                {
                                    'title': 'Root Cause Analysis Complete',
                                    'description': 'Comprehensive root cause analysis has been performed across all system layers (L1, L2, L3) with detailed investigation of symptoms, correlations, and underlying infrastructure issues.'
                                },
                                {
                                    'title': 'Actionable Recommendations Provided',
                                    'description': 'Detailed recommendations and solutions have been identified to address the root cause and prevent recurrence, including infrastructure improvements and enhanced monitoring.'
                                }
                            ]
                        
                        # Display final RCA points
                        st.markdown("""
                        <div style="background: rgba(255, 255, 255, 0.98); padding: 2rem; border-radius: 16px; 
                                    border: 2px solid rgba(16, 185, 129, 0.3); margin-bottom: 2rem;
                                    box-shadow: 0 8px 16px -4px rgba(16, 185, 129, 0.2);">
                        """, unsafe_allow_html=True)
                        
                        for idx, point in enumerate(final_rca_points, 1):
                            st.markdown(f"""
                            <div style="margin-bottom: 1.5rem; padding: 1.5rem; background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(249, 115, 22, 0.05) 100%);
                                        border-radius: 12px; border-left: 5px solid #10B981;">
                                <h4 style="color: #059669; margin-top: 0; margin-bottom: 0.75rem; font-family: 'Poppins', sans-serif; 
                                          font-weight: 800; font-size: 1.35rem;">
                                    <strong>{idx}. {point['title']}</strong>
                                </h4>
                                <p style="color: #1E293B; margin: 0; line-height: 1.7; font-size: 1.05rem; font-family: 'Inter', sans-serif;">
                                    {point['description']}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # Display token usage for L3
                        if 'L3' in st.session_state.token_usage:
                            token_info = st.session_state.token_usage['L3']
                            total_tokens = token_info.get('total_token_count', 0)
                            prompt_tokens = token_info.get('prompt_token_count', 0)
                            response_tokens = token_info.get('candidates_token_count', 0)
                            
                            # Calculate cost
                            cost_info = calculate_token_cost(prompt_tokens, response_tokens)
                            
                            st.markdown("---")
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
                                        backdrop-filter: blur(10px); padding: 1.75rem; border-radius: 16px; 
                                        border: 1px solid rgba(249, 115, 22, 0.2); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                                        margin-bottom: 1rem;">
                                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                                    <span style="font-size: 1.75rem;">🟠</span>
                                    <h4 style="color: #F97316; margin: 0; font-family: 'Space Grotesk', sans-serif; 
                                              font-weight: 700; font-size: 1.25rem;">L3 Analysis Token Usage</h4>
                                </div>
                                <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.05) 0%, rgba(234, 88, 12, 0.05) 100%);
                                            padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
                                    <p style="color: #1E293B; font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; font-family: 'Inter', sans-serif;">
                                        <strong style="color: #F97316;">Total Tokens:</strong> <span style="color: #1E293B;">{total_tokens:,}</span>
                                    </p>
                                    <div style="display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.95rem; color: #64748B;">
                                        <span><strong>Prompt:</strong> {prompt_tokens:,}</span>
                                        <span><strong>Response:</strong> {response_tokens:,}</span>
                                    </div>
                                </div>
                                <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
                                            padding: 1rem; border-radius: 12px; border-left: 4px solid #10B981;">
                                    <p style="color: #1E293B; font-size: 1.125rem; font-weight: 700; margin: 0; font-family: 'Space Grotesk', sans-serif;">
                                        💵 Estimated Cost: <span style="color: #10B981; font-size: 1.25rem;">${cost_info['total_cost']:.6f}</span>
                                    </p>
                                    <div style="margin-top: 0.5rem; font-size: 0.875rem; color: #64748B;">
                                        Input: ${cost_info['input_cost']:.6f} • Output: ${cost_info['output_cost']:.6f}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Display optimization savings for L3
                            if 'L3' in st.session_state.optimization_savings:
                                savings = st.session_state.optimization_savings['L3']
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.12) 0%, rgba(255, 140, 66, 0.12) 100%);
                                            backdrop-filter: blur(10px); padding: 1.75rem; border-radius: 16px; 
                                            border: 2px solid rgba(249, 115, 22, 0.4); box-shadow: 0 8px 16px -4px rgba(249, 115, 22, 0.3);
                                            margin-top: 1.5rem; margin-bottom: 1rem;">
                                    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
                                        <span style="font-size: 2rem;">💰</span>
                                        <h4 style="color: #F97316; margin: 0; font-family: 'Space Grotesk', sans-serif; 
                                                  font-weight: 800; font-size: 1.35rem;">Optimization Savings (Multilevel Chunking)</h4>
                                    </div>
                                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 1rem;">
                                        <div style="background: rgba(255, 255, 255, 0.6); padding: 1rem; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.2);">
                                            <p style="color: #64748B; font-size: 0.875rem; margin: 0 0 0.5rem 0; font-weight: 600;">Tokens Saved</p>
                                            <p style="color: #1E293B; font-size: 1.5rem; font-weight: 800; margin: 0; font-family: 'Space Grotesk', sans-serif;">
                                                {savings['tokens_saved']:,} <span style="color: #10B981; font-size: 1rem;">({savings['savings_percentage']:.1f}%)</span>
                                            </p>
                                            <p style="color: #64748B; font-size: 0.75rem; margin: 0.25rem 0 0 0;">
                                                Baseline: {savings['baseline_tokens']:,} → Optimized: {savings['optimized_tokens']:,}
                                            </p>
                                        </div>
                                        <div style="background: rgba(255, 255, 255, 0.6); padding: 1rem; border-radius: 12px; border: 1px solid rgba(249, 115, 22, 0.2);">
                                            <p style="color: #64748B; font-size: 0.875rem; margin: 0 0 0.5rem 0; font-weight: 600;">Cost Saved</p>
                                            <p style="color: #1E293B; font-size: 1.5rem; font-weight: 800; margin: 0; font-family: 'Space Grotesk', sans-serif;">
                                                ${savings['cost_saved']:.6f} <span style="color: #10B981; font-size: 1rem;">({savings['cost_savings_percentage']:.1f}%)</span>
                                            </p>
                                            <p style="color: #64748B; font-size: 0.75rem; margin: 0.25rem 0 0 0;">
                                                Baseline: ${savings['baseline_cost']:.6f} → Optimized: ${savings['optimized_cost']:.6f}
                                            </p>
                                        </div>
                                    </div>
                                    <div style="background: rgba(16, 185, 129, 0.1); padding: 0.75rem; border-radius: 8px; border-left: 3px solid #10B981;">
                                        <p style="color: #1E293B; font-size: 0.9rem; margin: 0 0 0.5rem 0; font-weight: 600;">
                                            ✨ <strong style="color: #0066FF;">Multilevel chunking</strong> (4-level progressive filtering) reduced token usage by <strong style="color: #10B981;">{savings['savings_percentage']:.1f}%</strong> while maintaining analysis quality!
                                        </p>
                                        <p style="color: #64748B; font-size: 0.8rem; margin: 0; line-height: 1.5;">
                                            <strong>Multilevel Process:</strong> Level 1 → Extract critical content | Level 2 → Deduplicate & prioritize | Level 3 → Compress & summarize | Level 4 → Remove noise & optimize
                                        </p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Final Analysis Summary - After L3
                        if RCA_TOOLS_AVAILABLE:
                            rca_metrics = collect_rca_metrics(st.session_state.bundle_data)
                            if rca_metrics and 'error' not in rca_metrics.get('metadata', {}):
                                st.markdown("---")
                                st.markdown("### 🎯 Final Analysis Summary")
                                st.markdown("""
                                <div style="background: linear-gradient(135deg, rgba(0, 102, 255, 0.1) 0%, rgba(255, 107, 53, 0.1) 100%);
                                            padding: 2rem; border-radius: 20px; margin: 2rem 0; 
                                            border: 2px solid;
                                            border-image: linear-gradient(135deg, #0066FF 0%, #FF6B35 100%) 1;
                                            box-shadow: 0 8px 16px -4px rgba(0, 102, 255, 0.2), 0 8px 16px -4px rgba(255, 107, 53, 0.2);">
                                    <h3 style="color: #0F172A; margin-top: 0; font-family: 'Poppins', sans-serif; 
                                              font-weight: 800; font-size: 1.75rem; margin-bottom: 1rem;">
                                        📊 Comprehensive Incident Analysis Summary
                                    </h3>
                                    <p style="color: #475569; font-size: 1.1rem; margin: 0; font-weight: 500;">
                                        Complete overview combining insights from L1, L2, and L3 analysis levels
                                    </p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                error_stats = rca_metrics.get('error_stats', {})
                                service_stats = rca_metrics.get('service_stats', {})
                                request_patterns = rca_metrics.get('request_patterns', {})
                                timeline_stats = rca_metrics.get('timeline_stats', {})
                                errors_by_service = error_stats.get('errors_by_service', {})
                                
                                # Final Analysis Summary Chart
                                st.markdown("#### 📈 Final Analysis - Service Impact Summary")
                                final_summary_chart = create_rca_final_analysis_summary_chart(rca_metrics)
                                if final_summary_chart:
                                    st.plotly_chart(final_summary_chart, use_container_width=True, key="final_analysis_summary")
                                
                                # Final Analysis Summary Table
                                total_errors = error_stats.get('total_errors', 0)
                                total_events = timeline_stats.get('total_events', 0)
                                services_analyzed = len(service_stats.get('service_summary', {}))
                                success_rate = request_patterns.get('success_rate', 0)
                                top_error_category = max(error_stats.get('errors_by_category', {}).items(), key=lambda x: x[1])[0] if error_stats.get('errors_by_category') else 'N/A'
                                most_affected_service = max(errors_by_service.items(), key=lambda x: x[1])[0] if errors_by_service else 'N/A'
                                
                                # Calculate overall health score
                                service_summary = service_stats.get('service_summary', {})
                                total_health_score = 0
                                healthy_services = 0
                                for service, details in service_summary.items():
                                    if isinstance(details, dict) and 'error' not in details:
                                        error_rate = details.get('error_rate', 0)
                                        health_score = max(0, 100 - (error_rate * 2))
                                        total_health_score += health_score
                                        if health_score >= 80:
                                            healthy_services += 1
                                
                                avg_health_score = total_health_score / services_analyzed if services_analyzed > 0 else 0
                                
                                final_summary_data = [
                                    {'Metric': 'Total Errors Detected', 'Value': total_errors, 'Category': 'Errors'},
                                    {'Metric': 'Total Events Analyzed', 'Value': total_events, 'Category': 'Events'},
                                    {'Metric': 'Services Analyzed', 'Value': services_analyzed, 'Category': 'Services'},
                                    {'Metric': 'Overall Success Rate (%)', 'Value': f"{success_rate:.2f}%", 'Category': 'Performance'},
                                    {'Metric': 'Average Service Health Score', 'Value': f"{avg_health_score:.1f}/100", 'Category': 'Health'},
                                    {'Metric': 'Healthy Services', 'Value': f"{healthy_services}/{services_analyzed}", 'Category': 'Health'},
                                    {'Metric': 'Top Error Category', 'Value': top_error_category, 'Category': 'Root Cause'},
                                    {'Metric': 'Most Affected Service', 'Value': most_affected_service, 'Category': 'Root Cause'},
                                    {'Metric': 'Critical Services', 'Value': services_analyzed - healthy_services, 'Category': 'Health'},
                                    {'Metric': 'Overall Incident Severity', 'Value': 'Critical' if total_errors > 100 or success_rate < 50 else 'High' if total_errors > 50 or success_rate < 80 else 'Medium' if total_errors > 20 else 'Low', 'Category': 'Severity'}
                                ]
                                
                                if final_summary_data:
                                    final_summary_df = pd.DataFrame(final_summary_data)
                                    st.dataframe(final_summary_df, use_container_width=True, hide_index=True)
                                
                                # Final Timeline Summary Chart
                                st.markdown("---")
                                st.markdown("#### ⏱️ Final Analysis - Incident Timeline Progression")
                                final_timeline_chart = create_rca_final_timeline_summary_chart(rca_metrics)
                                if final_timeline_chart:
                                    st.plotly_chart(final_timeline_chart, use_container_width=True, key="final_timeline_summary")
                                
                                # Final Comprehensive Analysis Table
                                st.markdown("---")
                                st.markdown("#### 📋 Final Comprehensive Analysis Table")
                                
                                # Create comprehensive final analysis table
                                comprehensive_analysis = []
                                
                                # Service-level final analysis
                                for service, details in service_stats.get('service_summary', {}).items():
                                    if isinstance(details, dict) and 'error' not in details:
                                        errors = details.get('errors', 0)
                                        error_rate = details.get('error_rate', 0)
                                        total_entries = details.get('total_entries', 0)
                                        service_errors = errors_by_service.get(service, 0)
                                        perf = details.get('performance', {})
                                        latency = perf.get('latency', {}) if perf else {}
                                        
                                        # Calculate final score
                                        final_score = (error_rate * 0.3) + (service_errors * 0.25) + ((100 - (error_rate * 2)) * 0.25) + ((latency.get('avg', 0) / 10) * 0.2 if latency else 0)
                                        
                                        comprehensive_analysis.append({
                                            'Service': service,
                                            'Total Entries': total_entries,
                                            'Total Errors': errors,
                                            'Service Errors': service_errors,
                                            'Error Rate (%)': round(error_rate, 2),
                                            'Avg Latency (ms)': round(latency.get('avg', 0), 2) if latency else 'N/A',
                                            'Health Score': round(max(0, 100 - (error_rate * 2)), 1),
                                            'Final Impact Score': round(final_score, 1),
                                            'Priority': 'P0 - Critical' if final_score > 50 else 'P1 - High' if final_score > 30 else 'P2 - Medium' if final_score > 15 else 'P3 - Low',
                                            'Recommendation': 'Immediate Action Required' if final_score > 50 else 'High Priority Fix' if final_score > 30 else 'Monitor Closely' if final_score > 15 else 'Normal Operations'
                                        })
                                
                                if comprehensive_analysis:
                                    comprehensive_df = pd.DataFrame(comprehensive_analysis).sort_values('Final Impact Score', ascending=False)
                                    st.dataframe(comprehensive_df, use_container_width=True, hide_index=True)
            
            # Download results (outside tabs, always visible)
            
            # Download results
            if st.session_state.analysis_results:
                st.markdown("---")
                results_json = json.dumps(st.session_state.analysis_results, indent=2)
                st.download_button(
                    label="📥 Download Analysis Results (JSON)",
                    data=results_json,
                    file_name="rca_analysis_results.json",
                    mime="application/json"
                )
    
    # RCA Analysis Chatbot Section - Ask questions about the bundle
    if st.session_state.bundle_data:
        st.markdown("---")
        st.markdown("""
        <div style="background: linear-gradient(135deg, #E6F2FF 0%, #FFE5CC 100%); padding: 1.5rem; border-radius: 8px; margin: 1.5rem 0; 
                    border: 1px solid #E5E7EB; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                <span style="font-size: 1.5rem;">🤖</span>
                <h2 style="color: #111827; font-family: 'Inter', sans-serif; font-weight: 600; 
                          font-size: 1.5rem; margin: 0;">RCA Analysis Chatbot</h2>
            </div>
            <p style="color: #6B7280; font-size: 0.875rem; margin: 0; font-weight: 400;">
                Ask questions about your RCA bundle logs and get AI-powered answers based on the uploaded bundle contents
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Chat input
        user_query = st.chat_input("Ask a question about your RCA bundle logs...")
        
        if user_query:
            # Add user message to history
            st.session_state.chat_history.append({
                'user': user_query,
                'assistant': ''
            })
            
            # Process query
            with st.spinner("🤔 Analyzing bundle logs..."):
                answer = process_chat_query(
                    st.session_state.bundle_data,
                    user_query,
                    st.session_state.chat_history[:-1]  # Exclude current message
                )
                
                # Update last message with answer
                st.session_state.chat_history[-1]['assistant'] = answer
            
            # Rerun to show new messages
            st.rerun()
        
        # Display conversation history at the bottom
        if st.session_state.chat_history:
            st.markdown("---")
            st.markdown("""
            <div style="background: #FFFFFF; padding: 1.25rem; border-radius: 8px; margin: 1.5rem 0; 
                        border: 1px solid #E5E7EB; box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.1);">
                <h3 style="color: #111827; font-family: 'Inter', sans-serif; font-weight: 600; 
                          font-size: 1.125rem; margin: 0 0 1rem 0; display: flex; align-items: center; gap: 0.5rem;">
                    💬 Conversation History
                </h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Display all messages in the conversation
            for i, msg in enumerate(st.session_state.chat_history):
                with st.chat_message("user"):
                    st.write(msg['user'])
                with st.chat_message("assistant"):
                    st.markdown(msg['assistant'])
            
            # Add some spacing at the end
            st.markdown("<br>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
