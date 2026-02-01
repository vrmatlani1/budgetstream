"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🇮🇳 BUDGETSTREAM - CONFIGURATION FILE                                        ║
║  Edit this file to configure your live stream and API settings               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# =============================================================================
# 📺 YOUTUBE LIVE STREAM CONFIGURATION
# =============================================================================
# Paste your live YouTube URL here before starting the app
# Examples:
#   - Sansad TV: https://www.youtube.com/watch?v=XXXXXX
#   - DD News: https://www.youtube.com/watch?v=YYYYYY
#   - NDTV: https://www.youtube.com/watch?v=ZZZZZZ

YOUTUBE_LIVE_URL = "https://www.youtube.com/watch?v=VIDEO_ID_HERE"

# =============================================================================
# 🔑 API KEYS (Can also be set in .streamlit/secrets.toml)
# =============================================================================
# If you prefer to set keys here instead of secrets.toml, uncomment and fill:

# DEEPGRAM_API_KEY = "your_deepgram_api_key"
# GROQ_API_KEY = "your_groq_api_key"
# OPENAI_API_KEY = "your_openai_api_key"  # Fallback

# =============================================================================
# 📊 KOTAK NEO API CONFIGURATION
# =============================================================================
# Fill in your Kotak Neo credentials for live stock data

KOTAK_NEO_CONFIG = {
    "consumer_key": "YOUR_CONSUMER_KEY",
    "consumer_secret": "YOUR_CONSUMER_SECRET",
    "access_token": "YOUR_ACCESS_TOKEN",
    "neo_fin_key": "YOUR_NEO_FIN_KEY",
    "totp_secret": "YOUR_TOTP_SECRET",  # For 2FA
    "mpin": "YOUR_MPIN",
    "mobile_number": "YOUR_MOBILE",
    "password": "YOUR_PASSWORD",
}

# =============================================================================
# ⚙️ APP SETTINGS
# =============================================================================

# Auto-start live stream when app loads (set to True for budget day)
AUTO_START_STREAM = False

# Transcript analysis settings
SENTENCES_PER_ANALYSIS = 2  # How many sentences to buffer before AI analysis

# Stock data refresh interval (seconds)
STOCK_REFRESH_INTERVAL = 5

# Watchlist - Stocks to track closely during budget
WATCHLIST_STOCKS = [
    "IRCTC", "RVNL", "IRFC",      # Railways
    "HAL", "BEL", "BHEL",          # Defence
    "TATASTEEL", "HINDALCO",       # Metals
    "TATAPOWER", "ADANIGREEN",     # Green Energy
    "HDFCBANK", "SBIN", "ICICIBANK", # Banking
    "TCS", "INFY",                 # IT
    "RELIANCE", "LT",              # Infrastructure
]
