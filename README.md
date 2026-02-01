# 🇮🇳 BudgetStream - Live Budget 2026 Impact Engine

Real-time Speech-to-Stock-Ticker dashboard for the Indian Union Budget 2026.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![License](https://img.shields.io/badge/License-MIT-green)

## 🎯 What It Does

1. **Listens** to the Finance Minister's live speech (via YouTube)
2. **Transcribes** in real-time using Deepgram's Nova-2
3. **Analyzes** each statement for stock market impact using Groq/OpenAI
4. **Displays** affected sectors and NSE tickers with sentiment
5. **Shows** live social media sentiment from Reddit

**Target Latency:** Under 3 seconds from "FM speaks" to "Stock on Screen"

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd budgetstream
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit `.streamlit/secrets.toml` with your keys:

```toml
[deepgram]
api_key = "your_deepgram_key"  # Get from console.deepgram.com

[groq]
api_key = "your_groq_key"      # Get from console.groq.com

[openai]
api_key = "your_openai_key"    # Fallback, optional

[reddit]
client_id = "your_client_id"
client_secret = "your_secret"
user_agent = "BudgetStream/1.0"
```

### 3. Run the App

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`

## 🧪 Test Mode (Recommended First)

Before the live event, use **Test Mode** to verify everything works:

1. Select "🧪 Test Mode" in the sidebar
2. Paste sample budget text like:

   > "I am pleased to announce a capital expenditure of ₹11.11 lakh crore for infrastructure development, with a focus on highways and railways."

3. Click "🔍 Analyze Text"
4. Watch the Alpha Feed for detected impacts

### Sample Test Statements

```
"The government will provide ₹25,000 crore for semiconductor manufacturing incentives."

"Defence budget increased by 13% to ₹6.21 lakh crore, focusing on indigenous production."

"Tax exemption limit for individual taxpayers raised to ₹12 lakh under new regime."

"Green energy receives ₹35,000 crore allocation for solar and wind projects."
```

## 🔴 Live Mode

On **February 1, 2026 at 11:00 AM IST**:

1. Select "🔴 Live Mode" in the sidebar
2. Paste the Sansad TV YouTube URL
3. Click "▶️ Start"
4. Watch the magic happen!

**Recommended YouTube Sources:**
- [Sansad TV](https://www.youtube.com/@SansadTV) - Official Parliament channel
- [DD News](https://www.youtube.com/@DDNewsOfficial) - Government news
- [NDTV](https://www.youtube.com/@ndtv) - News coverage

## 📊 Understanding the Dashboard

### Layout

| Section | Purpose |
|---------|---------|
| **Header** | Shows live status + market sentiment score |
| **Status Bar** | AI provider, social connection, impact count |
| **Transcript (Left)** | Live speech text as it's transcribed |
| **Alpha Feed (Right)** | Stock impacts with tickers, sector, sentiment |

### Sentiment Meter

| Score | Emoji | Meaning |
|-------|-------|---------|
| 70+ | 🚀 | Very Bullish |
| 55-70 | 📈 | Bullish |
| 45-55 | 😐 | Neutral |
| 30-45 | 📉 | Bearish |
| <30 | 💀 | Very Bearish |

### Impact Cards

- **Green border** = Bullish sentiment
- **Red border** = Bearish sentiment
- **Tickers** = NSE symbols to watch
- **Reason** = 5-word summary of why

## 🔧 Troubleshooting

### "No AI Configured"
→ Check your API keys in `.streamlit/secrets.toml`

### Groq Rate Limited
→ App auto-switches to OpenAI - ensure fallback key is set

### YouTube Stream Not Working
→ Ensure `yt-dlp` and `ffmpeg` are installed:
```bash
brew install yt-dlp ffmpeg  # macOS
# or
pip install yt-dlp
```

### No Social Sentiment
→ Reddit API is optional; app works without it

## 📁 File Structure

```
budgetstream/
├── app.py              # Streamlit dashboard
├── data_engine.py      # Audio + AI processing
├── social_engine.py    # Reddit sentiment polling
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .streamlit/
    └── secrets.toml    # API keys (DO NOT COMMIT!)
```

## 🛡️ Security Notes

- **Never commit `secrets.toml`** to version control
- API keys have usage limits - monitor your dashboards
- Reddit API is read-only in this implementation

## 📄 License

MIT License - Use freely for the Budget 2026!

---

**Built with ❤️ for Indian traders and investors**

*Jai Hind! 🇮🇳*
