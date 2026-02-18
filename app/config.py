import os
from dotenv import load_dotenv

load_dotenv()

# App config (127.0.0.1 for localhost, 0.0.0.0 for whole network)
APP_NAME = os.getenv("APP_NAME", "A2A registry")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = os.getenv("APP_PORT", 8000)

# Logging
DEBUG = bool(os.getenv("DEBUG", "False").lower() == "true")

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# A2A clients health check
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
MAX_FAILURES = int(os.getenv("MAX_FAILURES", "3"))
