# settings.py
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

LOCATION_API_BASE = os.getenv("API_BASE", "https://timeline.osmosis.page/api/v1")
LOCATION_API_KEY = os.getenv("API_KEY")

OPENROUTER_API_BASE = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SITE_URL = os.getenv("SITE_URL", "https://mygame.example")

# Mission monitoring interval in seconds
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "60"))

