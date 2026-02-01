"""
🎙️ LIVE TRANSCRIPTION ENGINE - Auto-starts with YouTube URL
Uses Deepgram for transcription, Groq/OpenAI for analysis
Works WITHOUT ffmpeg by using Deepgram URL transcription
"""

import subprocess
import threading
import time
import json
import os
import requests
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Callable, Dict
from queue import Queue
import tempfile


@dataclass
class StockImpact:
    """Stock impact from budget speech."""
    sector: str
    sentiment: str
    tickers: List[str]
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    confidence: float = 0.8


@dataclass 
class TranscriptChunk:
    """A chunk of transcribed text."""
    text: str
    timestamp: str
    is_final: bool = True


class AIAnalyzer:
    """Analyzes text for stock impacts using Groq/OpenAI."""
    
    SYSTEM_PROMPT = """You are an expert Indian financial analyst specializing in Union Budget analysis.

When given budget speech text, identify stock market impacts and return ONLY a valid JSON array.
Each impact should have:
- "sector": Affected sector (Railways, Defence, Banking, Infrastructure, Green Energy, IT, etc.)
- "sentiment": "Bullish" or "Bearish"
- "tickers": List of 2-4 NSE stock symbols
- "reason": Brief explanation (max 20 words)

If no clear market impact, return: []

Example: [{"sector": "Railways", "sentiment": "Bullish", "tickers": ["IRCTC", "RVNL"], "reason": "₹2.5L cr allocation"}]"""

    def __init__(self):
        self.groq_client = None
        self.openai_client = None
        self._init_clients()
    
    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key from settings."""
        try:
            from settings_store import get_setting
            key = get_setting(f"{provider}_api_key", "")
            if key and len(key) > 10:
                return key
        except:
            pass
        return None
    
    def _init_clients(self):
        """Initialize AI clients."""
        groq_key = self._get_api_key("groq")
        openai_key = self._get_api_key("openai")
        
        if groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_key)
                print("✅ Groq initialized")
            except Exception as e:
                print(f"❌ Groq error: {e}")
        
        if openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_key)
                print("✅ OpenAI initialized")
            except Exception as e:
                print(f"❌ OpenAI error: {e}")
    
    def get_status(self) -> str:
        if self.openai_client:
            return "✅ OpenAI"
        elif self.groq_client:
            return "✅ Groq"
        return "❌ No AI"
    
    def analyze(self, text: str) -> List[StockImpact]:
        """Analyze text for stock impacts."""
        if not text or len(text.strip()) < 30:
            return []
        
        # Try OpenAI first (User requested)
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.2,
                    max_tokens=400
                )
                return self._parse_response(response.choices[0].message.content)
            except Exception as e:
                print(f"OpenAI error: {e}")
        
        # Fallback to Groq
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.2,
                    max_tokens=400
                )
                return self._parse_response(response.choices[0].message.content)
            except Exception as e:
                print(f"Groq error: {e}")
        
        return []
    
    def _parse_response(self, content: str) -> List[StockImpact]:
        """Parse AI response into StockImpact objects."""
        try:
            content = content.strip()
            if "```" in content:
                content = content.split("```")[1].replace("json", "").strip()
            
            data = json.loads(content)
            if not isinstance(data, list):
                data = [data]
            
            return [
                StockImpact(
                    sector=item.get("sector", "Unknown"),
                    sentiment=item.get("sentiment", "Neutral"),
                    tickers=item.get("tickers", [])[:4],
                    reason=item.get("reason", "")[:100]
                )
                for item in data
                if all(k in item for k in ["sector", "sentiment", "tickers"])
            ]
        except:
            return []


class LiveTranscriber:
    """
    Transcribes YouTube live streams using Deepgram.
    Uses URL-based transcription - no ffmpeg required!
    """
    
    def __init__(self):
        self.is_running = False
        self.transcripts: List[str] = []
        self.transcript_queue: Queue = Queue()
        self._thread = None
        self._deepgram_key = None
        self._init_deepgram()
    
    def _init_deepgram(self):
        """Initialize Deepgram API key."""
        try:
            from settings_store import get_setting
            self._deepgram_key = get_setting("deepgram_api_key", "")
            if self._deepgram_key and len(self._deepgram_key) > 10:
                print(f"✅ Deepgram key loaded ({self._deepgram_key[:10]}...)")
            else:
                print("⚠️ No Deepgram API key configured")
                self._deepgram_key = None
        except Exception as e:
            print(f"❌ Deepgram key error: {e}")
            self._deepgram_key = None
    
    def get_status(self) -> str:
        if self.is_running:
            return "🔴 LIVE"
        elif self._deepgram_key:
            return "✅ Ready"
        return "❌ No API Key"
    
    def start(self, youtube_url: str):
        """Start transcription from YouTube URL."""
        if self.is_running:
            return
        
        if not self._deepgram_key:
            print("❌ No Deepgram API key")
            return
        
        self.is_running = True
        self._thread = threading.Thread(
            target=self._transcribe_loop, 
            args=(youtube_url,),
            daemon=True
        )
        self._thread.start()
        print(f"🎙️ Started transcription for: {youtube_url}")
    
    def stop(self):
        """Stop transcription."""
        self.is_running = False
    
    def get_new_transcripts(self) -> List[str]:
        """Get any new transcripts from the queue."""
        new = []
        while not self.transcript_queue.empty():
            try:
                new.append(self.transcript_queue.get_nowait())
            except:
                break
        return new
    
    def _transcribe_loop(self, youtube_url: str):
        """Main transcription loop wrapper."""
        # Directly call the streamlink-based transcriber with the YouTube URL
        try:
             self._transcribe_url(youtube_url)
        except Exception as e:
             print(f"❌ Loop wrapper error: {e}")
        finally:
             self.is_running = False
    
    def _transcribe_url(self, youtube_url: str):
        """
        Streamlink-based Loop: Connects to stream, reads chunks, transcribes.
        """
        print(f"📡 Connecting via Streamlink: {youtube_url}...")
        
        # Initialize OpenAI client 
        try:
            from openai import OpenAI
            from settings_store import get_setting
            api_key = get_setting("openai_api_key")
            if not api_key:
                print("❌ No OpenAI key found")
                return
            client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"❌ OpenAI init error: {e}")
            return

        import streamlink
        import time
        import os
        
        try:
            # 1. Get streams
            # Use 'best' to ensure we get a valid stream, or 'audio_only'
            session = streamlink.Streamlink()
            try:
                streams = session.streams(youtube_url)
            except Exception as sl_err:
                print(f"❌ Streamlink extraction failed: {sl_err}")
                return

            if not streams:
                print("❌ No streams found by Streamlink")
                return
                
            # Prefer audio, else worst video (saves bandwidth)
            stream = streams.get('audio_only')
            if not stream:
                stream = streams.get('worst')
            
            if not stream:
                print("❌ No useable stream found")
                return

            print(f"🔗 Opening stream: {stream}")
            
            # 2. Chunk processing loop
            # Open stream as file-like object
            try:
                fd = stream.open()
            except Exception as e:
                print(f"❌ Failed to open stream: {e}")
                return

            # Read in chunks of ~10 seconds
            # 1 second of 128kbps audio ~ 16KB. 
            # 10 seconds ~ 160KB. 
            # Let's read 256KB chunks to be safe.
            chunk_size = 256 * 1024 
            
            print("🟢 Stream opened. Starting transcription loop.", flush=True)
            
            while self.is_running:
                try:
                    # Read chunk from stream
                    # print("⬇️ Reading chunk...", flush=True)
                    data = fd.read(chunk_size)
                    
                    if not data:
                        print("⚠️ Stream ended or no data")
                        break
                    
                    # Save to temp file
                    temp_filename = f"live_chunk_{int(time.time()*1000)}.ts"
                    with open(temp_filename, "wb") as f:
                        f.write(data)
                    
                    # Transcribe
                    # print(f"🎧 Sending {len(data)} bytes to Whisper...", flush=True)
                    try:
                        with open(temp_filename, "rb") as audio_file:
                            transcript = client.audio.transcriptions.create(
                                model="whisper-1", 
                                file=audio_file,
                                language="en"
                            )
                        
                        text = transcript.text.strip()
                        if text and len(text) > 5:
                            print(f"📝 {text}", flush=True)
                            self.transcripts.append(text)
                            self.transcript_queue.put(text)
                    
                    except Exception as e:
                        # Common error if chunk is too short/silent
                        pass
                        # print(f"❌ Whisper error: {e}")
                    finally:
                        if os.path.exists(temp_filename):
                            os.remove(temp_filename)
                            
                except Exception as e:
                    print(f"⚠️ Chunk loop error: {e}")
                    time.sleep(1)
            
            fd.close()
            
        except Exception as e:
            print(f"❌ Streamlink error: {e}")
        finally:
            self.is_running = False


class BudgetDataEngine:
    """
    Main orchestrator - combines transcription and AI analysis.
    Auto-starts when YouTube URL is configured.
    """
    
    def __init__(self):
        self.transcriber = LiveTranscriber()
        self.analyzer = AIAnalyzer()
        self.transcripts: List[str] = []
        self.impacts: List[StockImpact] = []
        self._text_buffer = ""
    
    def get_ai_status(self) -> str:
        return self.analyzer.get_status()
    
    def get_transcriber_status(self) -> str:
        return self.transcriber.get_status()
    
    def is_streaming(self) -> bool:
        return self.transcriber.is_running
    
    def start_stream(self, youtube_url: str):
        """Start processing a YouTube URL."""
        self.transcriber.start(youtube_url)
    
    def stop_stream(self):
        """Stop processing."""
        self.transcriber.stop()
    
    def update(self) -> tuple:
        """
        Call this periodically to:
        1. Get new transcripts
        2. Analyze them for impacts
        
        Returns: (new_transcripts, new_impacts)
        """
        new_transcripts = self.transcriber.get_new_transcripts()
        new_impacts = []
        
        for transcript in new_transcripts:
            self.transcripts.append(transcript)
            
            # Buffer text for analysis
            self._text_buffer += " " + transcript
            
            # Analyze when buffer has enough content (2+ sentences)
            if len(self._text_buffer) > 80 or self._text_buffer.count('.') >= 2:
                impacts = self.analyzer.analyze(self._text_buffer.strip())
                if impacts:
                    self.impacts.extend(impacts)
                    new_impacts.extend(impacts)
                self._text_buffer = ""
        
        return new_transcripts, new_impacts
    
    def analyze_text(self, text: str) -> List[StockImpact]:
        """Manually analyze text (for testing)."""
        impacts = self.analyzer.analyze(text)
        self.impacts.extend(impacts)
        return impacts
