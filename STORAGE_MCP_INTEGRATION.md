# Storage MCP Tools Integration

## Overview
The RCA Analysis Agent has been enhanced with Storage MCP (Model Context Protocol) tools to provide comprehensive storage and infrastructure analysis alongside Kubernetes incident analysis.

## What's New

### 1. Storage Metrics Collection
- **Disk Capacity**: Real-time disk usage monitoring
- **IOPS**: Input/Output Operations Per Second tracking
- **Latency**: Read/write latency measurements
- **Disk Health**: Overall health scoring (0-100)
- **Partitions**: Disk partition information
- **Swap Usage**: Swap space monitoring
- **Inode Usage**: File system inode tracking
- **Top I/O Processes**: Processes with highest disk I/O activity
- **Storage Trends**: Historical storage usage patterns
- **Cleanup Recommendations**: Automated cleanup suggestions

### 2. Kubernetes Metrics Collection
- **Cluster Health**: Overall cluster status
- **Pod Status**: Real-time pod information
- **Node Status**: Node health and capacity
- **Events**: Kubernetes event stream
- **Resource Usage**: CPU and memory metrics (requires metrics-server)

### 3. Enhanced Analysis Levels

#### L1 Analysis (Incident Triage)
- Now includes storage metrics context
- Correlates storage issues with application symptoms
- Identifies storage-related infrastructure problems

#### L2 Analysis (Correlation)
- Correlates storage performance with pod failures
- Identifies storage bottlenecks affecting services
- Links I/O issues to application errors

#### L3 Analysis (Root Cause)
- Deep storage infrastructure analysis
- Storage-related root cause identification
- Storage-specific fix recommendations
- Preventive storage monitoring suggestions

### 4. UI Enhancements
- **Storage Metrics Panel**: Live storage metrics display in bundle summary
- **Kubernetes Cluster Health**: Real-time cluster status
- **Storage Health Indicators**: Visual metrics in L1 analysis
- **Storage RCA Summary**: Integrated storage root cause analysis

## Installation

1. Install additional dependencies:
```bash
cd "RCA analysis agent/RCA analysis agent"
pip install -r requirements.txt
```

2. The storage MCP tools are automatically available in the `mcp_storage/tools/` directory.

## Usage

### Automatic Integration
Storage metrics are automatically collected and included in all analysis levels when:
- Storage MCP tools are available
- The application is running on a system with storage access

### Manual Collection
Storage metrics can be viewed in the "Storage Metrics (Live)" expander after uploading an RCA bundle.

## Features

### Storage RCA Generation
The system automatically generates a comprehensive Storage RCA that includes:
- Capacity analysis
- Performance metrics (IOPS, latency)
- Health scoring
- Issue identification
- Recommendations

### Kubernetes Integration
- Real-time pod status
- Cluster health monitoring
- Event correlation
- Resource usage tracking

## Benefits

1. **Comprehensive Analysis**: Storage issues are now part of the RCA process
2. **Proactive Detection**: Storage problems are identified before they cause failures
3. **Better Correlation**: Links storage performance to application issues
4. **Actionable Insights**: Provides specific storage-related recommendations
5. **Real-time Monitoring**: Live metrics during analysis

## Example Use Cases

1. **Disk Full Issues**: Automatically detects and correlates disk capacity issues with pod failures
2. **I/O Bottlenecks**: Identifies high I/O processes causing performance degradation
3. **Storage Latency**: Correlates slow storage with application timeouts
4. **Cluster Health**: Monitors overall Kubernetes cluster status during incident analysis

## Technical Details

### Tools Location
- Storage tools: `mcp_storage/tools/`
- Integration: Automatic via import system
- Error handling: Graceful degradation if tools unavailable

### Dependencies
- `psutil>=5.9.0`: System and process utilities
- `kubernetes>=28.1.0`: Kubernetes API client

### Platform Support
- **Linux**: Full support for all tools
- **macOS**: Most tools supported (some I/O metrics limited)
- **Windows**: Basic support (some features may be limited)

## Troubleshooting

### Tools Not Available
If you see "Storage MCP tools not available":
1. Check that `psutil` and `kubernetes` are installed
2. Verify the `mcp_storage/tools/` directory exists
3. Check Python path configuration

### Metrics Collection Errors
- Storage metrics may fail on some platforms (e.g., macOS I/O counters)
- Kubernetes metrics require cluster access (kubeconfig or in-cluster)
- Metrics-server is optional but recommended for resource usage

## Future Enhancements

Potential future improvements:
- Storage trend visualization
- Historical storage analysis
- Automated storage alerts
- Storage capacity planning
- Multi-node storage analysis
