"""
📈 KOTAK NEO API ENGINE - Live Stock Data Integration
Fetches real-time stock prices, market depth, and order book data
"""

import time
import threading
import hashlib
from datetime import datetime
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
import streamlit as st

# Try importing neo_api_client
try:
    from neo_api_client import NeoAPI
    NEO_AVAILABLE = True
except ImportError:
    NEO_AVAILABLE = False
    print("⚠️ neo_api_client not installed. Run: pip install neo_api_client")

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False


@dataclass
class StockQuote:
    """Real-time stock quote data."""
    symbol: str
    ltp: float  # Last Traded Price
    change: float  # Change from previous close
    change_pct: float  # Percentage change
    volume: int
    high: float
    low: float
    open_price: float
    prev_close: float
    timestamp: str
    bid: float = 0.0
    ask: float = 0.0
    
    @property
    def is_bullish(self) -> bool:
        return self.change >= 0
    
    @property
    def color(self) -> str:
        return "#00ff88" if self.is_bullish else "#ff4444"


@dataclass 
class MarketSummary:
    """Overall market summary."""
    nifty_50: float = 0.0
    nifty_change: float = 0.0
    sensex: float = 0.0
    sensex_change: float = 0.0
    market_status: str = "Closed"
    last_updated: str = ""


class KotakNeoEngine:
    """
    Kotak Neo API integration for live stock data.
    Handles authentication, quote fetching, and real-time updates.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.client: Optional[NeoAPI] = None
        self.is_connected = False
        self.quotes: Dict[str, StockQuote] = {}
        self.market_summary = MarketSummary()
        self._polling_thread: Optional[threading.Thread] = None
        self._running = False
        self._callbacks: List[Callable] = []
        
    def _generate_totp(self) -> str:
        """Generate TOTP for 2FA authentication."""
        if not PYOTP_AVAILABLE:
            raise ImportError("pyotp not installed. Run: pip install pyotp")
        
        totp_secret = self.config.get("totp_secret", "")
        if not totp_secret:
            raise ValueError("TOTP secret not configured")
        
        totp = pyotp.TOTP(totp_secret)
        return totp.now()
    
    def connect(self) -> bool:
        """
        Connect to Kotak Neo API with authentication.
        Returns True if successful.
        """
        if not NEO_AVAILABLE:
            print("❌ neo_api_client not available")
            return False
        
        try:
            # Initialize client
            self.client = NeoAPI(
                consumer_key=self.config.get("consumer_key"),
                consumer_secret=self.config.get("consumer_secret"),
                environment="prod"
            )
            
            # Generate OTP and login
            totp = self._generate_totp()
            
            # Session login
            self.client.login(
                mobilenumber=self.config.get("mobile_number"),
                password=self.config.get("password")
            )
            
            # 2FA with TOTP
            self.client.session_2fa(OTP=totp)
            
            self.is_connected = True
            print("✅ Connected to Kotak Neo API")
            return True
            
        except Exception as e:
            print(f"❌ Kotak Neo connection failed: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the API."""
        self._running = False
        if self._polling_thread:
            self._polling_thread.join(timeout=2)
        self.is_connected = False
        self.client = None
    
    def get_quote(self, symbol: str, exchange: str = "NSE") -> Optional[StockQuote]:
        """
        Fetch real-time quote for a single stock.
        """
        if not self.is_connected or not self.client:
            return None
        
        try:
            # Get quote from API
            response = self.client.quotes(
                instrument_tokens=[{"instrument_token": symbol, "exchange_segment": exchange}]
            )
            
            if response and 'data' in response:
                data = response['data'][0]
                
                ltp = float(data.get('ltp', 0))
                prev_close = float(data.get('prev_close', ltp))
                change = ltp - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0
                
                quote = StockQuote(
                    symbol=symbol,
                    ltp=ltp,
                    change=change,
                    change_pct=change_pct,
                    volume=int(data.get('volume', 0)),
                    high=float(data.get('high', 0)),
                    low=float(data.get('low', 0)),
                    open_price=float(data.get('open', 0)),
                    prev_close=prev_close,
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    bid=float(data.get('bid', 0)),
                    ask=float(data.get('ask', 0))
                )
                
                self.quotes[symbol] = quote
                return quote
                
        except Exception as e:
            print(f"⚠️ Error fetching quote for {symbol}: {e}")
        
        return None
    
    def get_multiple_quotes(self, symbols: List[str], exchange: str = "NSE") -> Dict[str, StockQuote]:
        """Fetch quotes for multiple stocks at once."""
        quotes = {}
        
        if not self.is_connected or not self.client:
            return quotes
        
        try:
            tokens = [{"instrument_token": s, "exchange_segment": exchange} for s in symbols]
            response = self.client.quotes(instrument_tokens=tokens)
            
            if response and 'data' in response:
                for data in response['data']:
                    symbol = data.get('trading_symbol', '')
                    ltp = float(data.get('ltp', 0))
                    prev_close = float(data.get('prev_close', ltp))
                    change = ltp - prev_close
                    change_pct = (change / prev_close * 100) if prev_close else 0
                    
                    quote = StockQuote(
                        symbol=symbol,
                        ltp=ltp,
                        change=change,
                        change_pct=change_pct,
                        volume=int(data.get('volume', 0)),
                        high=float(data.get('high', 0)),
                        low=float(data.get('low', 0)),
                        open_price=float(data.get('open', 0)),
                        prev_close=prev_close,
                        timestamp=datetime.now().strftime("%H:%M:%S"),
                        bid=float(data.get('bid', 0)),
                        ask=float(data.get('ask', 0))
                    )
                    
                    quotes[symbol] = quote
                    self.quotes[symbol] = quote
                    
        except Exception as e:
            print(f"⚠️ Error fetching multiple quotes: {e}")
        
        return quotes
    
    def get_market_summary(self) -> MarketSummary:
        """Get NIFTY 50 and SENSEX summary."""
        if not self.is_connected:
            return self.market_summary
        
        try:
            # Fetch index data
            nifty = self.get_quote("NIFTY 50", "NSE_INDEX")
            sensex = self.get_quote("SENSEX", "BSE_INDEX")
            
            if nifty:
                self.market_summary.nifty_50 = nifty.ltp
                self.market_summary.nifty_change = nifty.change_pct
            
            if sensex:
                self.market_summary.sensex = sensex.ltp
                self.market_summary.sensex_change = sensex.change_pct
            
            self.market_summary.market_status = "Open" if self._is_market_open() else "Closed"
            self.market_summary.last_updated = datetime.now().strftime("%H:%M:%S")
            
        except Exception as e:
            print(f"⚠️ Error fetching market summary: {e}")
        
        return self.market_summary
    
    def _is_market_open(self) -> bool:
        """Check if market is currently open."""
        now = datetime.now()
        
        # Weekend check
        if now.weekday() >= 5:
            return False
        
        # Market hours: 9:15 AM to 3:30 PM IST
        market_open = now.replace(hour=9, minute=15, second=0)
        market_close = now.replace(hour=15, minute=30, second=0)
        
        return market_open <= now <= market_close
    
    def start_polling(self, symbols: List[str], interval: int = 5, callback: Callable = None):
        """
        Start background polling for stock quotes.
        
        Args:
            symbols: List of stock symbols to poll
            interval: Polling interval in seconds
            callback: Optional callback function when quotes update
        """
        if callback:
            self._callbacks.append(callback)
        
        def poll_loop():
            while self._running:
                try:
                    self.get_multiple_quotes(symbols)
                    self.get_market_summary()
                    
                    for cb in self._callbacks:
                        try:
                            cb(self.quotes)
                        except:
                            pass
                            
                except Exception as e:
                    print(f"⚠️ Polling error: {e}")
                
                time.sleep(interval)
        
        self._running = True
        self._polling_thread = threading.Thread(target=poll_loop, daemon=True)
        self._polling_thread.start()
    
    def stop_polling(self):
        """Stop background polling."""
        self._running = False
        if self._polling_thread:
            self._polling_thread.join(timeout=2)


# =============================================================================
# MOCK DATA FOR DEMO MODE (When API not configured)
# =============================================================================

def get_mock_quotes(symbols: List[str]) -> Dict[str, StockQuote]:
    """Generate mock quotes for demo/testing."""
    import random
    
    quotes = {}
    
    for symbol in symbols:
        base_price = random.uniform(100, 5000)
        change_pct = random.uniform(-3, 3)
        change = base_price * change_pct / 100
        
        quotes[symbol] = StockQuote(
            symbol=symbol,
            ltp=round(base_price, 2),
            change=round(change, 2),
            change_pct=round(change_pct, 2),
            volume=random.randint(100000, 10000000),
            high=round(base_price * 1.02, 2),
            low=round(base_price * 0.98, 2),
            open_price=round(base_price - change/2, 2),
            prev_close=round(base_price - change, 2),
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
    
    return quotes


def get_mock_market_summary() -> MarketSummary:
    """Generate mock market summary."""
    import random
    
    return MarketSummary(
        nifty_50=round(random.uniform(22000, 23000), 2),
        nifty_change=round(random.uniform(-1, 1), 2),
        sensex=round(random.uniform(72000, 75000), 2),
        sensex_change=round(random.uniform(-1, 1), 2),
        market_status="Pre-Open",
        last_updated=datetime.now().strftime("%H:%M:%S")
    )
