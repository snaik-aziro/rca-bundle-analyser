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
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import google.generativeai as genai
from io import BytesIO
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

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

# Custom CSS for modern Gen Z + professional styling
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Header styling with gradient */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    /* Subheader styling */
    h2 {
        color: #6366F1;
        font-weight: 700;
        border-bottom: 3px solid #6366F1;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
    }
    
    h3 {
        color: #8B5CF6;
        font-weight: 600;
    }
    
    /* Body text for light theme */
    p {
        color: #475569;
    }
    
    /* Button styling - L1, L2, L3 with different colors */
    .stButton > button {
        border-radius: 12px;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* L1 Analysis Button - Blue */
    div[data-testid="column"]:nth-of-type(1) button {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white;
    }
    
    div[data-testid="column"]:nth-of-type(1) button:hover {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
    }
    
    /* L2 Analysis Button - Purple */
    div[data-testid="column"]:nth-of-type(2) button {
        background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
        color: white;
    }
    
    div[data-testid="column"]:nth-of-type(2) button:hover {
        background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%);
    }
    
    /* L3 Analysis Button - Pink/Purple */
    div[data-testid="column"]:nth-of-type(3) button {
        background: linear-gradient(135deg, #EC4899 0%, #DB2777 100%);
        color: white;
    }
    
    div[data-testid="column"]:nth-of-type(3) button:hover {
        background: linear-gradient(135deg, #DB2777 0%, #BE185D 100%);
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        border-radius: 8px;
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
    }
    
    /* Success message styling */
    .stSuccess {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        border-radius: 8px;
        padding: 1rem;
        border-left: 4px solid #059669;
    }
    
    /* Info boxes with modern styling */
    .stExpander {
        background-color: rgba(99, 102, 241, 0.05);
        border-radius: 8px;
        border: 1px solid rgba(99, 102, 241, 0.15);
    }
    
    /* Analysis result cards */
    .analysis-result {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid #6366F1;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* File uploader styling */
    .stFileUploader {
        border: 2px dashed #6366F1;
        border-radius: 12px;
        padding: 2rem;
        background: rgba(99, 102, 241, 0.03);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
    }
    
    /* Sidebar text colors for light theme */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #1E293B;
    }
    
    /* Code blocks */
    code {
        background: rgba(99, 102, 241, 0.08);
        color: #6366F1;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
        font-size: 0.9em;
    }
    
    /* Markdown styling improvements */
    .stMarkdown {
        line-height: 1.8;
    }
    
    /* Badge-like styling for analysis levels */
    .analysis-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        margin: 0.25rem;
    }
    
    .badge-l1 {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white;
    }
    
    .badge-l2 {
        background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
        color: white;
    }
    
    .badge-l3 {
        background: linear-gradient(135deg, #EC4899 0%, #DB2777 100%);
        color: white;
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


def parse_rca_bundle(uploaded_file) -> Optional[Dict]:
    """Parse uploaded RCA bundle (tar.gz) and extract all files."""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
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
        
        with tarfile.open(tmp_path, 'r:gz') as tar:
            for member in tar.getmembers():
                if member.isfile():
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
        
        Path(tmp_path).unlink()  # Clean up
        return bundle_data
    except Exception as e:
        st.error(f"Error parsing bundle: {str(e)}")
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
            marker_color=['#3B82F6', '#8B5CF6', '#EC4899'],
            text=list(component_data.values()),
            textposition='outside',
            showlegend=False
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title=dict(text='L1 Analysis - Incident Overview', font=dict(size=20, color='#3B82F6')),
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
        marker_color=['#8B5CF6', '#EC4899', '#F59E0B'][:len(events)],
        text=counts,
        textposition='outside',
        name='Events'
    ))
    
    fig.update_layout(
        title=dict(text='L2 Analysis - Pod Lifecycle Events', font=dict(size=20, color='#8B5CF6')),
        xaxis_title='Event Type',
        yaxis_title='Count',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def create_l3_diagram(stats: Dict) -> go.Figure:
    """Create L3 analysis diagram."""
    fig = go.Figure()
    
    # Root cause type and recommendations
    root_cause = stats['root_cause_type']
    labels = [k for k, v in root_cause.items() if v > 0] or ['Unknown']
    values = [v for k, v in root_cause.items() if v > 0] or [1]
    
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=['#EC4899', '#8B5CF6', '#3B82F6'][:len(labels)],
        text=values,
        textposition='outside',
        name='Root Cause Type'
    ))
    
    fig.update_layout(
        title=dict(text='L3 Analysis - Root Cause Type', font=dict(size=20, color='#EC4899')),
        xaxis_title='Root Cause Category',
        yaxis_title='Count',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1E293B')
    )
    
    return fig


def display_l1_stats_and_diagram(bundle_data: Dict, analysis_data: Optional[Dict] = None, analysis_text: str = ""):
    """Display L1 statistics and diagram."""
    stats = extract_l1_stats(bundle_data, analysis_data, analysis_text)
    
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
    
    # Diagram
    fig = create_l1_diagram(stats, analysis_data)
    st.plotly_chart(fig, use_container_width=True)
    
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
                <div style="background: rgba(59, 130, 246, 0.05); padding: 1rem; border-radius: 8px; 
                            border-left: 4px solid #3B82F6; margin-top: 1rem;">
                    <h4 style="color: #3B82F6; margin-top: 0;">⏰ Time Window</h4>
                    <p style="margin-bottom: 0;">{}</p>
                </div>
                """.format(analysis_data['time_window']), unsafe_allow_html=True)
        
        with col2:
            affected = analysis_data.get('affected_components', {})
            
            if affected.get('pods'):
                st.markdown("""
                <div style="background: rgba(139, 92, 246, 0.05); padding: 1rem; border-radius: 8px; 
                            border-left: 4px solid #8B5CF6; margin-bottom: 1rem;">
                    <h4 style="color: #8B5CF6; margin-top: 0;">📦 Affected Pods</h4>
                </div>
                """, unsafe_allow_html=True)
                for pod in affected['pods'][:10]:  # Show first 10
                    st.markdown(f"  • `{pod}`")
                if len(affected['pods']) > 10:
                    st.caption(f"... and {len(affected['pods']) - 10} more")
            
            if affected.get('services'):
                st.markdown("""
                <div style="background: rgba(16, 185, 129, 0.05); padding: 1rem; border-radius: 8px; 
                            border-left: 4px solid #10B981; margin-top: 1rem;">
                    <h4 style="color: #10B981; margin-top: 0;">🔧 Affected Services</h4>
                </div>
                """, unsafe_allow_html=True)
                for svc in affected['services']:
                    st.markdown(f"  • `{svc}`")
            
            if affected.get('nodes'):
                st.markdown("""
                <div style="background: rgba(245, 158, 11, 0.05); padding: 1rem; border-radius: 8px; 
                            border-left: 4px solid #F59E0B; margin-top: 1rem;">
                    <h4 style="color: #F59E0B; margin-top: 0;">🖥️ Affected Nodes</h4>
                </div>
                """, unsafe_allow_html=True)
                for node in affected['nodes']:
                    st.markdown(f"  • `{node}`")
        
        if analysis_data.get('initial_observations'):
            st.markdown("---")
            st.markdown("""
            <div style="background: rgba(99, 102, 241, 0.05); padding: 1rem; border-radius: 8px; 
                        border-left: 4px solid #6366F1;">
                <h4 style="color: #6366F1; margin-top: 0;">👁️ Initial Observations</h4>
            </div>
            """, unsafe_allow_html=True)
            for obs in analysis_data['initial_observations']:
                st.markdown(f"  • {obs}")


def display_l2_stats_and_diagram(bundle_data: Dict, analysis_text: str):
    """Display L2 statistics and diagram."""
    stats = extract_l2_stats(bundle_data, analysis_text)
    
    # Stats cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Failing Components", len(stats['failing_components']), delta=None)
    with col2:
        st.metric("Dependency Issues", stats['dependency_issues'], delta=None)
    with col3:
        st.metric("Config Issues", stats['config_issues'], delta=None)
    
    # Diagram
    fig = create_l2_diagram(stats)
    st.plotly_chart(fig, use_container_width=True)
    
    # Failing components list
    if stats['failing_components']:
        st.markdown("**Failing Components:**")
        for component in stats['failing_components']:
            st.markdown(f"  • {component}")


def display_l3_stats_and_diagram(bundle_data: Dict, analysis_text: str):
    """Display L3 statistics and diagram."""
    stats = extract_l3_stats(bundle_data, analysis_text)
    
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
    fig = create_l3_diagram(stats)
    st.plotly_chart(fig, use_container_width=True)


def perform_l1_analysis(bundle_data: Dict) -> Tuple[str, Optional[Dict]]:
    """Perform L1 incident triage analysis. Returns both text and structured JSON."""
    prompt = """You are a Kubernetes operations analyst performing L1 incident triage.
Your task is to quickly identify symptoms, affected components, severity,
and time window from the provided Kubernetes logs.
Do NOT speculate on root cause.
Output must be concise and structured.

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
""".format(
        app_logs='\n\n'.join([f"=== {log['filename']} ===\n{log['content'][:5000]}" for log in bundle_data.get('app_logs', [])[:5]]),
        k8s_events=str(bundle_data.get('k8s_events', 'N/A'))[:3000],
        pod_status=bundle_data.get('pod_status', 'N/A')[:3000],
        errors=json.dumps(bundle_data.get('errors', {}), indent=2)[:3000] if bundle_data.get('errors') else 'N/A'
    )
    
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
        
        return text, json_data
    except Exception as e:
        return f"Error performing L1 analysis: {str(e)}", None


def perform_l2_analysis(bundle_data: Dict) -> str:
    """Perform L2 analysis with correlation and root cause identification."""
    prompt = """Perform L2 analysis on the following data.

Tasks:
1. Correlate logs across pods, nodes, and services
2. Identify failing components and dependencies
3. Analyze pod lifecycle events (CrashLoopBackOff, OOM, NotReady)
4. Identify configuration or infrastructure issues
5. Provide a probable root cause statement

Inputs:
- Application Logs:
{app_logs}

- Kubernetes Events:
{k8s_events}

- Pod Status:
{pod_status}
""".format(
        app_logs='\n\n'.join([f"=== {log['filename']} ===\n{log['content'][:8000]}" for log in bundle_data.get('app_logs', [])[:10]]),
        k8s_events=str(bundle_data.get('k8s_events', 'N/A'))[:5000],
        pod_status=bundle_data.get('pod_status', 'N/A')[:5000]
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
        return response.text
    except Exception as e:
        return f"Error performing L2 analysis: {str(e)}"


def perform_l3_analysis(bundle_data: Dict) -> str:
    """Perform L3 root cause analysis with recommendations."""
    # Extract code snippets from logs if available
    code_snippet = ""
    for log in bundle_data.get('app_logs', []):
        if 'traceback' in log['content'].lower() or 'stack trace' in log['content'].lower():
            code_snippet = log['content'][:5000]
            break
    
    prompt = """Perform L3 root cause analysis using the following inputs.

Tasks:
1. Identify the exact root cause (code, config, or design)
2. Explain why existing checks or alerts failed
3. Recommend permanent fixes (code, deployment, or infra)
4. Suggest preventive monitoring and alerts
5. Provide a concise RCA summary

Inputs:
- Full RCA Bundle Logs:
{rca_bundle}

- Deployment Manifests:
{k8s_yaml}

- Backend Code Snippet:
{code_snippet}
""".format(
        rca_bundle='\n\n'.join([f"=== {log['filename']} ===\n{log['content'][:10000]}" for log in bundle_data.get('app_logs', [])[:15]]),
        k8s_yaml='\n\n'.join([f"=== {manifest['filename']} ===\n{manifest['content']}" for manifest in bundle_data.get('deployment_manifests', [])]),
        code_snippet=code_snippet[:5000] if code_snippet else 'N/A'
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
        return response.text
    except Exception as e:
        return f"Error performing L3 analysis: {str(e)}"


def main():
    # Hero section with gradient title
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="margin-bottom: 0.5rem;">🔍 RCA Analysis Agent</h1>
        <p style="font-size: 1.2rem; color: #64748B; margin-top: 0;">AI-Powered Kubernetes Incident Analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sidebar for information
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1rem 0;">
            <h2 style="color: #6366F1; border-bottom: 2px solid #6366F1; padding-bottom: 0.5rem;">📋 Analysis Levels</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(37, 99, 235, 0.08) 100%); 
                    padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #3B82F6;">
            <strong style="color: #3B82F6;">🔍 L1: Incident Triage</strong><br>
            <span style="color: #64748B; font-size: 0.9rem;">Symptoms, affected components, severity</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(124, 58, 237, 0.08) 100%); 
                    padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #8B5CF6;">
            <strong style="color: #8B5CF6;">🔬 L2: Correlation Analysis</strong><br>
            <span style="color: #64748B; font-size: 0.9rem;">Failing components, dependencies, probable root cause</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(236, 72, 153, 0.08) 0%, rgba(219, 39, 119, 0.08) 100%); 
                    padding: 1rem; border-radius: 8px; margin: 0.5rem 0; border-left: 4px solid #EC4899;">
            <strong style="color: #EC4899;">🎯 L3: Deep Root Cause</strong><br>
            <span style="color: #64748B; font-size: 0.9rem;">Exact cause, fixes, preventive measures</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("""
        <div style="background: rgba(99, 102, 241, 0.05); padding: 1rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.15);">
            <h3 style="color: #6366F1; margin-top: 0;">ℹ️ About</h3>
            <p style="color: #475569; font-size: 0.9rem; margin-bottom: 0;">
            Powered by <strong style="color: #6366F1;">Google Gemini AI</strong> to analyze
            Kubernetes RCA bundles and provide multi-level
            incident analysis.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # File upload section
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%); 
                padding: 2rem; border-radius: 12px; margin: 1rem 0; border: 2px dashed #6366F1;">
        <h2 style="color: #6366F1; margin-top: 0;">📤 Upload RCA Bundle</h2>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "Choose a tar.gz file",
        type=['tar.gz', 'gz'],
        help="Upload a tar.gz file containing RCA logs",
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
    
    # Analysis section
    if st.session_state.bundle_data:
        st.markdown("""
        <div style="margin: 2rem 0;">
            <h2 style="color: #6366F1;">📊 Analysis</h2>
            <p style="color: #64748B;">Select an analysis level to begin</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 0.5rem;">
                <span class="analysis-badge badge-l1">L1</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔍 Run L1 Analysis", use_container_width=True, key="l1_btn"):
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
            if st.button("🔬 Run L2 Analysis", use_container_width=True, key="l2_btn"):
                with st.spinner("🔬 Performing L2 analysis..."):
                    result = perform_l2_analysis(st.session_state.bundle_data)
                    st.session_state.analysis_results['L2'] = result
        
        with col3:
            st.markdown("""
            <div style="text-align: center; margin-bottom: 0.5rem;">
                <span class="analysis-badge badge-l3">L3</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🎯 Run L3 Analysis", use_container_width=True, key="l3_btn"):
                with st.spinner("🎯 Performing L3 analysis..."):
                    result = perform_l3_analysis(st.session_state.bundle_data)
                    st.session_state.analysis_results['L3'] = result
        
        # Display results
        if st.session_state.analysis_results:
            st.markdown("---")
            
            # L1 Results
            if 'L1' in st.session_state.analysis_results:
                st.markdown("""
                <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%); 
                            padding: 1.5rem; border-radius: 12px; margin: 1rem 0; border-left: 4px solid #3B82F6;">
                    <h3 style="color: #3B82F6; margin-top: 0;">📋 L1 Analysis - Incident Triage</h3>
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
                
                st.markdown("---")
                st.markdown("**Detailed Analysis:**")
                st.markdown(f"""
                <div style="background: rgba(59, 130, 246, 0.03); padding: 1.5rem; border-radius: 8px; 
                            border: 1px solid rgba(59, 130, 246, 0.15); margin-bottom: 2rem; color: #1E293B;">
                    {st.session_state.analysis_results['L1']}
                </div>
                """, unsafe_allow_html=True)
            
            # L2 Results
            if 'L2' in st.session_state.analysis_results:
                st.markdown("""
                <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(124, 58, 237, 0.1) 100%); 
                            padding: 1.5rem; border-radius: 12px; margin: 1rem 0; border-left: 4px solid #8B5CF6;">
                    <h3 style="color: #8B5CF6; margin-top: 0;">🔬 L2 Analysis - Correlation & Root Cause</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Display stats and diagram
                display_l2_stats_and_diagram(st.session_state.bundle_data, st.session_state.analysis_results['L2'])
                
                st.markdown("---")
                st.markdown("**Detailed Analysis:**")
                st.markdown(f"""
                <div style="background: rgba(139, 92, 246, 0.03); padding: 1.5rem; border-radius: 8px; 
                            border: 1px solid rgba(139, 92, 246, 0.15); margin-bottom: 2rem; color: #1E293B;">
                    {st.session_state.analysis_results['L2']}
                </div>
                """, unsafe_allow_html=True)
            
            # L3 Results
            if 'L3' in st.session_state.analysis_results:
                st.markdown("""
                <div style="background: linear-gradient(135deg, rgba(236, 72, 153, 0.1) 0%, rgba(219, 39, 119, 0.1) 100%); 
                            padding: 1.5rem; border-radius: 12px; margin: 1rem 0; border-left: 4px solid #EC4899;">
                    <h3 style="color: #EC4899; margin-top: 0;">🎯 L3 Analysis - Deep Root Cause & Recommendations</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Display stats and diagram
                display_l3_stats_and_diagram(st.session_state.bundle_data, st.session_state.analysis_results['L3'])
                
                st.markdown("---")
                st.markdown("**Detailed Analysis:**")
                st.markdown(f"""
                <div style="background: rgba(236, 72, 153, 0.03); padding: 1.5rem; border-radius: 8px; 
                            border: 1px solid rgba(236, 72, 153, 0.15); margin-bottom: 2rem; color: #1E293B;">
                    {st.session_state.analysis_results['L3']}
                </div>
                """, unsafe_allow_html=True)
            
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


if __name__ == "__main__":
    main()
