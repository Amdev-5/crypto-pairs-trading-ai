"""Order execution manager"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
import logging

from src.data.bybit_client import get_bybit_client
from src.data.models import OrderSide, OrderType, PositionSide
from src.config import config
from src.execution.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class OrderManager:
    """Manages order execution"""

    def __init__(self):
        self.client = get_bybit_client()
        self.pending_orders: Dict[str, Dict] = {}
        self.trading_enabled = config.trading.enabled
        self.rate_limiter = get_rate_limiter()  # Add rate limiter

    async def execute_pair_entry(
        self,
        pair_id: str,
        symbol_a: str,
        symbol_b: str,
        action: str,  # 'LONG_SPREAD' or 'SHORT_SPREAD'
        size_a: float,
        size_b: float,
        hedge_ratio: float
    ) -> tuple[bool, Dict]:
        """
        Execute entry orders for a pair

        For LONG_SPREAD: Long A, Short B
        For SHORT_SPREAD: Short A, Long B

        Returns:
            - success: bool
            - result: Dict with entry prices and order IDs
        """
        if not self.trading_enabled:
            logger.warning("Trading disabled, simulating order execution")
            return await self._simulate_execution(symbol_a, symbol_b)

        try:
            logger.info(f"Executing {action} for {pair_id}...")

            # Determine sides
            if action == 'LONG_SPREAD':
                side_a = OrderSide.BUY
                side_b = OrderSide.SELL
            elif action == 'SHORT_SPREAD':
                side_a = OrderSide.SELL
                side_b = OrderSide.BUY
            else:
                raise ValueError(f"Invalid action: {action}")

            # Get current prices (try WebSocket first, fallback to REST API)
            price_a = self.client.get_latest_price(symbol_a)
            price_b = self.client.get_latest_price(symbol_b)

            # Fallback to REST API if WebSocket doesn't have data yet
            if not price_a or not price_b:
                logger.warning(f"WebSocket prices not available, using REST API...")
                try:
                    from pybit.unified_trading import HTTP
                    from src.config import config

                    http_client = HTTP(
                        testnet=config.bybit.testnet,
                        api_key=config.bybit.api_key,
                        api_secret=config.bybit.api_secret
                    )

                    if not price_a:
                        ticker_a = http_client.get_tickers(category="linear", symbol=symbol_a)
                        if ticker_a and ticker_a.get('result') and ticker_a['result'].get('list') and len(ticker_a['result']['list']) > 0:
                            price_a = float(ticker_a['result']['list'][0]['lastPrice'])
                        else:
                            logger.error(f"No ticker data available for {symbol_a}")
                            return False, {}

                    if not price_b:
                        ticker_b = http_client.get_tickers(category="linear", symbol=symbol_b)
                        if ticker_b and ticker_b.get('result') and ticker_b['result'].get('list') and len(ticker_b['result']['list']) > 0:
                            price_b = float(ticker_b['result']['list'][0]['lastPrice'])
                        else:
                            logger.error(f"No ticker data available for {symbol_b}")
                            return False, {}

                    logger.info(f"REST API prices: {symbol_a}=${price_a:.2f}, {symbol_b}=${price_b:.2f}")
                except Exception as e:
                    logger.error(f"Could not get prices for {symbol_a}/{symbol_b}: {e}")
                    return False, {}

            # Validate prices
            if not self._validate_price(symbol_a, price_a):
                logger.warning(f"Invalid price for {symbol_a}: {price_a}. Retrying via REST...")
                price_a = self._fetch_price_rest(symbol_a)
            
            if not self._validate_price(symbol_b, price_b):
                logger.warning(f"Invalid price for {symbol_b}: {price_b}. Retrying via REST...")
                price_b = self._fetch_price_rest(symbol_b)

            if not self._validate_price(symbol_a, price_a) or not self._validate_price(symbol_b, price_b):
                logger.error(f"❌ Aborting execution: Invalid prices. {symbol_a}=${price_a}, {symbol_b}=${price_b}")
                return False, {}

            # Convert USD notional to contract quantities
            # size_a and size_b are in USD from risk_agent
            # For Bybit linear perpetuals, qty must be in base currency (BTC, ETH, etc)
            
            # Log the calculation for debugging
            logger.info(f"🧮 Sizing: {symbol_a} ${size_a:.2f} / ${price_a:.2f} | {symbol_b} ${size_b:.2f} / ${price_b:.2f}")

            def round_qty(qty: float, symbol: str) -> float:
                """Round quantity to proper decimal places for each symbol"""
                # Bybit precision rules for linear perpetuals
                if 'BTC' in symbol:
                    return round(qty, 3)  # 0.001 BTC precision
                elif 'ETH' in symbol:
                    return round(qty, 2)  # 0.01 ETH precision
                elif 'SOL' in symbol or 'AVAX' in symbol:
                    return round(qty, 1)  # 0.1 precision
                elif 'XRP' in symbol or 'DOGE' in symbol or 'ADA' in symbol:
                    return int(qty)  # 1 unit precision
                else:
                    return round(qty, 2)  # Default 0.01 precision

            # Convert USD to base currency qty
            qty_a = size_a / price_a
            qty_b = size_b / price_b

            logger.debug(f"Pre-rounding: {symbol_a}={qty_a:.10f} contracts, {symbol_b}={qty_b:.10f} contracts")

            # Round to proper decimals FIRST
            qty_a_rounded = round_qty(qty_a, symbol_a)
            qty_b_rounded = round_qty(qty_b, symbol_b)

            # Safety check for huge quantities (Hard limits)
            # XRP max = 50M, BTC max = 100, ETH max = 1000
            max_qty_limits = {
                'BTC': 100,
                'ETH': 1000,
                'XRP': 50_000_000,
                'LTC': 10000,
                'DOGE': 50_000_000,
                'BCH': 1000,
                'ADA': 50_000_000,
                'SOL': 10000
            }

            # Get coin name from symbol (e.g., BTCUSDT -> BTC)
            coin_a = symbol_a.replace('USDT', '')
            coin_b = symbol_b.replace('USDT', '')

            max_a = max_qty_limits.get(coin_a, 100000)
            max_b = max_qty_limits.get(coin_b, 100000)

            if qty_a_rounded > max_a or qty_b_rounded > max_b:
                logger.error(f"🚨 Safety limit triggered: Qty too large!")
                logger.error(f"   {symbol_a}: {qty_a_rounded} > max {max_a}")
                logger.error(f"   {symbol_b}: {qty_b_rounded} > max {max_b}")
                logger.error(f"   Input size_a=${size_a:.2f}, size_b=${size_b:.2f}")
                logger.error(f"   Prices: {symbol_a}=${price_a:.2f}, {symbol_b}=${price_b:.2f}")
                return False, {}

            # Check minimum order sizes
            min_qty_a = 0.001 if 'BTC' in symbol_a else 0.01
            min_qty_b = 0.001 if 'BTC' in symbol_b else 0.01

            if qty_a_rounded < min_qty_a or qty_b_rounded < min_qty_b:
                logger.error(f"Qty below minimum: {symbol_a}={qty_a_rounded} (min {min_qty_a}), {symbol_b}={qty_b_rounded} (min {min_qty_b})")
                return False, {}

            logger.info(f"Position sizing: {symbol_a}={qty_a_rounded} (~${size_a:.2f}), {symbol_b}={qty_b_rounded} (~${size_b:.2f})")

            # ========== ROBUST ENTRY EXECUTION ==========
            # Use smart limit orders for better pricing, with market fallback
            
            logger.info(f"🎯 Executing ENTRY with smart limit orders...")
            
            # Execute leg A with smart entry
            success_a, filled_qty_a, avg_price_a, side_a_pos = await self._smart_entry_order(
                symbol_a, side_a, qty_a_rounded, price_a
            )
            
            if not success_a:
                logger.error(f"❌ Failed to execute leg A for {pair_id}")
                return False, {}
            
            # Small delay between legs
            await asyncio.sleep(0.1)
            
            # Execute leg B with smart entry
            success_b, filled_qty_b, avg_price_b, side_b_pos = await self._smart_entry_order(
                symbol_b, side_b, qty_b_rounded, price_b
            )
            
            if not success_b:
                logger.error(f"❌ Failed to execute leg B for {pair_id}")
                # Leg A succeeded but B failed - need to close A
                logger.warning(f"⚠️ Closing leg A to avoid imbalanced position...")
                await self._smart_exit_order(
                    symbol_a,
                    OrderSide.SELL if side_a == OrderSide.BUY else OrderSide.BUY,
                    filled_qty_a,
                    avg_price_a
                )
                return False, {}

            result = {
                'entry_price_a': avg_price_a,
                'entry_price_b': avg_price_b,
                'qty_a': filled_qty_a,
                'qty_b': filled_qty_b,
                'side_a': side_a_pos,
                'side_b': side_b_pos,
                'timestamp': datetime.now()
            }

            logger.info(f"✅ Entry executed: {pair_id} | A: {filled_qty_a}@${avg_price_a:.2f}, B: {filled_qty_b}@${avg_price_b:.2f}")
            return True, result

        except Exception as e:
            logger.error(f"Error executing orders for {pair_id}: {e}")
            return False, {}

    async def _smart_entry_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        current_price: float,
        max_attempts: int = 3
    ) -> tuple[bool, float, float, PositionSide]:
        """
        Smart entry with limit orders and fallback to market
        
        Returns: (success, filled_qty, avg_price, position_side)
        """
        from pybit.unified_trading import HTTP
        from src.config import config
        
        # Create HTTP client for order status checks
        http_client = HTTP(
            testnet=config.bybit.testnet,
            api_key=config.bybit.api_key,
            api_secret=config.bybit.api_secret
        )
        
        # Determine position side
        position_side = PositionSide.LONG if side == OrderSide.BUY else PositionSide.SHORT
        
        # Try limit orders with progressively aggressive pricing
        for attempt in range(max_attempts):
            try:
                # Rate limiting
                await self.rate_limiter.acquire(symbol)
                
                # Calculate limit price (favorable for us)
                # For BUY: place above market to increase fill chance
                # For SELL: place below market to increase fill chance
                if side == OrderSide.BUY:
                    # Buying: start at market, then go higher
                    limit_price = current_price * (1.0 + 0.0003 * attempt)  # 0.03% steps
                else:
                    # Selling: start at market, then go lower
                    limit_price = current_price * (1.0 - 0.0003 * attempt)

                logger.info(f"Entry attempt {attempt + 1}: {side.value} {qty} {symbol} @ ${limit_price:.2f}")

                # Place limit order
                order = await self.client.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=OrderType.LIMIT,
                    qty=str(qty),
                    price=str(limit_price),
                    time_in_force="GTC"
                )

                order_id = order.get('orderId')
                
                # Wait for fill (1.5 seconds for entry - faster than exit)
                await asyncio.sleep(1.5)

                # Check order status
                order_info = http_client.get_open_orders(
                    category="linear",
                    symbol=symbol,
                    orderId=order_id
                )
                
                if order_info and order_info.get('result') and order_info['result'].get('list'):
                    order_data = order_info['result']['list'][0]
                    order_status = order_data.get('orderStatus')
                    
                    if order_status == 'Filled':
                        filled_qty = float(order_data.get('cumExecQty', qty))
                        avg_price = float(order_data.get('avgPrice', limit_price))
                        logger.info(f"✅ Entry limit filled: {filled_qty} @ ${avg_price:.2f}")
                        self.rate_limiter.report_success()
                        return True, filled_qty, avg_price, position_side
                    
                    elif order_status == 'PartiallyFilled':
                        # Partial fill - cancel and retry with remaining
                        filled_qty = float(order_data.get('cumExecQty', 0))
                        remaining_qty = qty - filled_qty
                        
                        logger.warning(f"Partial fill: {filled_qty}/{qty}. Canceling and retrying...")
                        http_client.cancel_order(
                            category="linear",
                            symbol=symbol,
                            orderId=order_id
                        )
                        
                        if remaining_qty > 0:
                            qty = remaining_qty  # Retry with remaining
                            continue
                        else:
                            avg_price = float(order_data.get('avgPrice', limit_price))
                            self.rate_limiter.report_success()
                            return True, filled_qty, avg_price, position_side
                    
                    else:
                        # Not filled - cancel and try next attempt
                        logger.warning(f"Order not filled (status: {order_status}). Canceling...")
                        http_client.cancel_order(
                            category="linear",
                            symbol=symbol,
                            orderId=order_id
                        )
                else:
                    # Order not found - may be filled
                    logger.warning(f"Order {order_id} not in open orders - may be filled")
                    self.rate_limiter.report_success()
                    return True, qty, limit_price, position_side
                    
            except Exception as e:
                logger.error(f"Entry limit attempt {attempt + 1} failed: {e}")
                if 'rate limit' in str(e).lower():
                    self.rate_limiter.report_error(str(e))

        # All limit attempts failed - force MARKET order
        logger.warning(f"⚠️ Entry limit orders failed. Forcing MARKET order for {symbol}")
        
        try:
            await self.rate_limiter.acquire(symbol)
            
            market_order = await self.client.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                qty=str(qty)
            )
            
            filled_qty = float(market_order.get('cumExecQty', qty))
            avg_price = float(market_order.get('avgPrice', current_price))
            
            logger.info(f"✅ Entry market filled: {filled_qty} @ ${avg_price:.2f}")
            self.rate_limiter.report_success()
            return True, filled_qty, avg_price, position_side
            
        except Exception as e:
            logger.error(f"❌ Entry market order failed: {e}")
            self.rate_limiter.report_error(str(e))
            return False, 0.0, 0.0, position_side

    async def execute_pair_exit(
        self,
        pair_id: str,
        symbol_a: str,
        symbol_b: str,
        side_a: PositionSide,
        side_b: PositionSide,
        size_a: float,
        size_b: float
    ) -> tuple[bool, Dict]:
        """
        Execute exit orders for a pair with robust fill verification
        
        Strategy:
        1. Try LIMIT orders at favorable prices (3 attempts with price adjustment)
        2. If limit fails, force MARKET order
        3. Verify fills and retry partial fills
        """
        if not self.trading_enabled:
            logger.warning("Trading disabled, simulating order execution")
            return await self._simulate_execution(symbol_a, symbol_b)

        try:
            logger.info(f"Closing position for {pair_id}...")

            # Determine exit sides (opposite of entry)
            exit_side_a = OrderSide.SELL if side_a == PositionSide.LONG else OrderSide.BUY
            exit_side_b = OrderSide.SELL if side_b == PositionSide.LONG else OrderSide.BUY

            # Get current prices
            price_a = self.client.get_latest_price(symbol_a)
            price_b = self.client.get_latest_price(symbol_b)

            # Fallback to REST API if WebSocket doesn't have data
            if not price_a or not price_b:
                logger.warning(f"WebSocket prices not available, using REST API...")
                try:
                    from pybit.unified_trading import HTTP
                    from src.config import config

                    http_client = HTTP(
                        testnet=config.bybit.testnet,
                        api_key=config.bybit.api_key,
                        api_secret=config.bybit.api_secret
                    )

                    if not price_a:
                        ticker_a = http_client.get_tickers(category="linear", symbol=symbol_a)
                        if ticker_a and ticker_a.get('result') and ticker_a['result'].get('list'):
                            price_a = float(ticker_a['result']['list'][0]['lastPrice'])

                    if not price_b:
                        ticker_b = http_client.get_tickers(category="linear", symbol=symbol_b)
                        if ticker_b and ticker_b.get('result') and ticker_b['result'].get('list'):
                            price_b = float(ticker_b['result']['list'][0]['lastPrice'])

                except Exception as e:
                    logger.error(f"Could not get prices: {e}")
                    return False, {}

            if price_a <= 0 or price_b <= 0:
                logger.error(f"Invalid prices: {symbol_a}={price_a}, {symbol_b}={price_b}")
                return False, {}

            # Round quantities
            def round_qty(qty: float, symbol: str) -> float:
                if 'BTC' in symbol:
                    return round(qty, 3)
                elif 'ETH' in symbol:
                    return round(qty, 2)
                elif 'XRP' in symbol or 'DOGE' in symbol:
                    return round(qty, 0)
                else:
                    return round(qty, 2)

            qty_a = round_qty(size_a, symbol_a)
            qty_b = round_qty(size_b, symbol_b)

            logger.info(f"Closing: {symbol_a}={qty_a}, {symbol_b}={qty_b}")

            # Try smart exit with limit orders first (better pricing)
            success_a, filled_qty_a, avg_price_a = await self._smart_exit_order(
                symbol_a, exit_side_a, qty_a, price_a
            )
            
            success_b, filled_qty_b, avg_price_b = await self._smart_exit_order(
                symbol_b, exit_side_b, qty_b, price_b
            )

            if not success_a or not success_b:
                logger.error(f"Exit failed: A={success_a}, B={success_b}")
                return False, {}

            result = {
                'exit_price_a': avg_price_a,
                'exit_price_b': avg_price_b,
                'filled_qty_a': filled_qty_a,
                'filled_qty_b': filled_qty_b,
                'timestamp': datetime.now()
            }

            logger.info(f"✅ Position closed: {pair_id} | A: {filled_qty_a}@${avg_price_a:.2f}, B: {filled_qty_b}@${avg_price_b:.2f}")
            return True, result

        except Exception as e:
            logger.error(f"Error closing {pair_id}: {e}")
            return False, {}

    async def _smart_exit_order(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        current_price: float,
        max_attempts: int = 3
    ) -> tuple[bool, float, float]:
        """
        Smart exit with limit orders and fallback to market
        
        Returns: (success, filled_qty, avg_price)
        """
        from pybit.unified_trading import HTTP
        from src.config import config
        
        # Create HTTP client for order status checks
        http_client = HTTP(
            testnet=config.bybit.testnet,
            api_key=config.bybit.api_key,
            api_secret=config.bybit.api_secret
        )
        
        # Try limit orders with progressively aggressive pricing
        for attempt in range(max_attempts):
            try:
                # Calculate limit price (slightly favorable for us)
                # For SELL: place below market, For BUY: place above market
                if side == OrderSide.SELL:
                    # Selling: start at market, then go lower
                    limit_price = current_price * (1.0 - 0.0005 * attempt)  # 0.05% steps
                else:
                    # Buying: start at market, then go higher
                    limit_price = current_price * (1.0 + 0.0005 * attempt)

                logger.info(f"Attempt {attempt + 1}: {side.value} {qty} {symbol} @ ${limit_price:.2f}")

                # Place limit order
                order = await self.client.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=OrderType.LIMIT,
                    qty=str(qty),
                    price=str(limit_price),
                    reduce_only=True,
                    time_in_force="GTC"  # Good till cancel
                )

                order_id = order.get('orderId')
                
                # Wait for fill (2 seconds)
                await asyncio.sleep(2)

                # Check order status using HTTP client
                order_info = http_client.get_open_orders(
                    category="linear",
                    symbol=symbol,
                    orderId=order_id
                )
                
                if order_info and order_info.get('result') and order_info['result'].get('list'):
                    order_data = order_info['result']['list'][0]
                    order_status = order_data.get('orderStatus')
                    
                    if order_status == 'Filled':
                        filled_qty = float(order_data.get('cumExecQty', qty))
                        avg_price = float(order_data.get('avgPrice', limit_price))
                        logger.info(f"✅ Limit order filled: {filled_qty} @ ${avg_price:.2f}")
                        return True, filled_qty, avg_price
                    
                    elif order_status == 'PartiallyFilled':
                        # Partial fill - cancel and retry with remaining
                        filled_qty = float(order_data.get('cumExecQty', 0))
                        remaining_qty = qty - filled_qty
                        
                        logger.warning(f"Partial fill: {filled_qty}/{qty}. Canceling and retrying...")
                        http_client.cancel_order(
                            category="linear",
                            symbol=symbol,
                            orderId=order_id
                        )
                        
                        if remaining_qty > 0:
                            qty = remaining_qty  # Retry with remaining
                            continue
                        else:
                            avg_price = float(order_data.get('avgPrice', limit_price))
                            return True, filled_qty, avg_price
                    
                    else:
                        # Not filled - cancel and try next attempt
                        logger.warning(f"Order not filled (status: {order_status}). Canceling...")
                        http_client.cancel_order(
                            category="linear",
                            symbol=symbol,
                            orderId=order_id
                        )
                else:
                    # Order not found or already filled - assume filled
                    logger.warning(f"Order {order_id} not in open orders - may be filled")
                    return True, qty, limit_price
                    
            except Exception as e:
                logger.error(f"Limit order attempt {attempt + 1} failed: {e}")

        # All limit attempts failed - force MARKET order
        logger.warning(f"⚠️ Limit orders failed. Forcing MARKET order for {symbol}")
        
        try:
            market_order = await self.client.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                qty=str(qty),
                reduce_only=True
            )
            
            # Market orders fill immediately
            filled_qty = float(market_order.get('cumExecQty', qty))
            avg_price = float(market_order.get('avgPrice', current_price))
            
            logger.info(f"✅ Market order filled: {filled_qty} @ ${avg_price:.2f}")
            return True, filled_qty, avg_price
            
        except Exception as e:
            logger.error(f"❌ Market order failed: {e}")
            return False, 0.0, 0.0

    async def _simulate_execution(
        self,
        symbol_a: str,
        symbol_b: str
    ) -> tuple[bool, Dict]:
        """Simulate order execution (for testing/paper trading)"""
        # Get current prices
        price_a = self.client.get_latest_price(symbol_a)
        price_b = self.client.get_latest_price(symbol_b)

        if not price_a or not price_b:
            # Fallback to mid-price
            price_a = self.client.get_mid_price(symbol_a) or 0.0
            price_b = self.client.get_mid_price(symbol_b) or 0.0

        # Simulate slippage (0.05%)
        slippage = 0.0005
        price_a_slipped = price_a * (1 + slippage)
        price_b_slipped = price_b * (1 + slippage)

        result = {
            'entry_price_a': price_a_slipped,
            'entry_price_b': price_b_slipped,
            'exit_price_a': price_a_slipped,
            'exit_price_b': price_b_slipped,
            'order_id_a': f"sim_{symbol_a}_{datetime.now().timestamp()}",
            'order_id_b': f"sim_{symbol_b}_{datetime.now().timestamp()}",
            'timestamp': datetime.now(),
            'simulated': True
        }

        logger.info(f"Simulated execution: {symbol_a} @ ${price_a_slipped:.2f}, {symbol_b} @ ${price_b_slipped:.2f}")
        return True, result

    async def cancel_all_orders(self, symbol: Optional[str] = None):
        """Cancel all pending orders"""
        try:
            if symbol:
                logger.info(f"Cancelling all orders for {symbol}")
            else:
                logger.info("Cancelling all orders")

            # Implementation depends on whether we're tracking pending orders
            # For now, just log
            self.pending_orders.clear()

        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")

    def get_estimated_slippage(self, symbol: str, size: float) -> float:
        """
        Estimate slippage for an order

        Returns estimated slippage in USD
        """
        # Simple model: larger orders = more slippage
        # In production, analyze orderbook depth

        base_slippage = 0.0005  # 0.05%
        size_factor = min(size / 10000, 0.01)  # Up to 1% for very large orders

        total_slippage = base_slippage + size_factor

        price = self.client.get_latest_price(symbol) or 0
        estimated_cost = price * size * total_slippage

        return estimated_cost

    def _validate_price(self, symbol: str, price: float) -> bool:
        """Validate if price is reasonable"""
        if not price or price <= 0:
            return False
            
        # Basic sanity checks for major assets
        if 'BTC' in symbol and price < 10000:
            return False
        if 'ETH' in symbol and price < 500:
            return False
        if 'SOL' in symbol and price < 10:
            return False
            
        return True

    def _fetch_price_rest(self, symbol: str) -> float:
        """Fetch price via REST API as fallback"""
        try:
            from pybit.unified_trading import HTTP
            from src.config import config
            
            http_client = HTTP(
                testnet=config.bybit.testnet,
                api_key=config.bybit.api_key,
                api_secret=config.bybit.api_secret
            )
            
            ticker = http_client.get_tickers(category="linear", symbol=symbol)
            if ticker and ticker.get('result') and ticker['result'].get('list') and len(ticker['result']['list']) > 0:
                return float(ticker['result']['list'][0]['lastPrice'])
                
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching REST price for {symbol}: {e}")
            return 0.0
