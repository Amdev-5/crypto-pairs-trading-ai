"""Correlation + RSI Mean Reversion Strategy for 1m timeframe"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StrategySignal:
    """Strategy signal output"""
    action: str  # LONG_SPREAD, SHORT_SPREAD, CLOSE, HOLD
    confidence: float  # 0.0 to 1.0
    correlation: float
    rsi_a: float
    rsi_b: float
    zscore: float
    entry_reason: str


class CorrelationRSIStrategy:
    """
    Aggressive correlation + RSI mean reversion strategy

    Strategy Logic:
    1. Check correlation between pairs (must be > threshold)
    2. Calculate RSI for each symbol
    3. Calculate z-score of price ratio
    4. Entry signals:
       - LONG SPREAD: When A is oversold (RSI < 30) and B is overbought (RSI > 70) and z-score < -0.5
       - SHORT SPREAD: When A is overbought (RSI > 70) and B is oversold (RSI < 30) and z-score > 0.5
    5. Exit signals:
       - When z-score crosses zero (mean reversion complete)
       - Or RSI normalizes (both between 40-60)
    """

    def __init__(
        self,
        correlation_threshold: float = -1.0,  # HFT INSANE: Accept ANY correlation including negative!
        rsi_period: int = 7,  # Faster RSI for HFT
        rsi_oversold: float = 45,  # EXTREMELY sensitive
        rsi_overbought: float = 55,  # EXTREMELY sensitive - almost always signaling!
        zscore_entry: float = 0.01,  # HFT MODE: Trade on ANY tiny divergence!
        zscore_exit: float = 0.005,  # Ultra quick exits
        zscore_stoploss: float = 1.5,  # Tighter stop
        lookback_periods: int = 30  # Shorter lookback for HFT
    ):
        self.correlation_threshold = correlation_threshold
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.zscore_entry = zscore_entry
        self.zscore_exit = zscore_exit
        self.zscore_stoploss = zscore_stoploss
        self.lookback_periods = lookback_periods

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        try:
            if len(prices) < period + 1:
                return 50.0  # Neutral if not enough data

            # Calculate price changes
            delta = prices.diff()

            # Separate gains and losses
            gains = delta.where(delta > 0, 0.0)
            losses = -delta.where(delta < 0, 0.0)

            # Calculate average gains and losses
            avg_gain = gains.rolling(window=period).mean()
            avg_loss = losses.rolling(window=period).mean()

            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            return float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0

        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return 50.0

    def calculate_correlation(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        window: int = 60
    ) -> float:
        """Calculate rolling correlation"""
        try:
            if len(prices_a) < window or len(prices_b) < window:
                return 0.0

            # Align series
            df = pd.DataFrame({'a': prices_a, 'b': prices_b})
            df = df.dropna()

            if len(df) < window:
                return 0.0

            # Calculate correlation
            corr = df['a'].tail(window).corr(df['b'].tail(window))

            return float(corr) if not np.isnan(corr) else 0.0

        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0

    def calculate_zscore(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        window: int = 60
    ) -> Tuple[float, float]:
        """Calculate z-score of price ratio"""
        try:
            # Calculate price ratio
            ratio = prices_b / prices_a

            # Remove any inf/nan values
            ratio = ratio.replace([np.inf, -np.inf], np.nan).dropna()

            if len(ratio) < window:
                return 0.0, 1.0

            # Calculate z-score
            mean = ratio.tail(window).mean()
            std = ratio.tail(window).std()

            if std == 0 or np.isnan(std):
                return 0.0, 1.0

            current_ratio = ratio.iloc[-1]
            zscore = (current_ratio - mean) / std

            return float(zscore), float(std)

        except Exception as e:
            logger.error(f"Error calculating z-score: {e}")
            return 0.0, 1.0

    def generate_signal(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        current_position: Optional[str] = None
    ) -> StrategySignal:
        """
        Generate trading signal based on correlation + RSI + z-score

        Args:
            prices_a: Price series for symbol A
            prices_b: Price series for symbol B
            current_position: Current position if any (LONG_SPREAD, SHORT_SPREAD, None)

        Returns:
            StrategySignal with action and metadata
        """
        try:
            # Remove duplicates and sort by index
            prices_a = prices_a[~prices_a.index.duplicated(keep='last')].sort_index()
            prices_b = prices_b[~prices_b.index.duplicated(keep='last')].sort_index()

            # Check minimum data requirement
            min_required = max(self.rsi_period + 1, self.lookback_periods)
            if len(prices_a) < min_required or len(prices_b) < min_required:
                return StrategySignal(
                    action='HOLD',
                    confidence=0.0,
                    correlation=0.0,
                    rsi_a=50.0,
                    rsi_b=50.0,
                    zscore=0.0,
                    entry_reason='Insufficient data'
                )

            # Calculate indicators
            correlation = self.calculate_correlation(prices_a, prices_b, self.lookback_periods)
            rsi_a = self.calculate_rsi(prices_a, self.rsi_period)
            rsi_b = self.calculate_rsi(prices_b, self.rsi_period)
            zscore, zscore_std = self.calculate_zscore(prices_a, prices_b, self.lookback_periods)

            logger.info(f"Correlation: {correlation:.3f}, RSI_A: {rsi_a:.1f}, RSI_B: {rsi_b:.1f}, Z-Score: {zscore:.3f}")

            # ULTRA AGGRESSIVE: Skip correlation check entirely
            # Allow all pairs regardless of correlation

            # If we have a position, check exit conditions
            if current_position:
                # Stop loss
                if abs(zscore) > self.zscore_stoploss:
                    return StrategySignal(
                        action='CLOSE',
                        confidence=0.95,
                        correlation=correlation,
                        rsi_a=rsi_a,
                        rsi_b=rsi_b,
                        zscore=zscore,
                        entry_reason=f'Stop loss: z-score {zscore:.3f} > {self.zscore_stoploss}'
                    )

                # Mean reversion exit
                if abs(zscore) < self.zscore_exit:
                    return StrategySignal(
                        action='CLOSE',
                        confidence=0.85,
                        correlation=correlation,
                        rsi_a=rsi_a,
                        rsi_b=rsi_b,
                        zscore=zscore,
                        entry_reason=f'Mean reversion complete: z-score {zscore:.3f}'
                    )

                # RSI normalization exit
                if 40 < rsi_a < 60 and 40 < rsi_b < 60:
                    return StrategySignal(
                        action='CLOSE',
                        confidence=0.75,
                        correlation=correlation,
                        rsi_a=rsi_a,
                        rsi_b=rsi_b,
                        zscore=zscore,
                        entry_reason='RSI normalized'
                    )

                return StrategySignal(
                    action='HOLD',
                    confidence=0.5,
                    correlation=correlation,
                    rsi_a=rsi_a,
                    rsi_b=rsi_b,
                    zscore=zscore,
                    entry_reason='Holding position'
                )

            # Entry signals (no current position)

            # LONG SPREAD: Buy A, Sell B
            # When A is cheap (oversold) and B is expensive (overbought)
            # and z-score is negative (B/A ratio is low)
            if rsi_a < self.rsi_oversold and rsi_b > self.rsi_overbought and zscore < -self.zscore_entry:
                confidence = min(
                    0.95,
                    0.5 + (self.rsi_overbought - rsi_b) / 100 + (self.rsi_oversold - rsi_a) / 100 + abs(zscore) / 10
                )
                return StrategySignal(
                    action='LONG_SPREAD',
                    confidence=confidence,
                    correlation=correlation,
                    rsi_a=rsi_a,
                    rsi_b=rsi_b,
                    zscore=zscore,
                    entry_reason=f'A oversold (RSI {rsi_a:.1f}), B overbought (RSI {rsi_b:.1f}), z-score {zscore:.3f}'
                )

            # SHORT SPREAD: Sell A, Buy B
            # When A is expensive (overbought) and B is cheap (oversold)
            # and z-score is positive (B/A ratio is high)
            if rsi_a > self.rsi_overbought and rsi_b < self.rsi_oversold and zscore > self.zscore_entry:
                confidence = min(
                    0.95,
                    0.5 + (rsi_a - self.rsi_overbought) / 100 + (self.rsi_oversold - rsi_b) / 100 + abs(zscore) / 10
                )
                return StrategySignal(
                    action='SHORT_SPREAD',
                    confidence=confidence,
                    correlation=correlation,
                    rsi_a=rsi_a,
                    rsi_b=rsi_b,
                    zscore=zscore,
                    entry_reason=f'A overbought (RSI {rsi_a:.1f}), B oversold (RSI {rsi_b:.1f}), z-score {zscore:.3f}'
                )

            # Moderate signals with VERY relaxed conditions (ULTRA AGGRESSIVE)
            if rsi_a < 45 and rsi_b > 55 and zscore < -self.zscore_entry * 0.5:
                return StrategySignal(
                    action='LONG_SPREAD',
                    confidence=0.65,
                    correlation=correlation,
                    rsi_a=rsi_a,
                    rsi_b=rsi_b,
                    zscore=zscore,
                    entry_reason=f'Moderate LONG signal: RSI_A {rsi_a:.1f}, RSI_B {rsi_b:.1f}, z-score {zscore:.3f}'
                )

            if rsi_a > 55 and rsi_b < 45 and zscore > self.zscore_entry * 0.5:
                return StrategySignal(
                    action='SHORT_SPREAD',
                    confidence=0.65,
                    correlation=correlation,
                    rsi_a=rsi_a,
                    rsi_b=rsi_b,
                    zscore=zscore,
                    entry_reason=f'Moderate SHORT signal: RSI_A {rsi_a:.1f}, RSI_B {rsi_b:.1f}, z-score {zscore:.3f}'
                )

            # ULTRA AGGRESSIVE: Even weaker signals
            if abs(rsi_a - rsi_b) > 10 and abs(zscore) > self.zscore_entry * 0.3:
                action = 'LONG_SPREAD' if rsi_a < rsi_b else 'SHORT_SPREAD'
                return StrategySignal(
                    action=action,
                    confidence=0.55,
                    correlation=correlation,
                    rsi_a=rsi_a,
                    rsi_b=rsi_b,
                    zscore=zscore,
                    entry_reason=f'Weak {action}: RSI divergence {abs(rsi_a - rsi_b):.1f}, z-score {zscore:.3f}'
                )

            # No clear signal
            return StrategySignal(
                action='HOLD',
                confidence=0.5,
                correlation=correlation,
                rsi_a=rsi_a,
                rsi_b=rsi_b,
                zscore=zscore,
                entry_reason='No clear entry signal'
            )

        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return StrategySignal(
                action='HOLD',
                confidence=0.0,
                correlation=0.0,
                rsi_a=50.0,
                rsi_b=50.0,
                zscore=0.0,
                entry_reason=f'Error: {str(e)}'
            )
