"""
Configuration loader for watchtower.py
Loads settings from .env file using python-dotenv
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Notion Configuration
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
RELEASES_DATABASE_ID = os.getenv("RELEASES_DATABASE_ID")  # For release notes

# TMDb API Configuration
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
REGION = os.getenv("TMDB_REGION", "US")

# SMS/Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMS_RECIPIENTS = os.getenv("SMS_RECIPIENTS")
SMS_SEND_MODE = os.getenv("SMS_SEND_MODE", "individual")  # 'group' or 'individual'

# Digest Configuration
DIGEST_PAGE_TITLE = os.getenv("DIGEST_PAGE_TITLE", "📩 DAILY DIGEST")

# Notification Preferences
def str_to_bool(value):
    """Convert string to boolean"""
    if value is None:
        return True
    return value.lower() in ('true', '1', 'yes', 'on')


NOTIFICATIONS = {
    "new_episode_any_show": False, 
    "episode_airing_today": True,
    "season_finale": True,
    "bulk_season_drop": True,
    "returning_soon": True,
    "long_gap": True,
    "multiple_episodes_tonight": True,
}

# Validation - check required settings
def validate_config():
    """Validate that required configuration is present"""
    required = {
        "NOTION_TOKEN": NOTION_TOKEN,
        "DATABASE_ID": DATABASE_ID,
        "TMDB_API_KEY": TMDB_API_KEY,
    }
    
    missing = [key for key, value in required.items() if not value]
    
    if missing:
        print("❌ ERROR: Missing required configuration!")
        print(f"   Missing: {', '.join(missing)}")
        print("\n   Please check your .env file.")
        print("   Copy .env.example to .env and fill in your credentials.")
        exit(1)

# Run validation on import
validate_config()