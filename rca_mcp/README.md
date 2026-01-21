# RCA MCP Tools

MCP (Model Context Protocol) server providing tools for extracting important data and statistics from RCA (Root Cause Analysis) logs.

## Overview

The `rca_mcp` server provides specialized tools for analyzing RCA log bundles, extracting statistics, identifying patterns, and generating insights from log files.

## Tools

### 1. Error Statistics (`get_error_statistics`)
Extracts error statistics from `errors.json`:
- Total error count
- Errors by category and service
- Error severity distribution
- Top error messages
- Error timeline

### 2. Timeline Statistics (`get_timeline_statistics`)
Analyzes timeline data from `timeline.json`:
- Total event count
- Events by service and log level
- Request distribution
- Timeline duration and event rate

### 3. Service Statistics (`get_service_statistics`)
Extracts statistics from service log files:
- Log entries per service
- Log level distribution
- Error counts per service
- Request counts
- Performance metrics (latency, duration, status codes)

### 4. Request Patterns (`get_request_patterns`)
Analyzes request patterns from logs:
- Request counts by service, endpoint, and method
- Request latency statistics
- Status code distribution
- Failed requests analysis
- Success rate calculation

### 5. Error Patterns (`analyze_error_patterns`)
Analyzes error patterns and correlations:
- Error categories and clusters
- Error sequences
- Service error correlations
- Root cause candidates
- Error time distribution

### 6. Metadata Extractor (`extract_metadata`)
Extracts metadata from `metadata.txt`:
- Scenario type
- Collection timestamp
- Namespace information
- File and error counts

### 7. Log Analyzer (`analyze_logs`)
Comprehensive analysis combining all tools:
- Integrated analysis from all data sources
- Summary statistics and insights
- Cross-correlation of data

## Usage

### Direct Function Calls

```python
from rca_mcp.tools.error_stats import get_error_statistics
from rca_mcp.tools.timeline_stats import get_timeline_statistics
from rca_mcp.tools.service_stats import get_service_statistics
from rca_mcp.tools.request_patterns import get_request_patterns
from rca_mcp.tools.error_patterns import analyze_error_patterns
from rca_mcp.tools.metadata_extractor import extract_metadata
from rca_mcp.tools.log_analyzer import analyze_logs

# Path to RCA logs directory
logs_path = "/path/to/rca_logs_20251216T162338Z"

# Get error statistics
error_stats_json = get_error_statistics(logs_path)
error_stats = json.loads(error_stats_json)

# Get timeline statistics
timeline_stats_json = get_timeline_statistics(logs_path)
timeline_stats = json.loads(timeline_stats_json)

# Get service statistics
service_stats_json = get_service_statistics(logs_path)
service_stats = json.loads(service_stats_json)

# Analyze request patterns
request_patterns_json = get_request_patterns(logs_path)
request_patterns = json.loads(request_patterns_json)

# Analyze error patterns
error_patterns_json = analyze_error_patterns(logs_path)
error_patterns = json.loads(error_patterns_json)

# Extract metadata
metadata_json = extract_metadata(logs_path)
metadata = json.loads(metadata_json)

# Comprehensive analysis
analysis_json = analyze_logs(logs_path)
analysis = json.loads(analysis_json)
```

## Input Format

The tools expect an RCA logs directory containing:
- `errors.json` - Structured error data
- `timeline.json` - Timeline events data
- `metadata.txt` - Metadata in key=value format
- `service-*.log` - Service log files (e.g., `service-a-current.log`, `service-b.log`)
- `persistent-*.log` - Persistent log files

## Output Format

All tools return JSON strings with the following structure:

```json
{
  "status": "OK",
  "data_field_1": "...",
  "data_field_2": "...",
  ...
}
```

On error:
```json
{
  "error": "Error type",
  "message": "Error message",
  "logs_path": "/path/to/logs"
}
```

## Integration

To integrate with the RCA Analysis Agent app:

```python
# In app.py
try:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rca_mcp'))
    from tools.error_stats import get_error_statistics
    from tools.log_analyzer import analyze_logs
    RCA_TOOLS_AVAILABLE = True
except ImportError as e:
    RCA_TOOLS_AVAILABLE = False
```

## Example Use Cases

1. **Incident Triage**: Use `get_error_statistics` to quickly identify error volume and affected services
2. **Performance Analysis**: Use `get_request_patterns` to analyze latency and request patterns
3. **Root Cause Analysis**: Use `analyze_error_patterns` to identify error sequences and correlations
4. **Service Health**: Use `get_service_statistics` to assess individual service health
5. **Comprehensive Analysis**: Use `analyze_logs` for complete log bundle analysis

## Error Handling

All tools handle:
- Missing files gracefully
- JSON parsing errors
- File access errors
- Invalid data formats

Errors are returned as JSON with status information rather than raising exceptions.
