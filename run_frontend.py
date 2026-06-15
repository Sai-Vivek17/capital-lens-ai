"""Run the CapitalLens AI Streamlit frontend."""

from __future__ import annotations

import subprocess
import sys


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", "frontend/streamlit_app.py"]))

