#!/usr/bin/env python
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on http://127.0.0.1:{port}")
    print(f"Documentation at http://127.0.0.1:{port}/docs")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
