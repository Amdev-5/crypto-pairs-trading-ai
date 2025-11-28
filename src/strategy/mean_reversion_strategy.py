"""Pure Mean Reversion Strategy with Bollinger Bands"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MeanReversionSignal:
    """Mean reversion signal output"""
    action: str
    confidence: float
    zscore: float
    bb_upper: float
    bb_lower: float
    bb_middle: float
    current_ratio: float
    entry_reason: str


class MeanReversionStrategy:
    """
    Pure mean reversion strategy using Bollinger Bands and Z-Score

    Entry:
    - LONG SPREAD: Ratio touches lower Bollinger Band + z-score < -1.5
    - SHORT SPREAD: Ratio touches upper Bollinger Band + z-score > 1.5

    Exit:
    - Ratio returns to middle Bollinger Band (20-period MA)
    - Or z-score crosses zero
    """

    def __init__(
        self,
        bb_period: int = 10,  # HFT: Faster Bollinger Bands
        bb_std: float = 1.5,  # Tighter bands = more signals
        zscore_entry: float = 0.3,  # MUCH lower threshold!
        zscore_exit: float = 0.1,  # Quick exits
        zscore_stoploss: float = 1.5,  # Tighter stop
        lookback_periods: int = 30  # Shorter for HFT
    ):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.zscore_entry = zscore_entry
        self.zscore_exit = zscore_exit
        self.zscore_stoploss = zscore_stoploss
        self.lookback_periods = lookback_periods

    def calculate_bollinger_bands(
        self,
        ratio: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        try:
            if len(ratio) < period:
                return 0.0, 0.0, 0.0

            middle = ratio.tail(period).mean()
            std = ratio.tail(period).std()

            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)

            return float(upper), float(middle), float(lower)

        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return 0.0, 0.0, 0.0

    def calculate_zscore(
        self,
        ratio: pd.Series,
        window: int = 100
    ) -> float:
        """Calculate z-score"""
        try:
            if len(ratio) < window:
                return 0.0

            mean = ratio.tail(window).mean()
            std = ratio.tail(window).std()

            if std == 0 or np.isnan(std):
                return 0.0

            current = ratio.iloc[-1]
            zscore = (current - mean) / std

            return float(zscore)

        except Exception as e:
            logger.error(f"Error calculating z-score: {e}")
            return 0.0

    def generate_signal(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        current_position: Optional[str] = None
    ) -> MeanReversionSignal:
        """Generate mean reversion signal"""
        try:
            # Remove duplicates
            prices_a = prices_a[~prices_a.index.duplicated(keep='last')].sort_index()
            prices_b = prices_b[~prices_b.index.duplicated(keep='last')].sort_index()

            if len(prices_a) < self.bb_period or len(prices_b) < self.bb_period:
                return MeanReversionSignal(
                    action='HOLD',
                    confidence=0.0,
                    zscore=0.0,
                    bb_upper=0.0,
                    bb_lower=0.0,
                    bb_middle=0.0,
                    current_ratio=0.0,
                    entry_reason='Insufficient data'
                )

            # Calculate price ratio
            ratio = prices_b / prices_a
            ratio = ratio.replace([np.inf, -np.inf], np.nan).dropna()

            if len(ratio) < self.bb_period:
                return MeanReversionSignal(
                    action='HOLD',
                    confidence=0.0,
                    zscore=0.0,
                    bb_upper=0.0,
                    bb_lower=0.0,
                    bb_middle=0.0,
                    current_ratio=0.0,
                    entry_reason='Insufficient ratio data'
                )

            # Calculate indicators
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(
                ratio, self.bb_period, self.bb_std
            )
            zscore = self.calculate_zscore(ratio, self.lookback_periods)
            current_ratio = float(ratio.iloc[-1])

            # Distance from bands (as percentage)
            bb_range = bb_upper - bb_lower
            if bb_range > 0:
                distance_from_upper = (bb_upper - current_ratio) / bb_range
                distance_from_lower = (current_ratio - bb_lower) / bb_range
            else:
                distance_from_upper = 0.5
                distance_from_lower = 0.5

            logger.info(f"Mean Reversion - Ratio: {current_ratio:.6f}, Z-Score: {zscore:.3f}, "
                       f"BB: [{bb_lower:.6f}, {bb_middle:.6f}, {bb_upper:.6f}]")

            # Exit conditions (if holding position)
            if current_position:
                # Stop loss
                if abs(zscore) > self.zscore_stoploss:
                    return MeanReversionSignal(
                        action='CLOSE',
                        confidence=0.95,
                        zscore=zscore,
                        bb_upper=bb_upper,
                        bb_lower=bb_lower,
                        bb_middle=bb_middle,
                        current_ratio=current_ratio,
                        entry_reason=f'Stop loss: z-score {zscore:.3f}'
                    )

                # Mean reversion complete
                if abs(zscore) < self.zscore_exit:
                    return MeanReversionSignal(
                        action='CLOSE',
                        confidence=0.85,
                        zscore=zscore,
                        bb_upper=bb_upper,
                        bb_lower=bb_lower,
                        bb_middle=bb_middle,
                        current_ratio=current_ratio,
                        entry_reason='Mean reversion complete'
                    )

                # Ratio crossed middle band
                if 0.4 < distance_from_upper < 0.6 and 0.4 < distance_from_lower < 0.6:
                    return MeanReversionSignal(
                        action='CLOSE',
                        confidence=0.80,
                        zscore=zscore,
                        bb_upper=bb_upper,
                        bb_lower=bb_lower,
                        bb_middle=bb_middle,
                        current_ratio=current_ratio,
                        entry_reason='Ratio returned to mean'
                    )

                return MeanReversionSignal(
                    action='HOLD',
                    confidence=0.5,
                    zscore=zscore,
                    bb_upper=bb_upper,
                    bb_lower=bb_lower,
                    bb_middle=bb_middle,
                    current_ratio=current_ratio,
                    entry_reason='Holding position'
                )

            # Entry signals

            # LONG SPREAD: Ratio at lower band (cheap A, expensive B)
            if current_ratio < bb_lower and zscore < -self.zscore_entry:
                confidence = min(0.95, 0.6 + abs(zscore) / 10 + distance_from_lower / 5)
                return MeanReversionSignal(
                    action='LONG_SPREAD',
                    confidence=confidence,
                    zscore=zscore,
                    bb_upper=bb_upper,
                    bb_lower=bb_lower,
                    bb_middle=bb_middle,
                    current_ratio=current_ratio,
                    entry_reason=f'Ratio below BB lower ({current_ratio:.6f} < {bb_lower:.6f}), z-score {zscore:.3f}'
                )

            # SHORT SPREAD: Ratio at upper band (expensive A, cheap B)
            if current_ratio > bb_upper and zscore > self.zscore_entry:
                confidence = min(0.95, 0.6 + abs(zscore) / 10 + distance_from_upper / 5)
                return MeanReversionSignal(
                    action='SHORT_SPREAD',
                    confidence=confidence,
                    zscore=zscore,
                    bb_upper=bb_upper,
                    bb_lower=bb_lower,
                    bb_middle=bb_middle,
                    current_ratio=current_ratio,
                    entry_reason=f'Ratio above BB upper ({current_ratio:.6f} > {bb_upper:.6f}), z-score {zscore:.3f}'
                )

            # Moderate signals
            if current_ratio < bb_lower * 1.01 and zscore < -self.zscore_entry * 0.7:
                return MeanReversionSignal(
                    action='LONG_SPREAD',
                    confidence=0.65,
                    zscore=zscore,
                    bb_upper=bb_upper,
                    bb_lower=bb_lower,
                    bb_middle=bb_middle,
                    current_ratio=current_ratio,
                    entry_reason=f'Moderate LONG: Near BB lower, z-score {zscore:.3f}'
                )

            if current_ratio > bb_upper * 0.99 and zscore > self.zscore_entry * 0.7:
                return MeanReversionSignal(
                    action='SHORT_SPREAD',
                    confidence=0.65,
                    zscore=zscore,
                    bb_upper=bb_upper,
                    bb_lower=bb_lower,
                    bb_middle=bb_middle,
                    current_ratio=current_ratio,
                    entry_reason=f'Moderate SHORT: Near BB upper, z-score {zscore:.3f}'
                )

            return MeanReversionSignal(
                action='HOLD',
                confidence=0.5,
                zscore=zscore,
                bb_upper=bb_upper,
                bb_lower=bb_lower,
                bb_middle=bb_middle,
                current_ratio=current_ratio,
                entry_reason='No clear signal'
            )

        except Exception as e:
            logger.error(f"Error generating mean reversion signal: {e}")
            return MeanReversionSignal(
                action='HOLD',
                confidence=0.0,
                zscore=0.0,
                bb_upper=0.0,
                bb_lower=0.0,
                bb_middle=0.0,
                current_ratio=0.0,
                entry_reason=f'Error: {str(e)}'
            )
