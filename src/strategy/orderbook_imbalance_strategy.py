"""Order Book Imbalance (OBI) Strategy

HFT strategy based on order book bid/ask volume imbalance.

Methodology:
1. Monitor top 5 depth levels of order book
2. Calculate Imbalance Ratio = (Bid Volume - Ask Volume) / (Bid Volume + Ask Volume)
3. Entry: Imbalance > 0.3 (strong buy pressure) or < -0.3 (strong sell pressure)
4. Exit: 0.1% profit target OR 0.05% stop loss
5. Kill switch: If loses >2% in 5 minutes, pause strategy

Entry Logic:
- Imbalance > 0.3 → LONG SPREAD (buy pressure on A, sell B)
- Imbalance < -0.3 → SHORT SPREAD (sell pressure on A, buy B)

Exit Logic:
- Take profit: 0.1% gain
- Stop loss: 0.05% loss
- Time-based: Max 2 minutes per trade (HFT scalping)
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class OBISignal:
    """Order Book Imbalance signal output"""
    action: str  # LONG_SPREAD, SHORT_SPREAD, CLOSE, HOLD
    confidence: float  # 0.0 to 1.0
    imbalance_ratio: float  # -1.0 to 1.0
    bid_volume: float
    ask_volume: float
    bid_pressure: float  # Bid volume as % of total
    ask_pressure: float  # Ask volume as % of total
    entry_reason: str


class OrderBookImbalanceStrategy:
    """
    HFT Order Book Imbalance Strategy

    ULTRA AGGRESSIVE MODE:
    - Imbalance threshold: 0.3 (30% imbalance)
    - Profit target: 0.1% (10 basis points)
    - Stop loss: 0.05% (5 basis points)
    - Max trade duration: 2 minutes
    - Kill switch: 2% loss in 5 minutes

    Theory:
    Order book imbalance predicts short-term price movements.
    High bid volume → price likely to rise
    High ask volume → price likely to fall
    """

    def __init__(
        self,
        depth_levels: int = 5,  # Monitor top 5 levels
        imbalance_threshold: float = 0.3,  # 30% imbalance triggers trade
        profit_target_pct: float = 0.001,  # 0.1% profit target
        stop_loss_pct: float = 0.0005,  # 0.05% stop loss
        max_trade_duration_seconds: int = 120,  # 2 minutes max
        kill_switch_loss_pct: float = 0.02,  # 2% max loss
        kill_switch_window_minutes: int = 5,  # in 5 minutes
        lookback_periods: int = 10  # For smoothing imbalance
    ):
        self.depth_levels = depth_levels
        self.imbalance_threshold = imbalance_threshold
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_trade_duration_seconds = max_trade_duration_seconds
        self.kill_switch_loss_pct = kill_switch_loss_pct
        self.kill_switch_window_minutes = kill_switch_window_minutes
        self.lookback_periods = lookback_periods

        # Track recent losses for kill switch
        self.recent_losses = deque(maxlen=100)  # Last 100 trades
        self.paused_until = None

        # Track entry time and price for exit logic
        self.entry_time: Optional[datetime] = None
        self.entry_price_a: Optional[float] = None
        self.entry_price_b: Optional[float] = None

        # Imbalance history for smoothing
        self.imbalance_history = deque(maxlen=self.lookback_periods)

    def calculate_orderbook_imbalance(
        self,
        orderbook_a: Dict,
        orderbook_b: Dict
    ) -> Tuple[float, float, float]:
        """
        Calculate order book imbalance ratio

        Imbalance Ratio = (Bid Volume - Ask Volume) / (Bid Volume + Ask Volume)

        Returns:
            - imbalance_ratio: -1.0 to 1.0
            - total_bid_volume: Sum of bid volumes
            - total_ask_volume: Sum of ask volumes
        """
        try:
            # Extract bids and asks from order book
            # Assuming orderbook format: {'bids': [[price, size], ...], 'asks': [[price, size], ...]}

            if not orderbook_a or not orderbook_b:
                return 0.0, 0.0, 0.0

            # Get bids and asks for symbol A (top N levels)
            bids_a = orderbook_a.get('bids', [])[:self.depth_levels]
            asks_a = orderbook_a.get('asks', [])[:self.depth_levels]

            # Calculate total volumes (multiply price * size for USD value)
            bid_volume_a = sum(float(price) * float(size) for price, size in bids_a)
            ask_volume_a = sum(float(price) * float(size) for price, size in asks_a)

            # For pair trading, we care about relative imbalance between A and B
            # Simplified: Use symbol A's order book imbalance
            total_volume = bid_volume_a + ask_volume_a

            if total_volume == 0:
                return 0.0, 0.0, 0.0

            # Imbalance ratio
            imbalance_ratio = (bid_volume_a - ask_volume_a) / total_volume

            return float(imbalance_ratio), float(bid_volume_a), float(ask_volume_a)

        except Exception as e:
            logger.error(f"Error calculating order book imbalance: {e}")
            return 0.0, 0.0, 0.0

    def check_kill_switch(self) -> bool:
        """
        Check if kill switch should be activated

        Returns True if strategy should be paused
        """
        try:
            # If already paused, check if pause period is over
            if self.paused_until:
                if datetime.now() < self.paused_until:
                    return True  # Still paused
                else:
                    self.paused_until = None  # Resume
                    logger.info("Kill switch period ended, resuming OBI strategy")
                    return False

            # Check losses in recent window
            cutoff_time = datetime.now() - timedelta(minutes=self.kill_switch_window_minutes)

            recent_losses_in_window = [
                loss for loss_time, loss in self.recent_losses
                if loss_time > cutoff_time
            ]

            if not recent_losses_in_window:
                return False

            total_loss_pct = sum(recent_losses_in_window)

            if total_loss_pct < -self.kill_switch_loss_pct:
                # Activate kill switch
                self.paused_until = datetime.now() + timedelta(minutes=10)
                logger.warning(
                    f"🚨 KILL SWITCH ACTIVATED! Lost {total_loss_pct*100:.2f}% in "
                    f"{self.kill_switch_window_minutes} minutes. Pausing for 10 minutes."
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking kill switch: {e}")
            return False

    def check_exit_conditions(
        self,
        current_price_a: float,
        current_price_b: float,
        current_position: Optional[str] = None
    ) -> Tuple[bool, str, float]:
        """
        Check if exit conditions are met

        Returns:
            - should_exit: bool
            - exit_reason: str
            - pnl_pct: float (for tracking)
        """
        if not current_position or not self.entry_time:
            return False, '', 0.0

        try:
            # Calculate P&L
            # For LONG_SPREAD: Long A, Short B
            # For SHORT_SPREAD: Short A, Long B

            if current_position == 'LONG_SPREAD':
                pnl_a = (current_price_a - self.entry_price_a) / self.entry_price_a
                pnl_b = (self.entry_price_b - current_price_b) / self.entry_price_b
            elif current_position == 'SHORT_SPREAD':
                pnl_a = (self.entry_price_a - current_price_a) / self.entry_price_a
                pnl_b = (current_price_b - self.entry_price_b) / self.entry_price_b
            else:
                return False, '', 0.0

            # Average P&L
            avg_pnl = (pnl_a + pnl_b) / 2

            # Check profit target
            if avg_pnl >= self.profit_target_pct:
                return True, f'Profit target hit: {avg_pnl*100:.3f}%', avg_pnl

            # Check stop loss
            if avg_pnl <= -self.stop_loss_pct:
                return True, f'Stop loss hit: {avg_pnl*100:.3f}%', avg_pnl

            # Check max duration
            time_in_trade = (datetime.now() - self.entry_time).total_seconds()
            if time_in_trade > self.max_trade_duration_seconds:
                return True, f'Max duration hit: {time_in_trade:.0f}s', avg_pnl

            return False, '', avg_pnl

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return False, '', 0.0

    def generate_signal(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        current_position: Optional[str] = None,
        orderbook_a: Optional[Dict] = None,
        orderbook_b: Optional[Dict] = None
    ) -> OBISignal:
        """
        Generate trading signal based on order book imbalance

        Args:
            prices_a: Price series for symbol A
            prices_b: Price series for symbol B
            current_position: Current position if any
            orderbook_a: Order book for symbol A (bids/asks)
            orderbook_b: Order book for symbol B (bids/asks)

        Returns:
            OBISignal with action and metadata
        """
        try:
            # Check kill switch
            if self.check_kill_switch():
                return OBISignal(
                    action='HOLD',
                    confidence=0.0,
                    imbalance_ratio=0.0,
                    bid_volume=0.0,
                    ask_volume=0.0,
                    bid_pressure=0.0,
                    ask_pressure=0.0,
                    entry_reason='Kill switch activated'
                )

            # Exit conditions (if holding position)
            if current_position:
                # Get current prices
                current_price_a = float(prices_a.iloc[-1]) if len(prices_a) > 0 else 0.0
                current_price_b = float(prices_b.iloc[-1]) if len(prices_b) > 0 else 0.0

                should_exit, exit_reason, pnl_pct = self.check_exit_conditions(
                    current_price_a, current_price_b, current_position
                )

                if should_exit:
                    # Track loss for kill switch
                    if pnl_pct < 0:
                        self.recent_losses.append((datetime.now(), pnl_pct))

                    # Reset entry tracking
                    self.entry_time = None
                    self.entry_price_a = None
                    self.entry_price_b = None

                    return OBISignal(
                        action='CLOSE',
                        confidence=0.95,
                        imbalance_ratio=0.0,
                        bid_volume=0.0,
                        ask_volume=0.0,
                        bid_pressure=0.0,
                        ask_pressure=0.0,
                        entry_reason=exit_reason
                    )

                # Hold position
                return OBISignal(
                    action='HOLD',
                    confidence=0.5,
                    imbalance_ratio=0.0,
                    bid_volume=0.0,
                    ask_volume=0.0,
                    bid_pressure=0.0,
                    ask_pressure=0.0,
                    entry_reason=f'Holding position (P&L: {pnl_pct*100:.3f}%)'
                )

            # Entry signals (no current position)

            # Need order book data
            if not orderbook_a:
                return OBISignal(
                    action='HOLD',
                    confidence=0.0,
                    imbalance_ratio=0.0,
                    bid_volume=0.0,
                    ask_volume=0.0,
                    bid_pressure=0.0,
                    ask_pressure=0.0,
                    entry_reason='No order book data available'
                )

            # Calculate imbalance
            imbalance_ratio, bid_volume, ask_volume = self.calculate_orderbook_imbalance(
                orderbook_a, orderbook_b
            )

            # Add to history for smoothing
            self.imbalance_history.append(imbalance_ratio)

            # Calculate smoothed imbalance (moving average)
            if len(self.imbalance_history) >= 3:
                smoothed_imbalance = np.mean(list(self.imbalance_history))
            else:
                smoothed_imbalance = imbalance_ratio

            # Calculate bid/ask pressure
            total_volume = bid_volume + ask_volume
            if total_volume > 0:
                bid_pressure = bid_volume / total_volume
                ask_pressure = ask_volume / total_volume
            else:
                bid_pressure = 0.5
                ask_pressure = 0.5

            logger.info(
                f"OBI: Imbalance={smoothed_imbalance:.3f} (raw={imbalance_ratio:.3f}), "
                f"Bid={bid_volume:.0f}, Ask={ask_volume:.0f}, "
                f"Pressure: {bid_pressure*100:.1f}% / {ask_pressure*100:.1f}%"
            )

            # LONG SPREAD: Strong buy pressure (imbalance > threshold)
            # Interpretation: A has strong bid volume, likely to rise vs B
            if smoothed_imbalance > self.imbalance_threshold:
                # Set entry tracking
                self.entry_time = datetime.now()
                self.entry_price_a = float(prices_a.iloc[-1]) if len(prices_a) > 0 else 0.0
                self.entry_price_b = float(prices_b.iloc[-1]) if len(prices_b) > 0 else 0.0

                # Confidence based on imbalance strength
                confidence = min(0.95, 0.6 + abs(smoothed_imbalance) * 0.5)

                return OBISignal(
                    action='LONG_SPREAD',
                    confidence=confidence,
                    imbalance_ratio=smoothed_imbalance,
                    bid_volume=bid_volume,
                    ask_volume=ask_volume,
                    bid_pressure=bid_pressure,
                    ask_pressure=ask_pressure,
                    entry_reason=(
                        f'Strong buy pressure: Imbalance={smoothed_imbalance:.3f} > {self.imbalance_threshold} '
                        f'(Bid pressure: {bid_pressure*100:.1f}%)'
                    )
                )

            # SHORT SPREAD: Strong sell pressure (imbalance < -threshold)
            # Interpretation: A has strong ask volume, likely to fall vs B
            if smoothed_imbalance < -self.imbalance_threshold:
                # Set entry tracking
                self.entry_time = datetime.now()
                self.entry_price_a = float(prices_a.iloc[-1]) if len(prices_a) > 0 else 0.0
                self.entry_price_b = float(prices_b.iloc[-1]) if len(prices_b) > 0 else 0.0

                confidence = min(0.95, 0.6 + abs(smoothed_imbalance) * 0.5)

                return OBISignal(
                    action='SHORT_SPREAD',
                    confidence=confidence,
                    imbalance_ratio=smoothed_imbalance,
                    bid_volume=bid_volume,
                    ask_volume=ask_volume,
                    bid_pressure=bid_pressure,
                    ask_pressure=ask_pressure,
                    entry_reason=(
                        f'Strong sell pressure: Imbalance={smoothed_imbalance:.3f} < -{self.imbalance_threshold} '
                        f'(Ask pressure: {ask_pressure*100:.1f}%)'
                    )
                )

            # Moderate signals (70% of threshold)
            moderate_threshold = self.imbalance_threshold * 0.7

            if smoothed_imbalance > moderate_threshold:
                return OBISignal(
                    action='LONG_SPREAD',
                    confidence=0.65,
                    imbalance_ratio=smoothed_imbalance,
                    bid_volume=bid_volume,
                    ask_volume=ask_volume,
                    bid_pressure=bid_pressure,
                    ask_pressure=ask_pressure,
                    entry_reason=f'Moderate buy pressure: Imbalance={smoothed_imbalance:.3f}'
                )

            if smoothed_imbalance < -moderate_threshold:
                return OBISignal(
                    action='SHORT_SPREAD',
                    confidence=0.65,
                    imbalance_ratio=smoothed_imbalance,
                    bid_volume=bid_volume,
                    ask_volume=ask_volume,
                    bid_pressure=bid_pressure,
                    ask_pressure=ask_pressure,
                    entry_reason=f'Moderate sell pressure: Imbalance={smoothed_imbalance:.3f}'
                )

            # No signal
            return OBISignal(
                action='HOLD',
                confidence=0.5,
                imbalance_ratio=smoothed_imbalance,
                bid_volume=bid_volume,
                ask_volume=ask_volume,
                bid_pressure=bid_pressure,
                ask_pressure=ask_pressure,
                entry_reason=f'No clear imbalance: {smoothed_imbalance:.3f} within neutral range'
            )

        except Exception as e:
            logger.error(f"Error generating OBI signal: {e}", exc_info=True)
            return OBISignal(
                action='HOLD',
                confidence=0.0,
                imbalance_ratio=0.0,
                bid_volume=0.0,
                ask_volume=0.0,
                bid_pressure=0.0,
                ask_pressure=0.0,
                entry_reason=f'Error: {str(e)}'
            )
