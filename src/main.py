"""Main trading engine"""

import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import signal
import sys

from src.config import config
from src.data.bybit_client import get_bybit_client
from src.agents.orchestrator import OrchestratorAgent
from src.execution.position_manager import PositionManager
from src.execution.order_manager import OrderManager
from src.data.models import PositionSide, TradeSignal

# Import dashboard update functions
try:
    from src.dashboard.app import update_dashboard, update_balance, update_stats
    DASHBOARD_ENABLED = True
except ImportError:
    DASHBOARD_ENABLED = False
    logger.warning("Dashboard not available")

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.settings.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingEngine:
    """Main trading engine orchestrating all components"""

    def __init__(self):
        self.config = config
        self.client = get_bybit_client()
        self.orchestrator = OrchestratorAgent()
        self.position_manager = PositionManager()
        self.order_manager = OrderManager()

        self.running = False
        self.price_data: Dict[str, pd.Series] = {}
        self.candle_data: Dict[str, pd.DataFrame] = {}  # OHLCV data

        # Get trading pairs from config
        self.pairs = self.config.get_trading_pairs()
        self.symbols = self._extract_symbols(self.pairs)
        
        # Initialize MarketDataManager (will start in async start())
        from src.market_data.manager import MarketDataManager
        self.market_data = MarketDataManager(self.symbols)

        logger.info(f"Trading engine initialized with {len(self.pairs)} pairs")

    def _extract_symbols(self, pairs: List[Dict]) -> List[str]:
        """Extract unique symbols from pairs"""
        symbols = set()
        for pair in pairs:
            if pair.get('enabled', True):
                symbols.add(pair['symbol_a'])
                symbols.add(pair['symbol_b'])
        return list(symbols)

    async def start(self):
        """Start the trading engine"""
        try:
            logger.info("==" * 60)
            logger.info("CRYPTO PAIRS TRADING SYSTEM")
            logger.info("=" * 60)
            logger.info(f"Trading pairs: {len(self.pairs)}")
            logger.info(f"Trading enabled: {self.config.trading.enabled}")
            logger.info(f"Testnet mode: {self.config.bybit.testnet}")
            logger.info("=" * 60)
            
            # Clear all trade history at startup (fresh start)
            self.position_manager.clear_all_history()
            logger.info("Trade history cleared at startup")

            # Connect to Bybit WebSocket
            logger.info("Connecting to Bybit WebSocket...")
            await self.client.connect(self.symbols)

            # Load historical data
            logger.info("Loading historical data...")
            await self._load_historical_data()

            # Force reset daily P&L to clear any phantom state
            self.position_manager.reset_daily_pnl()
            logger.info("Daily P&L force-reset on startup")

            # Start MarketDataManager WebSocket in background
            logger.info("Starting MarketDataManager WebSocket...")
            market_data_task = asyncio.create_task(self.market_data.start())
            
            # Wait for initial connection and data
            await asyncio.sleep(3)
            logger.info(f"MarketDataManager started. Sample prices: {list(self.market_data.latest_prices.items())[:3]}")

            # Start main loop
            self.running = True
            logger.info("Starting main trading loop...")

            await self._main_loop()

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
            await self.stop()
        except Exception as e:
            logger.error(f"Fatal error in trading engine: {e}", exc_info=True)
            await self.stop()

    async def stop(self):
        """Stop the trading engine"""
        logger.info("Stopping trading engine...")
        self.running = False

        # Close all positions if configured
        if config.settings.trading_enabled:
            logger.info("Closing all open positions...")
            await self._close_all_positions()

        # Disconnect
        self.client.disconnect()
        logger.info("Trading engine stopped")

    async def _load_historical_data(self):
        """Load historical price data"""
        try:
            lookback_days = 90  # 90 days for cointegration analysis

            historical_data = await self.client.get_multiple_historical_klines(
                symbols=self.symbols,
                interval="1",  # 1 minute
                lookback_days=lookback_days
            )

            for symbol, klines in historical_data.items():
                if klines:
                    prices = pd.Series(
                        [k.close for k in klines],
                        index=[k.timestamp for k in klines]
                    )
                    # CRITICAL: Store prices in price_data for quant agent analysis
                    self.price_data[symbol] = prices
                    logger.info(f"Loaded {len(prices)} price points for {symbol}")

                    # Store OHLCV data in candle_data
                    df = pd.DataFrame([
                        {'open': k.open, 'high': k.high, 'low': k.low, 'close': k.close, 'volume': k.volume}
                        for k in klines
                    ], index=[k.timestamp for k in klines])  # Fixed index
                    self.candle_data[symbol] = df
                    logger.info(f"Loaded {len(df)} candles for {symbol}")
                else:
                    logger.warning(f"No historical data for {symbol}")

        except Exception as e:
            logger.error(f"Error loading historical data: {e}")

    async def _update_price_data(self):
        """Update price and candle data from MarketDataManager"""
        current_time = datetime.now()
        
        prices_updated = 0
        for symbol in self.symbols:
            # 1. Update Price (Ticks) from MarketData
            price = self.market_data.get_price(symbol)
            if price > 0:
                if symbol not in self.price_data:
                    self.price_data[symbol] = pd.Series(dtype=float)
                    logger.info(f"Initialized price_data for {symbol}")
                    
                # Throttle tick updates to 1s
                last_time = self.price_data[symbol].index[-1] if not self.price_data[symbol].empty else datetime.min
                if (current_time - last_time).total_seconds() >= 1:
                    new_data = pd.Series([price], index=[current_time])
                    self.price_data[symbol] = pd.concat([self.price_data[symbol], new_data])
                    prices_updated += 1
                    
                    # Keep last 10000 points
                    if len(self.price_data[symbol]) > 10000:
                        self.price_data[symbol] = self.price_data[symbol].iloc[-10000:]

            # 2. Update Candles (OHLCV) from MarketData - DISABLED (method not available)
            # candle = self.market_data.get_candle(symbol)
            # Candle data not needed - using tick data from WebSocket instead

    async def _main_loop(self):
        """Main trading loop"""
        iteration = 0

        while self.running:
            try:
                iteration += 1
                loop_start = datetime.now()

                logger.info(f"--- Iteration {iteration} ---")

                # 1. Update price data
                await self._update_price_data()

                # 2. Update open positions
                await self._update_positions()

                # 3. Get account balance
                account_balance = self.client.get_account_balance()
                logger.info(f"Account balance: ${account_balance:.2f}")

                # Update dashboard balance
                if DASHBOARD_ENABLED:
                    update_balance(account_balance)

                # 4. Make trading decisions (CONSENSUS LOGIC - Higher quality trades)
                current_positions = self.position_manager.get_all_positions()
                daily_pnl = self.position_manager.daily_pnl

                # Use consensus-based decision making
                decisions = await self.orchestrator.batch_make_decisions(
                    pairs=self.pairs,
                    price_data=self.price_data,
                    candle_data=self.candle_data,  # Pass candle data for Volume/ATR
                    current_positions=current_positions,
                    account_balance=account_balance,
                    daily_pnl=daily_pnl
                )


                logger.info(f"🔥 Got {len(decisions)} total decisions ({len([d for d in decisions if d['action'] != 'HOLD'])} actionable)")
                
                # Log first decision for debugging
                if decisions:
                    sample = decisions[0]
                    logger.info(f"Sample decision: {sample.get('pair_id', 'unknown')} -> {sample['action']} (conf: {sample['confidence']:.2f}, reason: {sample.get('reason', 'N/A')[:50]})")

                # 5. Execute ALL decisions in parallel (OR logic!)
                for decision in decisions:
                    # Decision already has pair info from orchestrator
                    await self._execute_decision(decision)

                    # Send pair data to dashboard
                    if DASHBOARD_ENABLED and 'pair' in decision:
                        pair = decision['pair']
                        pair_id = f"{pair['symbol_a']}_{pair['symbol_b']}"

                        # Get current prices
                        price_a = self.client.get_latest_price(pair['symbol_a']) or 0
                        price_b = self.client.get_latest_price(pair['symbol_b']) or 0

                        # Extract decision metadata
                        metadata = decision.get('metadata', {})

                        dashboard_pair_data = {
                            'zscore': metadata.get('zscore', 0),
                            'cointegration': {
                                'pvalue': metadata.get('pvalue', 1.0),
                                'hedge_ratio': metadata.get('hedge_ratio', 1.0),
                                'half_life': metadata.get('half_life')
                            },
                            'signal': decision.get('action', 'HOLD'),
                            'confidence': decision.get('confidence', 0),
                            'position_size_a': decision.get('position_size_a', 0),
                            'position_size_b': decision.get('position_size_b', 0),
                            'current_price_a': price_a,
                            'current_price_b': price_b,
                            'strategy': decision.get('strategy', 'unknown')  # Show which strategy triggered
                        }

                        update_dashboard(pair_id, dashboard_pair_data)

                # 6. Log statistics and update dashboard
                stats = self.position_manager.get_statistics()
                logger.info(
                    f"Stats: {stats['total_trades']} trades, "
                    f"Win rate: {stats['win_rate']*100:.1f}%, "
                    f"Total P&L: ${stats['total_pnl']:.2f}, "
                    f"Daily P&L: ${stats['daily_pnl']:.2f}"
                )

                # Update dashboard statistics
                if DASHBOARD_ENABLED:
                    stats['available_balance'] = account_balance
                    update_stats(stats)

                # Calculate loop time
                loop_time = (datetime.now() - loop_start).total_seconds()
                logger.info(f"Loop time: {loop_time:.2f}s")

                # Sleep until next iteration (1 second for HFT)
                sleep_time = max(0, 1 - loop_time)
                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(10)  # Wait before retrying

    async def _update_positions(self):
        """Update all open positions with current prices"""
        for position in self.position_manager.get_all_positions():
            try:
                # Get current prices
                price_a = self.client.get_latest_price(position.symbol_a)
                price_b = self.client.get_latest_price(position.symbol_b)

                if not price_a or not price_b:
                    continue

                # Calculate current spread and z-score
                current_spread = price_b - position.hedge_ratio * price_a

                # Get historical spread for z-score calculation
                if position.symbol_a in self.price_data and position.symbol_b in self.price_data:
                    hist_a = self.price_data[position.symbol_a]
                    hist_b = self.price_data[position.symbol_b]

                    hist_spread = hist_b - position.hedge_ratio * hist_a

                    # Simple z-score calculation
                    mean = hist_spread.mean()
                    std = hist_spread.std()
                    current_zscore = (current_spread - mean) / std if std > 0 else 0.0
                else:
                    current_zscore = 0.0

                # Update position
                self.position_manager.update_position(
                    pair_id=position.pair_id,
                    current_price_a=price_a,
                    current_price_b=price_b,
                    current_zscore=current_zscore
                )

            except Exception as e:
                logger.error(f"Error updating position {position.pair_id}: {e}")

    async def _execute_decision(self, decision: Dict):
        """Execute a trading decision"""
        try:
            action = decision['action']
            confidence = decision['confidence']

            if action == 'HOLD' or action == 'PAUSE':
                return

            # Extract pair info from metadata
            metadata = decision.get('metadata', {})
            pair_id = decision.get('pair_id')  # This would come from the decision

            # For demonstration, extract from available data
            # In production, ensure pair_id is in the decision

            if action == 'CLOSE':
                # Find and close position
                for position in self.position_manager.get_all_positions():
                    # Close position
                    success, result = await self.order_manager.execute_pair_exit(
                        pair_id=position.pair_id,
                        symbol_a=position.symbol_a,
                        symbol_b=position.symbol_b,
                        side_a=position.side_a,
                        side_b=position.side_b,
                        size_a=position.size_a,
                        size_b=position.size_b
                    )

                    if success:
                        self.position_manager.close_position(
                            pair_id=position.pair_id,
                            exit_price_a=result['exit_price_a'],
                            exit_price_b=result['exit_price_b'],
                            exit_zscore=position.current_zscore or 0.0,
                            reason=decision['reason']
                        )

            elif action in ['LONG_SPREAD', 'SHORT_SPREAD']:
                # Open new position - EXECUTE IMMEDIATELY!
                try:
                    # Robust symbol extraction
                    pair_data = decision.get('pair', {})
                    symbol_a = pair_data.get('symbol_a') or decision.get('symbol_a')
                    symbol_b = pair_data.get('symbol_b') or decision.get('symbol_b')
                    
                    if symbol_a and symbol_b:
                        pair_id = f"{symbol_a}_{symbol_b}"
                    else:
                        pair_id = decision.get('pair_id', '')
                    size_a = decision.get('position_size_a', 0)
                    size_b = decision.get('position_size_b', 0)
                    hedge_ratio = decision.get('hedge_ratio', 1.0)

                    if not symbol_a or not symbol_b:
                        logger.warning(f"Missing symbols for {action}")
                        logger.warning(f"Decision keys: {list(decision.keys())}")
                        logger.warning(f"Pair data: {decision.get('pair')}")
                        logger.debug(f"Full decision object: {decision}")
                        return

                    logger.info(f"🚀 EXECUTING {action} for {pair_id}! Size A: {size_a}, Size B: {size_b}")

                    # Execute the trade
                    success, result = await self.order_manager.execute_pair_entry(
                        pair_id=pair_id,
                        symbol_a=symbol_a,
                        symbol_b=symbol_b,
                        action=action,
                        size_a=size_a,
                        size_b=size_b,
                        hedge_ratio=hedge_ratio
                    )

                    if success:
                        # Track the position
                        self.position_manager.add_position(
                            pair_id=pair_id,
                            symbol_a=symbol_a,
                            symbol_b=symbol_b,
                            side_a=result['side_a'],
                            side_b=result['side_b'],
                            size_a=result['qty_a'],  # CRITICAL FIX: Use executed contract quantity!
                            size_b=result['qty_b'],  # CRITICAL FIX: Use executed contract quantity!
                            entry_price_a=result['entry_price_a'],
                            entry_price_b=result['entry_price_b'],
                            entry_zscore=decision.get('metadata', {}).get('zscore', 0),
                            hedge_ratio=hedge_ratio
                        )
                        logger.info(f"✅ {action} executed successfully for {pair_id}!")
                    else:
                        logger.error(f"❌ Failed to execute {action} for {pair_id}")

                except Exception as e:
                    logger.error(f"Error executing {action}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error executing decision: {e}")

    async def _close_all_positions(self):
        """Close all open positions"""
        for position in self.position_manager.get_all_positions():
            try:
                success, result = await self.order_manager.execute_pair_exit(
                    pair_id=position.pair_id,
                    symbol_a=position.symbol_a,
                    symbol_b=position.symbol_b,
                    side_a=position.side_a,
                    side_b=position.side_b,
                    size_a=position.size_a,
                    size_b=position.size_b
                )

                if success:
                    self.position_manager.close_position(
                        pair_id=position.pair_id,
                        exit_price_a=result['exit_price_a'],
                        exit_price_b=result['exit_price_b'],
                        exit_zscore=position.current_zscore or 0.0,
                        reason="System shutdown"
                    )

            except Exception as e:
                logger.error(f"Error closing position {position.pair_id}: {e}")


async def main():
    """Main entry point"""
    engine = TradingEngine()

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Interrupt received, stopping...")
        asyncio.create_task(engine.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start engine
    await engine.start()


if __name__ == "__main__":
    asyncio.run(main())
