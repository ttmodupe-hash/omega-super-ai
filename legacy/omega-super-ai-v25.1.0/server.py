"""Simple entry point for uvicorn.

Usage:
    uvicorn server:app --host 0.0.0.0 --port 8000
"""

import sys
from pathlib import Path

# Add project root to path
project_dir = Path(__file__).parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

from backend.router import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
