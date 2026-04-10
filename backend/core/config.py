import os

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploaded_datasets")
CHART_PATH = os.getenv("CHART_PATH", "output_chart.png")
MAX_RETRIES = 3

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CHART_PATH) if os.path.dirname(CHART_PATH) else ".", exist_ok=True)