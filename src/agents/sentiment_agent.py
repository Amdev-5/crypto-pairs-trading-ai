"""Sentiment analysis agent using Gemini with Google Search grounding"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from src.data.models import SentimentData
from src.config import config

logger = logging.getLogger(__name__)


class SentimentAgent:
    """
    AI-powered sentiment analysis agent

    Uses Gemini 2.5 Flash with Google Search grounding to:
    - Analyze news and events
    - Assess market sentiment
    - Detect major market-moving events
    - Provide actionable insights
    """

    def __init__(self):
        self.config = config.gemini
        self.sentiment_config = config.sentiment

        # Configure Gemini
        genai.configure(api_key=self.config.api_key)

        # Initialize model with search grounding
        generation_config = {
            "temperature": 0.3,  # Lower temperature for more factual responses
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }

        # Use Gemini 2.5 Flash with thinking
        self.model = genai.GenerativeModel(
            model_name=self.config.model,
            generation_config=generation_config
        )

        # Enable Google Search grounding
        self.search_config = {
            "google_search_retrieval": {
                "dynamic_retrieval_config": {
                    "mode": "MODE_DYNAMIC",
                    "dynamic_threshold": 0.3
                }
            }
        } if self.sentiment_config.enable_google_search else {}

        self.sentiment_cache: Dict[str, SentimentData] = {}
        self.last_update: Dict[str, datetime] = {}

    async def analyze_sentiment(
        self,
        symbol: str,
        lookback_hours: Optional[int] = None
    ) -> SentimentData:
        """
        Analyze sentiment for a cryptocurrency

        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            lookback_hours: Hours to look back for news (default from config)

        Returns:
            SentimentData with score, confidence, and summary
        """
        try:
            # Hard disable check
            if not getattr(self.sentiment_config, 'enabled', False):
                logger.debug("Sentiment analysis disabled in config")
                return SentimentData(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    sentiment_score=0.0,
                    confidence=0.0,
                    news_count=0,
                    major_events=[],
                    summary="Sentiment analysis disabled"
                )

            if lookback_hours is None:
                lookback_hours = self.sentiment_config.news_lookback_hours

            # Check cache
            if symbol in self.sentiment_cache:
                last_update = self.last_update.get(symbol)
                if last_update and (datetime.now() - last_update).seconds < self.sentiment_config.update_interval:
                    logger.debug(f"Using cached sentiment for {symbol}")
                    return self.sentiment_cache[symbol]

            logger.info(f"Analyzing sentiment for {symbol}...")

            # Create prompt for Gemini
            prompt = self._create_sentiment_prompt(symbol, lookback_hours)

            # Call Gemini with search grounding
            if self.sentiment_config.enable_google_search:
                # Use tools for search
                tools = [
                    genai.protos.Tool(
                        google_search_retrieval=genai.protos.GoogleSearchRetrieval()
                    )
                ]
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    tools=tools
                )
            else:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt
                )

            # Parse response
            sentiment_data = self._parse_sentiment_response(symbol, response.text)

            # Cache result
            self.sentiment_cache[symbol] = sentiment_data
            self.last_update[symbol] = datetime.now()

            logger.info(
                f"Sentiment for {symbol}: {sentiment_data.sentiment_score:.2f} "
                f"(confidence: {sentiment_data.confidence:.2f})"
            )

            return sentiment_data

        except ResourceExhausted as e:
            logger.warning(f"Gemini API quota exceeded for {symbol}. Returning neutral sentiment.")
            # Return neutral sentiment on quota exceeded
            return SentimentData(
                timestamp=datetime.now(),
                symbol=symbol,
                sentiment_score=0.0,
                confidence=0.0,
                news_count=0,
                major_events=[],
                summary="API quota exceeded - Neutral fallback"
            )

        except Exception as e:
            logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            # Return neutral sentiment on error
            return SentimentData(
                timestamp=datetime.now(),
                symbol=symbol,
                sentiment_score=0.0,
                confidence=0.0,
                news_count=0,
                major_events=[],
                summary="Error analyzing sentiment"
            )

    def _create_sentiment_prompt(self, symbol: str, lookback_hours: int) -> str:
        """Create prompt for Gemini"""
        return f"""You are a cryptocurrency market sentiment analyst. Analyze the current market sentiment for {symbol}.

Search for and analyze:
1. Recent news articles about {symbol} from the last {lookback_hours} hours
2. Major market events or announcements
3. Regulatory developments
4. Technical developments or upgrades
5. Market trends and trading volume
6. Social media sentiment (if available)
7. Expert opinions and analyst predictions

Provide your analysis in the following JSON format:
{{
    "sentiment_score": <float between -1.0 (very bearish) and 1.0 (very bullish)>,
    "confidence": <float between 0.0 and 1.0>,
    "news_count": <number of relevant news articles found>,
    "major_events": [<list of major events as strings>],
    "summary": "<2-3 sentence summary of market sentiment>"
}}

Consider:
- **Positive factors**: adoption news, partnerships, upgrades, positive regulation, institutional investment
- **Negative factors**: security breaches, regulatory crackdowns, negative news, market crashes
- **Neutral factors**: normal market volatility, minor news

Be objective and data-driven. Focus on market-moving events, not noise.

Current date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

    def _parse_sentiment_response(self, symbol: str, response_text: str) -> SentimentData:
        """Parse Gemini response into SentimentData"""
        try:
            # Try to extract JSON from response
            import json
            import re

            # Find JSON in response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                return SentimentData(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    sentiment_score=float(data.get('sentiment_score', 0.0)),
                    confidence=float(data.get('confidence', 0.5)),
                    news_count=int(data.get('news_count', 0)),
                    major_events=data.get('major_events', []),
                    summary=data.get('summary', '')
                )

            # Fallback: parse manually
            logger.warning("Could not parse JSON, using fallback parsing")

            # Simple keyword-based sentiment
            text_lower = response_text.lower()
            positive_keywords = ['bullish', 'positive', 'growth', 'adoption', 'partnership', 'upgrade']
            negative_keywords = ['bearish', 'negative', 'crash', 'regulation', 'ban', 'hack']

            positive_count = sum(1 for word in positive_keywords if word in text_lower)
            negative_count = sum(1 for word in negative_keywords if word in text_lower)

            if positive_count + negative_count > 0:
                sentiment_score = (positive_count - negative_count) / (positive_count + negative_count)
            else:
                sentiment_score = 0.0

            return SentimentData(
                timestamp=datetime.now(),
                symbol=symbol,
                sentiment_score=sentiment_score,
                confidence=0.5,
                news_count=0,
                major_events=[],
                summary=response_text[:200]
            )

        except Exception as e:
            logger.error(f"Error parsing sentiment response: {e}")
            return SentimentData(
                timestamp=datetime.now(),
                symbol=symbol,
                sentiment_score=0.0,
                confidence=0.0,
                news_count=0,
                major_events=[],
                summary="Error parsing response"
            )

    async def analyze_multiple_symbols(
        self,
        symbols: List[str]
    ) -> Dict[str, SentimentData]:
        """Analyze sentiment for multiple symbols concurrently"""
        tasks = [self.analyze_sentiment(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)

        return {symbol: result for symbol, result in zip(symbols, results)}

    async def detect_market_regime(self) -> str:
        """
        Detect current market regime

        Returns:
            'bull', 'bear', 'neutral', or 'volatile'
        """
        try:
            prompt = """Analyze the current cryptocurrency market regime.

Search for and analyze:
1. Overall market trends (BTC, ETH, major altcoins)
2. Market capitalization trends
3. Trading volumes
4. Fear & Greed Index
5. Major macro events affecting crypto

Classify the market as one of:
- **bull**: Strong uptrend, positive sentiment, increasing volumes
- **bear**: Strong downtrend, negative sentiment, fear
- **neutral**: Sideways movement, mixed sentiment
- **volatile**: High volatility, uncertain direction

Respond with ONLY ONE WORD: bull, bear, neutral, or volatile

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""

            if self.sentiment_config.enable_google_search:
                tools = [
                    genai.protos.Tool(
                        google_search_retrieval=genai.protos.GoogleSearchRetrieval()
                    )
                ]
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    tools=tools
                )
            else:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt
                )

            regime = response.text.strip().lower()

            if regime in ['bull', 'bear', 'neutral', 'volatile']:
                logger.info(f"Market regime: {regime}")
                return regime
            else:
                logger.warning(f"Unexpected regime response: {regime}")
                return 'neutral'

        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return 'neutral'

    async def check_for_major_events(self) -> List[str]:
        """
        Check for major market events that might affect trading

        Returns:
            List of major events
        """
        try:
            prompt = """Search for any MAJOR cryptocurrency market events in the last 24 hours that could significantly impact trading:

Examples of major events:
- Exchange hacks or outages
- Regulatory announcements
- Major institutional moves
- Hard forks or network upgrades
- Significant price crashes/pumps (>10%)
- Major economic news affecting crypto

If there are major events, list them concisely (one per line).
If there are NO major events, respond with: "No major events"

Current date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

            if self.sentiment_config.enable_google_search:
                tools = [
                    genai.protos.Tool(
                        google_search_retrieval=genai.protos.GoogleSearchRetrieval()
                    )
                ]
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    tools=tools
                )
            else:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt
                )

            text = response.text.strip()

            if "no major events" in text.lower():
                return []

            # Split by newlines and filter
            events = [
                line.strip()
                for line in text.split('\n')
                if line.strip() and not line.strip().startswith('#')
            ]

            if events:
                logger.info(f"Major events detected: {len(events)}")
                for event in events:
                    logger.info(f"  - {event}")

            return events

        except Exception as e:
            logger.error(f"Error checking for major events: {e}")
            return []

    def clear_cache(self):
        """Clear sentiment cache"""
        self.sentiment_cache.clear()
        self.last_update.clear()
        logger.info("Sentiment cache cleared")
