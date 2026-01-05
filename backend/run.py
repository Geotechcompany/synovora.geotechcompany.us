"""Quick start script for the LinkedIn automation app."""

import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

# Load .env file if it exists
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print("✅ Loaded environment variables from .env")
else:
    print("⚠️  Warning: .env file not found. Please create one from .env.example")
    print("   Some features may not work without proper configuration.")

# Check required environment variables
# Require either Gemini OR NVIDIA credentials
has_gemini = os.getenv("GEMINI_API_KEY")
has_nvidia = os.getenv("NVIDIA_API_KEY") and os.getenv("NVIDIA_BASE_URL")

if not (has_gemini or has_nvidia):
    print(f"\n❌ Missing required environment variables")
    print("   Please set GEMINI_API_KEY or (NVIDIA_API_KEY and NVIDIA_BASE_URL) in your .env file")
    sys.exit(1)

# Import and run the app
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"\n🚀 Starting LinkedIn Post Generator & Publisher")
    print(f"   Server: http://{host}:{port}")
    print(f"   Dashboard: http://localhost:{port}")
    print(f"\n   Press Ctrl+C to stop\n")
    
    # Use import string for reload to work properly
    uvicorn.run("app:app", host=host, port=port, reload=True)

