"""Signal generation for pairs trading"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from src.data.models import Signal, TradeSignal, CointegrationResult, ZScoreData
from src.strategy.cointegration import CointegrationAnalyzer
from src.strategy.zscore import ZScoreCalculator
from src.config import config

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Generate trading signals for pairs"""

    def __init__(self):
        self.zscore_config = config.zscore
        self.coint_config = config.cointegration

        self.coint_analyzer = CointegrationAnalyzer(
            pvalue_threshold=self.coint_config.pvalue_threshold
        )
        self.zscore_calculator = ZScoreCalculator(
            lookback_period=config.settings.cointegration_window
        )

    def generate_signal(
        self,
        symbol_a: str,
        symbol_b: str,
        price_history_a: pd.Series,
        price_history_b: pd.Series,
        current_position: Optional[str] = None,
        sentiment_score: Optional[float] = None
    ) -> Optional[Signal]:
        """
        Generate trading signal for a pair

        Args:
            symbol_a: First symbol
            symbol_b: Second symbol
            price_history_a: Price history for symbol A
            price_history_b: Price history for symbol B
            current_position: Current position ('long_spread', 'short_spread', or None)
            sentiment_score: Sentiment score from sentiment agent (-1 to 1)

        Returns:
            Signal object or None if no signal
        """
        try:
            if len(price_history_a) < 30 or len(price_history_b) < 30:
                logger.debug("Insufficient price history for signal generation")
                return None

            # Test cointegration
            is_coint, pvalue, _, hedge_ratio, half_life = self.coint_analyzer.test_cointegration(
                price_history_a,
                price_history_b
            )

            if not is_coint:
                logger.debug(f"{symbol_a}/{symbol_b} not cointegrated (p-value: {pvalue:.4f})")

                # If we have a position and cointegration breaks, signal to close
                if current_position:
                    return Signal(
                        pair_id=f"{symbol_a}_{symbol_b}",
                        timestamp=datetime.now(),
                        signal=TradeSignal.CLOSE,
                        zscore=0.0,
                        spread=0.0,
                        hedge_ratio=hedge_ratio,
                        confidence=0.0,
                        sentiment_score=sentiment_score,
                        reason="Cointegration breakdown"
                    )
                return None

            # Calculate spread and z-score
            spread = self.coint_analyzer.calculate_spread(
                price_history_a,
                price_history_b,
                hedge_ratio
            )

            current_spread = float(spread.iloc[-1])
            zscore = self.zscore_calculator.calculate_current_zscore(
                current_spread,
                spread[:-1]  # Use historical spread for calculation
            )

            # Get signal from z-score
            signal_str = self.zscore_calculator.get_signal_from_zscore(
                zscore,
                entry_threshold=self.zscore_config.entry_threshold,
                exit_threshold=self.zscore_config.exit_threshold,
                stop_loss_threshold=self.zscore_config.stoploss_threshold
            )

            # Map string signal to TradeSignal enum
            signal_map = {
                'long_spread': TradeSignal.LONG_SPREAD,
                'short_spread': TradeSignal.SHORT_SPREAD,
                'close': TradeSignal.CLOSE,
                'hold': TradeSignal.HOLD
            }
            signal = signal_map.get(signal_str, TradeSignal.HOLD)

            # Calculate confidence
            confidence = self._calculate_confidence(
                zscore=zscore,
                pvalue=pvalue,
                half_life=half_life,
                sentiment_score=sentiment_score
            )

            # Apply sentiment filter
            if sentiment_score is not None:
                signal, reason = self._apply_sentiment_filter(
                    signal,
                    zscore,
                    sentiment_score
                )
            else:
                reason = f"Z-score: {zscore:.2f}, Hedge ratio: {hedge_ratio:.4f}"

            # Don't generate duplicate signals
            if signal == TradeSignal.HOLD and not current_position:
                return None

            # If we have a position and signal is to enter opposite, close first
            if current_position:
                if (current_position == 'long_spread' and signal == TradeSignal.SHORT_SPREAD) or \
                   (current_position == 'short_spread' and signal == TradeSignal.LONG_SPREAD):
                    signal = TradeSignal.CLOSE
                    reason = "Reversing position"

            return Signal(
                pair_id=f"{symbol_a}_{symbol_b}",
                timestamp=datetime.now(),
                signal=signal,
                zscore=zscore,
                spread=current_spread,
                hedge_ratio=hedge_ratio,
                confidence=confidence,
                sentiment_score=sentiment_score,
                reason=reason
            )

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None

    def _calculate_confidence(
        self,
        zscore: float,
        pvalue: float,
        half_life: Optional[float],
        sentiment_score: Optional[float]
    ) -> float:
        """
        Calculate confidence score for signal (0 to 1)

        Factors:
        - Z-score magnitude (higher = more confident)
        - Cointegration p-value (lower = more confident)
        - Half-life (reasonable range = more confident)
        - Sentiment alignment (aligned = more confident)
        """
        confidence = 0.0

        # Z-score component (0 to 0.4)
        zscore_abs = abs(zscore)
        if zscore_abs > 3.0:
            zscore_confidence = 0.4
        elif zscore_abs > 2.0:
            zscore_confidence = 0.2 + (zscore_abs - 2.0) * 0.2
        else:
            zscore_confidence = zscore_abs * 0.1

        confidence += zscore_confidence

        # Cointegration component (0 to 0.3)
        coint_confidence = max(0, 0.3 * (1 - pvalue / 0.05))
        confidence += coint_confidence

        # Half-life component (0 to 0.2)
        if half_life:
            # Prefer half-life between 60 and 1440 minutes (1 hour to 1 day)
            if 60 <= half_life <= 1440:
                half_life_confidence = 0.2
            elif 30 <= half_life < 60 or 1440 < half_life <= 2880:
                half_life_confidence = 0.1
            else:
                half_life_confidence = 0.0
            confidence += half_life_confidence

        # Sentiment component (0 to 0.1)
        if sentiment_score is not None:
            # Sentiment aligned with signal
            sentiment_confidence = min(0.1, abs(sentiment_score) * 0.1)
            confidence += sentiment_confidence

        return float(np.clip(confidence, 0, 1))

    def _apply_sentiment_filter(
        self,
        signal: TradeSignal,
        zscore: float,
        sentiment_score: float
    ) -> tuple[TradeSignal, str]:
        """
        Apply sentiment filter to signal

        If sentiment strongly contradicts statistical signal, reduce confidence or hold
        """
        # Strong negative sentiment
        if sentiment_score < -0.5:
            if signal == TradeSignal.LONG_SPREAD:
                # Statistical signal says long, but sentiment is very negative
                return TradeSignal.HOLD, f"Negative sentiment ({sentiment_score:.2f}) contradicts signal"

        # Strong positive sentiment
        elif sentiment_score > 0.5:
            if signal == TradeSignal.SHORT_SPREAD:
                # Statistical signal says short, but sentiment is very positive
                return TradeSignal.HOLD, f"Positive sentiment ({sentiment_score:.2f}) contradicts signal"

        # Sentiment aligns or is neutral
        reason = f"Z-score: {zscore:.2f}, Sentiment: {sentiment_score:.2f}"
        return signal, reason

    def batch_generate_signals(
        self,
        pairs: list[Dict[str, Any]],
        price_data: Dict[str, pd.Series],
        current_positions: Dict[str, str],
        sentiment_data: Dict[str, float]
    ) -> list[Signal]:
        """
        Generate signals for multiple pairs

        Args:
            pairs: List of pair configurations
            price_data: Dictionary of symbol -> price history
            current_positions: Dictionary of pair_id -> position side
            sentiment_data: Dictionary of symbol -> sentiment score

        Returns:
            List of signals
        """
        signals = []

        for pair in pairs:
            if not pair.get('enabled', True):
                continue

            symbol_a = pair['symbol_a']
            symbol_b = pair['symbol_b']
            pair_id = f"{symbol_a}_{symbol_b}"

            if symbol_a not in price_data or symbol_b not in price_data:
                logger.warning(f"Missing price data for {pair_id}")
                continue

            # Get sentiment for reference asset
            reference = pair.get('reference', symbol_a[:3])  # e.g., 'BTC' from 'BTCUSDT'
            sentiment_score = sentiment_data.get(reference)

            signal = self.generate_signal(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                price_history_a=price_data[symbol_a],
                price_history_b=price_data[symbol_b],
                current_position=current_positions.get(pair_id),
                sentiment_score=sentiment_score
            )

            if signal:
                signals.append(signal)

        return signals


class SignalValidator:
    """Validate trading signals before execution"""

    def __init__(self):
        self.min_confidence = 0.3
        self.max_concurrent_signals = 5

    def validate_signal(
        self,
        signal: Signal,
        current_positions_count: int,
        account_balance: float,
        daily_pnl: float
    ) -> tuple[bool, str]:
        """
        Validate signal before execution

        Returns:
            - is_valid: bool
            - reason: str
        """
        # Check confidence
        if signal.confidence < self.min_confidence:
            return False, f"Low confidence: {signal.confidence:.2f}"

        # Check max concurrent positions
        if signal.signal in [TradeSignal.LONG_SPREAD, TradeSignal.SHORT_SPREAD]:
            if current_positions_count >= self.max_concurrent_signals:
                return False, "Maximum concurrent positions reached"

        # Check daily loss limit
        if daily_pnl < -config.trading.daily_loss_limit:
            return False, f"Daily loss limit reached: ${daily_pnl:.2f}"

        # Check account balance
        if account_balance < config.trading.max_position_size:
            return False, f"Insufficient balance: ${account_balance:.2f}"

        return True, "Valid"

    def filter_signals(
        self,
        signals: list[Signal],
        max_signals: int = 5
    ) -> list[Signal]:
        """
        Filter and prioritize signals

        Returns top N signals by confidence
        """
        # Filter by confidence
        valid_signals = [s for s in signals if s.confidence >= self.min_confidence]

        # Sort by confidence (descending)
        valid_signals.sort(key=lambda x: x.confidence, reverse=True)

        # Return top N
        return valid_signals[:max_signals]
