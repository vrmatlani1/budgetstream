"""
📱 SOCIAL ENGINE - Reddit/Twitter Sentiment Analysis
Handles: Polling social media for #Budget2026 sentiment
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import streamlit as st

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False


@dataclass
class SentimentScore:
    """Represents the current market sentiment from social media."""
    score: float  # 0-100, where 50 is neutral
    sample_size: int
    last_updated: str
    trending_keywords: list[str]
    mood: str  # "Bullish", "Bearish", "Neutral"
    
    @property
    def emoji(self) -> str:
        if self.score >= 70:
            return "🚀"
        elif self.score >= 55:
            return "📈"
        elif self.score >= 45:
            return "😐"
        elif self.score >= 30:
            return "📉"
        else:
            return "💀"


class SocialSentimentEngine:
    """
    Polls Reddit (and optionally Twitter) for budget-related sentiment.
    Runs in a background thread, updating a global sentiment score.
    """
    
    # Target subreddits for Indian market sentiment
    SUBREDDITS = ["IndianStreetBets", "IndiaInvestments", "indiainvestments"]
    KEYWORDS = ["budget", "Budget2026", "nirmala", "tax", "market", "stocks", "bull", "bear"]
    
    def __init__(self):
        self.reddit: Optional[praw.Reddit] = None
        self.current_sentiment: Optional[SentimentScore] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._init_reddit()
    
    def _init_reddit(self):
        """Initialize Reddit client from Streamlit secrets."""
        if not PRAW_AVAILABLE:
            print("⚠️ PRAW not installed. Social sentiment disabled.")
            return
            
        try:
            reddit_config = st.secrets.get("reddit", {})
            client_id = reddit_config.get("client_id", "")
            client_secret = reddit_config.get("client_secret", "")
            user_agent = reddit_config.get("user_agent", "BudgetStream/1.0")
            
            if client_id and client_id != "YOUR_REDDIT_CLIENT_ID":
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent
                )
                # Test connection
                self.reddit.user.me()
        except Exception as e:
            print(f"⚠️ Reddit init failed (read-only mode): {e}")
            # Try read-only mode
            try:
                self.reddit = praw.Reddit(
                    client_id=reddit_config.get("client_id", ""),
                    client_secret=reddit_config.get("client_secret", ""),
                    user_agent=reddit_config.get("user_agent", "BudgetStream/1.0"),
                    check_for_async=False
                )
            except:
                self.reddit = None
    
    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of text. Returns -1 to 1."""
        if not TEXTBLOB_AVAILABLE:
            return 0.0
        
        try:
            blob = TextBlob(text)
            return blob.sentiment.polarity
        except:
            return 0.0
    
    def _fetch_reddit_comments(self) -> list[str]:
        """Fetch recent comments from target subreddits."""
        if not self.reddit:
            return []
        
        comments = []
        try:
            for subreddit_name in self.SUBREDDITS:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Get hot posts
                    for post in subreddit.hot(limit=5):
                        # Check if budget-related
                        title_lower = post.title.lower()
                        if any(kw.lower() in title_lower for kw in self.KEYWORDS):
                            comments.append(post.title)
                            
                            # Get top comments
                            post.comments.replace_more(limit=0)
                            for comment in post.comments[:5]:
                                if hasattr(comment, 'body'):
                                    comments.append(comment.body)
                    
                    # Also check new posts about budget
                    for post in subreddit.new(limit=10):
                        title_lower = post.title.lower()
                        if any(kw.lower() in title_lower for kw in self.KEYWORDS):
                            comments.append(post.title)
                            
                except Exception as e:
                    print(f"⚠️ Error fetching from r/{subreddit_name}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Reddit fetch error: {e}")
        
        return comments[:20]  # Limit to 20 most recent
    
    def _extract_keywords(self, texts: list[str]) -> list[str]:
        """Extract trending keywords from texts."""
        keyword_counts = {}
        
        # Common words to ignore
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                    'as', 'into', 'through', 'during', 'before', 'after', 'above',
                    'below', 'between', 'under', 'again', 'further', 'then', 'once',
                    'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
                    'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
                    'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
                    'can', 'just', 'dont', 'now', 'its', 'this', 'that', 'and',
                    'but', 'if', 'or', 'because', 'until', 'while', 'about', 'i',
                    'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who'}
        
        for text in texts:
            words = text.lower().split()
            for word in words:
                # Clean word
                word = ''.join(c for c in word if c.isalnum())
                if len(word) > 3 and word not in stopwords:
                    keyword_counts[word] = keyword_counts.get(word, 0) + 1
        
        # Sort by frequency and return top 5
        sorted_kw = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in sorted_kw[:5]]
    
    def _calculate_sentiment_score(self) -> SentimentScore:
        """Calculate current sentiment from social media."""
        comments = self._fetch_reddit_comments()
        
        if not comments:
            return SentimentScore(
                score=50.0,
                sample_size=0,
                last_updated=datetime.now().strftime("%H:%M:%S"),
                trending_keywords=[],
                mood="Neutral"
            )
        
        # Calculate average sentiment
        sentiments = [self._analyze_sentiment(c) for c in comments]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # Convert -1 to 1 range to 0-100
        score = (avg_sentiment + 1) * 50
        
        # Determine mood
        if score >= 65:
            mood = "Bullish"
        elif score <= 35:
            mood = "Bearish"
        else:
            mood = "Neutral"
        
        return SentimentScore(
            score=round(score, 1),
            sample_size=len(comments),
            last_updated=datetime.now().strftime("%H:%M:%S"),
            trending_keywords=self._extract_keywords(comments),
            mood=mood
        )
    
    def _polling_loop(self, interval_seconds: int = 60):
        """Background polling loop."""
        while self._running:
            try:
                self.current_sentiment = self._calculate_sentiment_score()
            except Exception as e:
                print(f"❌ Sentiment polling error: {e}")
            
            time.sleep(interval_seconds)
    
    def start_polling(self, interval_seconds: int = 60):
        """Start background sentiment polling."""
        if self._thread and self._thread.is_alive():
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._polling_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._thread.start()
        
        # Get initial reading
        self.current_sentiment = self._calculate_sentiment_score()
    
    def stop_polling(self):
        """Stop background polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
    
    def get_sentiment(self) -> SentimentScore:
        """Get current sentiment score."""
        if not self.current_sentiment:
            # Return neutral if not started
            return SentimentScore(
                score=50.0,
                sample_size=0,
                last_updated=datetime.now().strftime("%H:%M:%S"),
                trending_keywords=[],
                mood="Neutral"
            )
        return self.current_sentiment
    
    def is_configured(self) -> bool:
        """Check if social engine is properly configured."""
        return self.reddit is not None


# =============================================================================
# MOCK DATA FOR DEMO MODE
# =============================================================================

def get_mock_sentiment() -> SentimentScore:
    """Generate mock sentiment for demo/testing."""
    import random
    
    score = random.uniform(45, 75)
    
    if score >= 65:
        mood = "Bullish"
    elif score <= 35:
        mood = "Bearish"
    else:
        mood = "Neutral"
    
    return SentimentScore(
        score=round(score, 1),
        sample_size=random.randint(10, 50),
        last_updated=datetime.now().strftime("%H:%M:%S"),
        trending_keywords=random.sample(
            ["Budget2026", "tax", "infrastructure", "nirmala", "bullish", 
             "railway", "defence", "green", "stocks", "market"],
            k=5
        ),
        mood=mood
    )
