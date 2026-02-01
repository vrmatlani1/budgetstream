import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os
import time
from typing import Optional, Dict
from openai import OpenAI
import threading

# --- CONFIGURATION ---
DB_FILE = "budget_stream.db"
SETTINGS_FILE = "settings.json"

st.set_page_config(
    page_title="BudgetStream - 2026",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📊"
)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS transcript (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 text TEXT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS insights (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 ticker TEXT,
                 sentiment TEXT,
                 reason TEXT,
                 sector TEXT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                 )''')
    conn.commit()
    conn.close()

def save_transcript(text: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO transcript (text) VALUES (?)", (text,))
    conn.commit()
    conn.close()

def save_insight(ticker: str, sentiment: str, reason: str, sector: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO insights (ticker, sentiment, reason, sector) VALUES (?, ?, ?, ?)", 
              (ticker, sentiment, reason, sector))
    conn.commit()
    conn.close()

def get_transcripts(limit: int = 20):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(f"SELECT * FROM transcript ORDER BY id DESC LIMIT {limit}", conn)
    conn.close()
    return df

def get_insights(limit: int = 50):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(f"SELECT * FROM insights ORDER BY id DESC LIMIT {limit}", conn)
    conn.close()
    return df

# --- SETTINGS & API ---
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

SETTINGS = load_settings()
# Try settings.json -> env var -> st.secrets
OPENAI_API_KEY = SETTINGS.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        OPENAI_API_KEY = st.secrets["openai"]["api_key"]
    except:
        pass

def get_video_id():
    url = SETTINGS.get("youtube_url", "https://www.youtube.com/watch?v=gCdw_uAaXzs")
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return "gCdw_uAaXzs"

# --- PRICE ENGINE (Subprocess Safe) ---
class PriceEngine:
    @staticmethod
    def get_latest_price(ticker: str) -> str:
        try:
            # Append .NS for NSE
            yf_ticker = f"{ticker}.NS" if not ticker.endswith(('.NS', '.BO')) else ticker
            
            import subprocess
            import sys
            # Use sys.executable to ensure we use the same python environment
            result = subprocess.run(
                [sys.executable, "price_fetcher.py", yf_ticker], 
                capture_output=True, text=True, timeout=5
            )
            output = result.stdout.strip()
            # Handle potential warning lines in output (take last line)
            if output:
                lines = output.splitlines()
                last_line = lines[-1]
                if "|" in last_line and "NaN" not in last_line:
                    vals = last_line.split("|")
                    return f"₹{float(vals[0]):,.2f}"
        except:
            pass
        return "Unavailable"

    @staticmethod
    def get_market_indices():
        indices = {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN"}
        results = {}
        for name, ticker in indices.items():
            try:
                import subprocess
                import sys
                import random
                # Add random arg to ensure no OS-level caching if any (though unlikely for subprocess)
                result = subprocess.run(
                    [sys.executable, "price_fetcher.py", ticker], 
                    capture_output=True, text=True, timeout=8
                )
                output = result.stdout.strip()
                if output:
                    lines = output.splitlines()
                    last_line = lines[-1]
                    if "|" in last_line and "NaN" not in last_line:
                        vals = last_line.split("|")
                        val = float(vals[0])
                        prev = float(vals[1])
                        change = val - prev
                        pct = (change / prev) * 100
                        results[name] = {"price": val, "change": change, "pct": pct}
                    else:
                        # Fallback if parse fails but keeping structure
                         results[name] = {"price": 0.0, "change": 0.0, "pct": 0.0}
                else:
                    results[name] = {"price": 0.0, "change": 0.0, "pct": 0.0}
            except Exception as e:
                print(f"Error fetching {name}: {e}")
                results[name] = {"price": 0.0, "change": 0.0, "pct": 0.0}
        return results

# --- ANALYTICS ---
def analyze_text(text: str):
    if not OPENAI_API_KEY:
        st.error("OpenAI API Key missing.")
        return

    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
    Analyze text for Indian stock market impacts.
    Text: "{text}"
    Return JSON: {{ "insights": [ {{ "ticker": "RELIANCE", "sentiment": "BULLISH", "reason": "Reason", "sector": "Sector" }} ] }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "You are a financial analyst."},
                      {"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        for item in data.get("insights", []):
            save_insight(item['ticker'], item['sentiment'], item['reason'], item['sector'])
    except Exception as e:
        st.error(f"AI: {e}")

# --- UI RENDERERS ---

def render_admin():
    """Secure Admin Panel"""
    st.markdown("### 🔒 Budget Stream Console")
    
    # Simple Auth State
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    if not st.session_state.is_admin:
        with st.form("auth"):
            uid = st.text_input("User ID")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Enter Console"):
                # Use secrets for auth
                valid_uid = st.secrets["admin"]["username"]
                valid_pwd = st.secrets["admin"]["password"]
                
                if uid == valid_uid and pwd == valid_pwd:
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Access Denied")
        return

    # Authenticated View
    st.success("Authenticated as Administrator")
    with st.form("broadcast"):
        text = st.text_area("Live Speech Transcript", height=150)
        if st.form_submit_button("Broadcast & Analyze"):
            save_transcript(text)
            with st.spinner("AI Analyzing..."):
                analyze_text(text)
            st.success("Sent to Viewer!")

    st.subheader("History")
    st.dataframe(get_transcripts(), use_container_width=True)


def render_viewer():
    """Clean Viewer UI"""
    
    
    # 1. Header (Indices) - Wrapped in Fragment for Auto-Refresh
    @st.fragment(run_every=5)
    def render_header():
        indices = PriceEngine.get_market_indices()
        
        # Custom Header
        st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 20px; border-bottom: 1px solid #eee;">
                <div>
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <h1 style="margin: 0; padding: 0; color: #1a73e8;">BudgetStream - 2026</h1>
                        <div style="
                            background-color: #ff4444; 
                            color: white; 
                            padding: 5px 10px; 
                            border-radius: 4px; 
                            font-weight: bold; 
                            font-size: 0.8em; 
                            animation: pulse 2s infinite;
                            box-shadow: 0 0 10px rgba(255,68,68,0.5);
                        ">
                            ● LIVE
                        </div>
                    </div>
                    <div style="margin-top: 5px; font-size: 0.9em; color: #555;">
                        Developed By <a href="https://linkedin.com/in/varunmatlani" target="_blank" style="color: #1a73e8; text-decoration: none; font-weight: bold;">Varun Matlani</a>
                    </div>
                </div>
                <style>
                    @keyframes pulse {
                        0% { opacity: 1; transform: scale(1); }
                        50% { opacity: 0.8; transform: scale(1.05); }
                        100% { opacity: 1; transform: scale(1); }
                    }
                </style>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([5, 2, 2])
        with col1:
            pass # Spacer
        with col2:
            nifty = indices["NIFTY 50"]
            st.metric("NIFTY 50", f"₹{nifty['price']:,.0f}", f"{nifty['pct']:.2f}%")
        with col3:
            sensex = indices["SENSEX"]
            st.metric("SENSEX", f"₹{sensex['price']:,.0f}", f"{sensex['pct']:.2f}%")
        
        st.divider()

    render_header()

    # 2. Ticker Tape (Simple HTML)
    # Using a simple marquee for safety and robustness
    insights = get_insights(limit=10)
    ticker_text = ""
    for _, row in insights.iterrows():
        # Get live price
        price = PriceEngine.get_latest_price(row['ticker'])
        symbol = "🟢" if "BULL" in row['sentiment'].upper() else "🔴"
        ticker_text += f"{symbol} {row['ticker']} ({price}) &nbsp;&nbsp;&nbsp; "
    
    if ticker_text:
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 25px; white-space: nowrap; overflow: hidden; border: 1px solid #eee;">
            <marquee scrollamount="12" style="font-weight: bold; font-family: 'Roboto Mono', monospace; font-size: 1.1em; color: #333;">{ticker_text}</marquee>
        </div>
        """, unsafe_allow_html=True)


    # 3. Main Layout
    c_left, c_mid, c_right = st.columns([1, 1, 1])

    with c_left:
        st.subheader("📜 Transcript")
        @st.fragment(run_every=2)
        def view_transcript():
            df = get_transcripts(limit=10)
            for _, row in df.iterrows():
                st.markdown(f"**{row['timestamp'][11:16]}**")
                st.caption(row['text'])
                st.markdown("---")
        view_transcript()

    with c_mid:
        st.subheader("⚡ AI Insights")
        @st.fragment(run_every=2)
        def view_insights():
            df = get_insights(limit=10)
            for _, row in df.iterrows():
                # Color logic
                is_bull = "BULL" in row['sentiment'].upper()
                color = "green" if is_bull else "red"
                bg = "#e6ffe6" if is_bull else "#ffe6e6"
                price = PriceEngine.get_latest_price(row['ticker'])
                
                html = f"""
                <div style="background-color: {bg}; border-left: 5px solid {color}; padding: 10px; margin-bottom: 10px; border-radius: 5px; color: black;">
                    <div style="display:flex; justify-content: space-between;">
                        <span style="font-weight:bold; font-size: 1.1em;">{row['ticker']}</span>
                        <span style="font-weight:bold; font-family:monospace;">{price}</span>
                    </div>
                    <div style="font-size: 0.9em; margin-top: 5px;">{row['reason']}</div>
                    <div style="font-size: 0.8em; color: #555; margin-top: 5px;">{row['sector']}</div>
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)
        view_insights()

    with c_right:
        st.subheader("📺 Live Feed")
        vid_id = get_video_id()
        st.components.v1.iframe(f"https://www.youtube.com/embed/{vid_id}?autoplay=1", height=250)

    # 4. Footer
    st.divider()
    st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.8em; padding: 20px;">
            (C) Varun Matlani | These are not stock recommendations, and mere analysis of impact, being provided without any direct/indirect consideration.
        </div>
    """, unsafe_allow_html=True)


# --- MAIN ---
def main():
    init_db()
    
    with st.sidebar:
        st.title("Navigation")
        page = st.radio("Mode", ["Viewer", "Admin"])
    
    if page == "Admin":
        render_admin()
    else:
        render_viewer()

if __name__ == "__main__":
    main()
