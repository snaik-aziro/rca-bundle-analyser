# RCA Bundle Analyser

A Streamlit application for performing multi-level Root Cause Analysis (RCA) on Kubernetes incident bundles using Google Gemini AI.

## Features

- **L1 Analysis**: Quick incident triage - identifies symptoms, affected components, severity, and time window with structured JSON output
- **L2 Analysis**: Correlation analysis across pods, nodes, and services - identifies failing components and probable root cause
- **L3 Analysis**: Deep root cause analysis with exact cause identification, fixes, and preventive measures
- **Interactive Visualizations**: High-level statistics and diagrams for each analysis level
- **Modern UI**: Gen Z + professional light color scheme with beautiful visualizations

## Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Google Gemini API key:
Create a `.env` file in the project root:
```bash
GEMINI_API_KEY=your-gemini-api-key-here
```

## Usage

1. Start the Streamlit app:
```bash
streamlit run app.py --server.port 8501
```

2. Upload an RCA bundle (tar.gz file) using the upload button

3. Run analysis:
   - Click "🔍 Run L1 Analysis" for incident triage with structured JSON output
   - Click "🔬 Run L2 Analysis" for correlation analysis
   - Click "🎯 Run L3 Analysis" for deep root cause analysis

4. View results:
   - High-level statistics and metrics
   - Interactive diagrams and visualizations
   - Detailed breakdown of symptoms, affected components, and observations
   - Structured JSON data view
   - Full text analysis

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
- Severity assessment (Critical/High/Medium/Low)
- Time window of incident
- Initial observations
- Structured JSON output with all findings
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
- Google Gemini API key (for AI-powered analysis)
- Streamlit
- PyYAML
- Plotly (for visualizations)
- Pandas (for data processing)
- python-dotenv (for environment variable management)

## Technology Stack

- **Frontend**: Streamlit with custom CSS styling
- **AI Model**: Google Gemini 2.0 Flash
- **Visualization**: Plotly for interactive charts
- **Data Processing**: Pandas

## Notes

- The application uses Google Gemini 2.0 Flash for analysis
- Large bundles may take time to process
- Results are cached in session state
- Analysis can be run independently for each level
- Structured JSON output is available for L1 analysis
- All sensitive data (API keys) should be stored in `.env` file (not committed to git)
