"""Multi-Strategy Manager - Run multiple strategies simultaneously"""

import asyncio
from typing import List, Dict, Optional
import pandas as pd
from dataclasses import dataclass
import logging

from src.strategy.correlation_rsi_strategy import CorrelationRSIStrategy, StrategySignal
from src.strategy.mean_reversion_strategy import MeanReversionStrategy, MeanReversionSignal
from src.strategy.engle_granger_strategy import EngleGrangerStrategy, EngleGrangerSignal
from src.strategy.orderbook_imbalance_strategy import OrderBookImbalanceStrategy, OBISignal

logger = logging.getLogger(__name__)


@dataclass
class AggregatedSignal:
    """Aggregated signal from multiple strategies"""
    action: str  # LONG_SPREAD, SHORT_SPREAD, CLOSE, HOLD
    confidence: float  # Weighted average
    strategy_signals: Dict[str, Dict]  # Individual strategy outputs
    consensus: str  # STRONG, MODERATE, WEAK, CONFLICTING
    metadata: Dict  # Additional metadata from strategies


class StrategyManager:
    """
    Manages multiple trading strategies running simultaneously

    Aggregates signals from:
    1. Engle-Granger Cointegration (academic paper-based, weight 40%)
    2. Order Book Imbalance (HFT microstructure, weight 30%)
    3. Correlation + RSI strategy (fast, weight 20%)
    4. Mean Reversion (Bollinger Bands) strategy (simple, weight 10%)

    Voting system:
    - If 2+ strategies agree: Execute with combined confidence
    - If strategies conflict: HOLD or use highest confidence
    - Engle-Granger has veto power (if it says NOT cointegrated, HOLD)
    - Track individual strategy performance
    """

    def __init__(self):
        # Initialize all strategies
        self.strategies = {
            'engle_granger': EngleGrangerStrategy(),  # Cointegration - academic rigor
            'orderbook_imbalance': OrderBookImbalanceStrategy(),  # HFT microstructure
            'correlation_rsi': CorrelationRSIStrategy(),  # Fast signals
            'mean_reversion': MeanReversionStrategy()  # Simple mean reversion
        }

        # Strategy weights (based on theoretical soundness and HFT requirements)
        # Engle-Granger: Highest - proven cointegration methodology
        # OBI: High - exploits real-time order flow (HFT advantage)
        # Correlation+RSI: Medium - fast but noisy
        # Mean Reversion: Lower - simple baseline
        self.weights = {
            'engle_granger': 0.4,  # Academic rigor
            'orderbook_imbalance': 0.3,  # HFT edge - order flow
            'correlation_rsi': 0.2,  # Fast signals
            'mean_reversion': 0.1  # Baseline
        }

        # Track strategy performance
        self.performance = {
            'engle_granger': {'trades': 0, 'wins': 0, 'pnl': 0.0},
            'orderbook_imbalance': {'trades': 0, 'wins': 0, 'pnl': 0.0},
            'correlation_rsi': {'trades': 0, 'wins': 0, 'pnl': 0.0},
            'mean_reversion': {'trades': 0, 'wins': 0, 'pnl': 0.0}
        }

        logger.info("Strategy Manager initialized with 4 strategies (Engle-Granger, OBI, Correlation+RSI, Mean Reversion)")

    async def generate_aggregated_signal(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        pair_id: str,
        candles_a: Optional[pd.DataFrame] = None,  # Added
        candles_b: Optional[pd.DataFrame] = None,  # Added
        current_position: Optional[str] = None,
        orderbook_a: Optional[Dict] = None,
        orderbook_b: Optional[Dict] = None
    ) -> AggregatedSignal:
        """
        Generate aggregated signal from all strategies

        Args:
            prices_a: Price series for symbol A
            prices_b: Price series for symbol B
            pair_id: Pair identifier
            candles_a: Candlestick data for symbol A (for breakout detection)
            candles_b: Candlestick data for symbol B (for breakout detection)
            current_position: Current position if any

        Returns:
            AggregatedSignal with consensus action
        """
        signals = {}

        # Run all strategies in parallel
        tasks = []
        for name, strategy in self.strategies.items():
            task = self._run_strategy(name, strategy, prices_a, prices_b, current_position, orderbook_a, orderbook_b)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Collect signals
        for name, signal in results:
            signals[name] = signal
            
        # Check for Breakouts (Volume + ATR) - User Request
        # If strong breakout detected, it can override or confirm signals
        breakout_detected = False
        if candles_a is not None and not candles_a.empty and 'volume' in candles_a.columns:
            if self.check_breakout(prices_a, candles_a['volume']):
                breakout_detected = True
                
        if candles_b is not None and not candles_b.empty and 'volume' in candles_b.columns:
            if self.check_breakout(prices_b, candles_b['volume']):
                breakout_detected = True
                
        # Aggregate signals
        aggregated = self._aggregate_signals(signals, pair_id)
        
        # Boost confidence if breakout detected
        if breakout_detected and aggregated.action != 'HOLD':
            aggregated.confidence = min(1.0, aggregated.confidence * 1.2)
            aggregated.consensus = 'STRONG'
            
        return aggregated

    async def _run_strategy(self, name, strategy, prices_a, prices_b, current_position, orderbook_a=None, orderbook_b=None):
        """Run a single strategy"""
        try:
            # OBI strategy needs order book data
            if name == 'orderbook_imbalance':
                signal = strategy.generate_signal(
                    prices_a, prices_b, current_position,
                    orderbook_a=orderbook_a, orderbook_b=orderbook_b
                )
            else:
                signal = strategy.generate_signal(prices_a, prices_b, current_position)

            # Convert to dict for aggregation
            signal_dict = {
                'action': signal.action,
                'confidence': signal.confidence,
                'details': signal.__dict__
            }

            return (name, signal_dict)

        except Exception as e:
            logger.error(f"Error in strategy {name}: {e}")
            return (name, {'action': 'HOLD', 'confidence': 0.0, 'details': {}})

    def _aggregate_signals(self, signals: Dict, pair_id: str) -> AggregatedSignal:
        """
        Aggregate signals using voting + confidence weighting

        Logic:
        1. Count votes for each action
        2. Weight by strategy confidence and performance
        3. Determine consensus level
        """
        actions = {}
        total_weight = 0

        for name, signal in signals.items():
            action = signal['action']
            confidence = signal['confidence']
            weight = self.weights[name]

            # Weight by confidence and strategy weight
            weighted_confidence = confidence * weight

            if action not in actions:
                actions[action] = {
                    'count': 0,
                    'total_confidence': 0.0,
                    'strategies': []
                }

            actions[action]['count'] += 1
            actions[action]['total_confidence'] += weighted_confidence
            actions[action]['strategies'].append(name)
            total_weight += weight

        # Find dominant action
        if not actions:
            return AggregatedSignal(
                action='HOLD',
                confidence=0.0,
                strategy_signals=signals,
                consensus='NONE',
                metadata={}
            )

        # Sort by confidence
        sorted_actions = sorted(
            actions.items(),
            key=lambda x: (x[1]['count'], x[1]['total_confidence']),
            reverse=True
        )

        dominant_action, details = sorted_actions[0]

        # Calculate consensus
        if details['count'] == len(self.strategies):
            consensus = 'STRONG'  # All strategies agree
        elif details['count'] >= len(self.strategies) / 2:
            consensus = 'MODERATE'  # Majority agrees
        elif details['total_confidence'] > 0.7:
            consensus = 'MODERATE'  # High confidence from one strategy
        else:
            # Check for conflicts
            if len(actions) > 2:
                consensus = 'CONFLICTING'
                dominant_action = 'HOLD'  # Hold on conflicts
            else:
                consensus = 'WEAK'

        # Calculate weighted confidence
        avg_confidence = details['total_confidence'] / total_weight if total_weight > 0 else 0.0

        logger.info(f"[{pair_id}] Aggregated Signal: {dominant_action} "
                   f"(confidence: {avg_confidence:.2f}, consensus: {consensus})")
        logger.info(f"  Individual signals: {[(k, v['action'], v['confidence']) for k, v in signals.items()]}")

        # Collect metadata from all strategies
        metadata = {
            'strategies': list(signals.keys()),
            'votes': {action: data['count'] for action, data in actions.items()},
            'agreeing_strategies': details['strategies']
        }

        return AggregatedSignal(
            action=dominant_action,
            confidence=avg_confidence,
            strategy_signals=signals,
            consensus=consensus,
            metadata=metadata
        )

    def update_strategy_performance(self, strategy_name: str, pnl: float):
        """Update strategy performance after trade"""
        if strategy_name in self.performance:
            self.performance[strategy_name]['trades'] += 1
            self.performance[strategy_name]['pnl'] += pnl
            if pnl > 0:
                self.performance[strategy_name]['wins'] += 1

            # Update weights based on performance
            self._update_weights()

    def _update_weights(self):
        """Dynamically adjust weights based on performance"""
        # Simple approach: Better performing strategies get more weight
        total_pnl = sum(s['pnl'] for s in self.performance.values())

        if total_pnl > 0:
            for name, perf in self.performance.items():
                if perf['trades'] > 10:  # Only adjust after 10 trades
                    win_rate = perf['wins'] / perf['trades']
                    # Adjust weight: 0.3 to 0.7 range
                    self.weights[name] = 0.3 + (0.4 * win_rate)

        # Normalize weights
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            for name in self.weights:
                self.weights[name] /= total_weight

    def get_performance_summary(self) -> Dict:
        """Get performance summary for all strategies"""
        summary = {}
        for name, perf in self.performance.items():
            win_rate = perf['wins'] / perf['trades'] if perf['trades'] > 0 else 0.0
            summary[name] = {
                **perf,
                'win_rate': win_rate,
                'weight': self.weights[name]
            }
        return summary

    def calculate_atr(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate Average True Range (ATR)"""
        high = prices.rolling(window=2).max()
        low = prices.rolling(window=2).min()
        close = prices.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        return atr

    def check_breakout(self, prices: pd.Series, volume: pd.Series) -> bool:
        """
        Check for Volume + ATR Breakout
        Returns True if breakout detected (strong move)
        """
        if len(prices) < 20 or len(volume) < 20:
            return False
            
        # 1. Volume Surge: Current volume > 2x average
        avg_volume = volume.rolling(window=20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_surge = current_volume > (avg_volume * 2.0)
        
        # 2. ATR Expansion: Current range > 1.5x ATR
        atr = self.calculate_atr(prices)
        current_range = prices.iloc[-1] - prices.iloc[-2]
        range_expansion = abs(current_range) > (atr * 1.5)
        
        return volume_surge and range_expansion
    def get_strategy_signals(self) -> Dict:
        """Get current signals from all strategies (for UI display)"""
        return {
            name: {
                'name': name,
                'weight': self.weights[name],
                'performance': self.performance[name]
            }
            for name in self.strategies.keys()
        }

    async def generate_all_individual_signals(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        pair_id: str,
        current_position: Optional[str] = None,
        orderbook_a: Optional[Dict] = None,
        orderbook_b: Optional[Dict] = None
    ) -> Dict[str, Dict]:
        """
        Generate signals from ALL strategies WITHOUT aggregation (OR logic)

        Returns each strategy's signal independently for parallel execution

        Args:
            prices_a: Price series for symbol A
            prices_b: Price series for symbol B
            pair_id: Pair identifier
            current_position: Current position if any
            orderbook_a: Order book for symbol A
            orderbook_b: Order book for symbol B

        Returns:
            Dict of {strategy_name: signal_dict} for all strategies
        """
        signals = {}

        # Run all strategies in parallel
        tasks = []
        for name, strategy in self.strategies.items():
            task = self._run_strategy(name, strategy, prices_a, prices_b, current_position, orderbook_a, orderbook_b)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        # Collect all signals
        for name, signal in results:
            # Only include signals that are actionable (not HOLD or have confidence > 0.3)
            if signal['action'] != 'HOLD' and signal['confidence'] > 0.3:
                signals[name] = signal
                logger.info(f"[{pair_id}] {name}: {signal['action']} (confidence: {signal['confidence']:.2f})")

        return signals
