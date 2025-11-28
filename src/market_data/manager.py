"""
Market Data Manager
Handles real-time data streaming, local order book management, and funding rate updates.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime
from collections import deque

from pybit.unified_trading import WebSocket
from src.config import config

logger = logging.getLogger(__name__)


class MarketDataManager:
    """
    Manages real-time market data via WebSockets.
    Maintains local order book and streams price updates.
    """

    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.ws: Optional[WebSocket] = None
        self.callbacks: List[Callable] = []
        
        # Data stores
        self.order_books: Dict[str, Dict] = {s: {'bids': [], 'asks': []} for s in symbols}
        self.latest_prices: Dict[str, float] = {}
        self.latest_candles: Dict[str, Dict] = {}  # Store latest OHLCV
        self.funding_rates: Dict[str, float] = {}
        self.tickers: Dict[str, Dict] = {}
        
        # Connection state
        self.connected = False
        self.last_update: Dict[str, datetime] = {}

    async def start(self):
        """Start the WebSocket connection"""
        try:
            logger.info(f"🚀 Starting MarketDataManager for {len(self.symbols)} symbols...")
            
            # Initialize PyBit WebSocket
            self.ws = WebSocket(
                testnet=config.bybit.testnet,
                channel_type="linear",
            )

            # Subscribe to streams
            for symbol in self.symbols:
                # Orderbook (Depth 50 for speed)
                self.ws.orderbook_stream(
                    depth=50,
                    symbol=symbol,
                    callback=self._handle_orderbook
                )
                
                # Ticker (Funding Rate)
                self.ws.ticker_stream(
                    symbol=symbol,
                    callback=self._handle_ticker
                )
                
                # Kline (1-minute candles for ATR/Volume)
                self.ws.kline_stream(
                    interval=1,
                    symbol=symbol,
                    callback=self._handle_kline
                )
            
            self.connected = True
            logger.info("✅ MarketDataManager connected and subscribed (OB, Ticker, Kline)!")
            
            # Keep alive loop
            while self.connected:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ MarketDataManager error: {e}")
            self.connected = False
            # Auto-reconnect logic could go here

    def stop(self):
        """Stop the WebSocket connection"""
        self.connected = False
        if self.ws:
            # PyBit WS doesn't have a clean async close, but we can stop the loop
            pass
        logger.info("🛑 MarketDataManager stopped")

    def _handle_kline(self, message: Dict):
        """Handle kline (candle) updates"""
        try:
            topic = message.get('topic', '')
            if 'kline' not in topic:
                return

            data = message.get('data', [])
            if not data:
                return
                
            # Data is a list of candles, usually just one latest update
            for candle in data:
                symbol = topic.split('.')[-1]
                
                # Store latest candle data
                # Format: start, open, high, low, close, volume, turnover
                self.latest_candles[symbol] = {
                    'timestamp': datetime.fromtimestamp(int(candle['start']) / 1000),
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': float(candle['volume'])
                }
                
        except Exception as e:
            logger.error(f"Error handling kline: {e}")

    def _handle_orderbook(self, message: Dict):
        """Handle orderbook snapshot/delta"""
        try:
            topic = message.get('topic', '')
            if 'orderbook' not in topic:
                return

            symbol = topic.split('.')[-1]
            data = message.get('data', {})
            
            # Update local order book (Simplified for now - just storing best bid/ask)
            # In a full LOB implementation, we'd process deltas carefully
            if 'b' in data and data['b']:
                self.order_books[symbol]['bids'] = data['b']
            if 'a' in data and data['a']:
                self.order_books[symbol]['asks'] = data['a']
                
            # Update latest price from mid-price
            if self.order_books[symbol]['bids'] and self.order_books[symbol]['asks']:
                best_bid = float(self.order_books[symbol]['bids'][0][0])
                best_ask = float(self.order_books[symbol]['asks'][0][0])
                mid_price = (best_bid + best_ask) / 2
                self.latest_prices[symbol] = mid_price
                self.last_update[symbol] = datetime.now()
                
                # Notify callbacks
                self._notify_callbacks(symbol, mid_price)

        except Exception as e:
            logger.error(f"Error handling orderbook: {e}")

    def _handle_ticker(self, message: Dict):
        """Handle ticker updates (Funding Rate, 24h stats)"""
        try:
            topic = message.get('topic', '')
            if 'tickers' not in topic:
                return

            data = message.get('data', {})
            symbol = data.get('symbol')
            
            if symbol:
                self.tickers[symbol] = data
                
                # Update Funding Rate
                if 'fundingRate' in data:
                    self.funding_rates[symbol] = float(data['fundingRate'])
                    
                # Update Last Price if OB not available
                if 'lastPrice' in data:
                    self.latest_prices[symbol] = float(data['lastPrice'])

        except Exception as e:
            logger.error(f"Error handling ticker: {e}")

    def register_callback(self, callback: Callable):
        """Register a callback for price updates"""
        self.callbacks.append(callback)

    def _notify_callbacks(self, symbol: str, price: float):
        """Notify all registered callbacks"""
        for callback in self.callbacks:
            try:
                # Callbacks should be non-blocking or scheduled
                asyncio.create_task(callback(symbol, price))
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    def get_price(self, symbol: str) -> float:
        """Get latest price for a symbol"""
        return self.latest_prices.get(symbol, 0.0)

    def get_orderbook(self, symbol: str) -> Dict:
        """Get current orderbook for a symbol"""
        return self.order_books.get(symbol, {})

    def get_funding_rate(self, symbol: str) -> float:
        """Get latest funding rate for a symbol"""
        return self.funding_rates.get(symbol, 0.0)

    def get_candle(self, symbol: str) -> Dict:
        """Get latest candle for a symbol"""
        return self.latest_candles.get(symbol, {})
