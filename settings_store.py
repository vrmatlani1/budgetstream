"""
📊 SETTINGS STORE - Persistent settings with real-time updates
Manages all dynamic configuration: APIs, YouTube URL, theme, etc.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import streamlit as st

SETTINGS_FILE = Path(__file__).parent / "settings.json"

DEFAULT_SETTINGS = {
    "youtube_url": "",
    "theme": "dark",  # "light" or "dark"
    "auto_start": False,
    "deepgram_api_key": "",
    "groq_api_key": "",
    "openai_api_key": "",
    "kotak_consumer_key": "",
    "kotak_mobile": "",
    "kotak_ucc": "",
    "kotak_mpin": "",
    "kotak_totp": "",  # User enters this each session
    "kotak_session_token": "",
    "kotak_connected": False,
    "last_updated": "",
}


def load_settings() -> dict:
    """Load settings from file, merging with defaults."""
    settings = DEFAULT_SETTINGS.copy()
    
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                settings.update(saved)
        except:
            pass
    
    # Also load from secrets.toml if available
    try:
        if st.secrets.get("deepgram", {}).get("api_key"):
            settings["deepgram_api_key"] = st.secrets["deepgram"]["api_key"]
        if st.secrets.get("groq", {}).get("api_key"):
            settings["groq_api_key"] = st.secrets["groq"]["api_key"]
        if st.secrets.get("openai", {}).get("api_key"):
            settings["openai_api_key"] = st.secrets["openai"]["api_key"]
        if st.secrets.get("kotak", {}):
            kotak = st.secrets["kotak"]
            settings["kotak_consumer_key"] = kotak.get("consumer_key", "")
            settings["kotak_mobile"] = kotak.get("mobile", "")
            settings["kotak_ucc"] = kotak.get("ucc", "")
            settings["kotak_mpin"] = kotak.get("mpin", "")
    except:
        pass
    
    return settings


def save_settings(settings: dict):
    """Save settings to file."""
    settings["last_updated"] = datetime.now().isoformat()
    
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_setting(key: str, default: Any = None) -> Any:
    """Get a single setting value."""
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value: Any):
    """Set a single setting value."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def get_theme() -> str:
    """Get current theme setting."""
    return get_setting("theme", "dark")


def set_theme(theme: str):
    """Set theme (light/dark)."""
    set_setting("theme", theme)


def get_youtube_url() -> str:
    """Get configured YouTube URL."""
    return get_setting("youtube_url", "")


def set_youtube_url(url: str):
    """Set YouTube URL."""
    set_setting("youtube_url", url)


def is_api_configured(api_name: str) -> bool:
    """Check if an API is configured."""
    key_map = {
        "deepgram": "deepgram_api_key",
        "groq": "groq_api_key",
        "openai": "openai_api_key",
        "kotak": "kotak_consumer_key",
    }
    key = get_setting(key_map.get(api_name, ""), "")
    return bool(key and len(key) > 10)
