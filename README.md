# RCA Analysis Agent

A Streamlit application for performing multi-level Root Cause Analysis (RCA) on Kubernetes incident bundles.

## Features

- **L1 Analysis**: Quick incident triage - identifies symptoms, affected components, severity, and time window
- **L2 Analysis**: Correlation analysis across pods, nodes, and services - identifies failing components and probable root cause
- **L3 Analysis**: Deep root cause analysis with exact cause identification, fixes, and preventive measures

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up OpenAI API key (optional - can be set in the app):
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.streamlit/secrets.toml` file:
```toml
OPENAI_API_KEY = "your-api-key-here"
```

## Usage

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Upload an RCA bundle (tar.gz file) using the upload button

3. Run analysis:
   - Click "Run L1 Analysis" for incident triage
   - Click "Run L2 Analysis" for correlation analysis
   - Click "Run L3 Analysis" for deep root cause analysis

4. View results in the main panel

5. Download results as JSON if needed

## RCA Bundle Format

The application expects a tar.gz file containing:
- Application logs (`.log` files, `persistent-*` files)
- Kubernetes events (`k8s-events.yaml`)
- Pod status (`pods-list.txt`, `pod-*-describe.txt`)
- Deployment manifests (`deployment-*-describe.txt`)
- Error reports (`errors.json`)
- Timeline data (`timeline.json`)
- Metadata (`metadata.txt`)

## Analysis Levels

### L1: Incident Triage
- Quick identification of symptoms
- Affected components (pods, services, nodes)
- Severity assessment
- Time window of incident
- No root cause speculation

### L2: Correlation Analysis
- Correlates logs across pods, nodes, and services
- Identifies failing components and dependencies
- Analyzes pod lifecycle events (CrashLoopBackOff, OOM, NotReady)
- Identifies configuration or infrastructure issues
- Provides probable root cause statement

### L3: Deep Root Cause Analysis
- Identifies exact root cause (code, config, or design)
- Explains why existing checks or alerts failed
- Recommends permanent fixes (code, deployment, or infra)
- Suggests preventive monitoring and alerts
- Provides concise RCA summary

## Requirements

- Python 3.8+
- OpenAI API key (for AI-powered analysis)
- Streamlit
- PyYAML

## Notes

- The application uses GPT-4 for analysis
- Large bundles may take time to process
- Results are cached in session state
- Analysis can be run independently for each level

