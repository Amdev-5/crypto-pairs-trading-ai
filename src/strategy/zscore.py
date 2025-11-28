"""Z-score calculation and analysis"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ZScoreCalculator:
    """Calculate and analyze z-scores for pairs trading"""

    def __init__(self, lookback_period: int = 720):
        """
        Args:
            lookback_period: Number of periods for calculating mean and std
        """
        self.lookback_period = lookback_period

    def calculate_zscore(
        self,
        spread: pd.Series,
        lookback: Optional[int] = None
    ) -> pd.Series:
        """
        Calculate z-score of spread

        z = (spread - mean(spread)) / std(spread)

        Args:
            spread: Price spread series
            lookback: Lookback period (uses default if None)

        Returns:
            Z-score series
        """
        if lookback is None:
            lookback = self.lookback_period

        try:
            # Calculate rolling mean and std
            mean = spread.rolling(window=lookback, min_periods=30).mean()
            std = spread.rolling(window=lookback, min_periods=30).std()

            # Calculate z-score
            zscore = (spread - mean) / std

            # Replace inf and -inf with NaN
            zscore = zscore.replace([np.inf, -np.inf], np.nan)

            return zscore

        except Exception as e:
            logger.error(f"Error calculating z-score: {e}")
            return pd.Series(index=spread.index, dtype=float)

    def calculate_current_zscore(
        self,
        current_spread: float,
        historical_spread: pd.Series
    ) -> float:
        """
        Calculate current z-score given historical spread

        Args:
            current_spread: Current spread value
            historical_spread: Historical spread values

        Returns:
            Current z-score
        """
        try:
            if len(historical_spread) < 30:
                logger.warning("Insufficient data for z-score calculation")
                return 0.0

            mean = historical_spread.mean()
            std = historical_spread.std()

            if std == 0 or np.isnan(std):
                return 0.0

            zscore = (current_spread - mean) / std

            if np.isnan(zscore) or np.isinf(zscore):
                return 0.0

            return float(zscore)

        except Exception as e:
            logger.error(f"Error calculating current z-score: {e}")
            return 0.0

    def get_signal_from_zscore(
        self,
        zscore: float,
        entry_threshold: float = 2.0,
        exit_threshold: float = 0.5,
        stop_loss_threshold: float = 3.0
    ) -> str:
        """
        Generate trading signal from z-score

        Args:
            zscore: Current z-score
            entry_threshold: Entry threshold (default 2.0)
            exit_threshold: Exit threshold (default 0.5)
            stop_loss_threshold: Stop-loss threshold (default 3.0)

        Returns:
            Signal: 'long_spread', 'short_spread', 'close', or 'hold'
        """
        # Stop-loss conditions
        if abs(zscore) > stop_loss_threshold:
            return 'close'

        # Entry signals
        if zscore > entry_threshold:
            # Spread is too high, expect mean reversion
            # Short spread: Short asset A, Long asset B
            return 'short_spread'
        elif zscore < -entry_threshold:
            # Spread is too low, expect mean reversion
            # Long spread: Long asset A, Short asset B
            return 'long_spread'

        # Exit signal (mean reversion occurred)
        if abs(zscore) < exit_threshold:
            return 'close'

        # Hold current position
        return 'hold'

    def calculate_spread_statistics(
        self,
        spread: pd.Series
    ) -> dict:
        """
        Calculate statistical properties of spread

        Returns:
            Dictionary with mean, std, min, max, etc.
        """
        try:
            stats = {
                'mean': float(spread.mean()),
                'std': float(spread.std()),
                'min': float(spread.min()),
                'max': float(spread.max()),
                'median': float(spread.median()),
                'current': float(spread.iloc[-1]) if len(spread) > 0 else 0.0,
                'skew': float(spread.skew()) if len(spread) > 3 else 0.0,
                'kurtosis': float(spread.kurtosis()) if len(spread) > 3 else 0.0
            }

            return stats

        except Exception as e:
            logger.error(f"Error calculating spread statistics: {e}")
            return {}

    def rolling_zscore(
        self,
        spread: pd.Series,
        window: int = 60
    ) -> pd.DataFrame:
        """
        Calculate rolling z-score with different window sizes

        Returns:
            DataFrame with z-scores for different windows
        """
        try:
            df = pd.DataFrame(index=spread.index)

            for w in [window, window * 2, window * 4]:
                col_name = f'zscore_{w}'
                df[col_name] = self.calculate_zscore(spread, lookback=w)

            return df

        except Exception as e:
            logger.error(f"Error calculating rolling z-score: {e}")
            return pd.DataFrame()

    def adaptive_zscore(
        self,
        spread: pd.Series,
        volatility: pd.Series
    ) -> pd.Series:
        """
        Calculate adaptive z-score that adjusts for volatility

        Uses volatility-weighted lookback period
        """
        try:
            # Adjust lookback based on volatility
            # Higher volatility = shorter lookback
            base_lookback = self.lookback_period

            vol_mean = volatility.mean()
            vol_std = volatility.std()

            if vol_std == 0:
                return self.calculate_zscore(spread)

            vol_zscore = (volatility - vol_mean) / vol_std

            # Adaptive lookback
            adaptive_lookback = base_lookback * (1 - 0.3 * vol_zscore)
            adaptive_lookback = adaptive_lookback.clip(
                lower=base_lookback * 0.5,
                upper=base_lookback * 1.5
            ).astype(int)

            # Calculate z-score with adaptive lookback
            zscores = []
            for i in range(len(spread)):
                if i < 30:
                    zscores.append(np.nan)
                    continue

                lookback = int(adaptive_lookback.iloc[i])
                start_idx = max(0, i - lookback)
                window_spread = spread.iloc[start_idx:i + 1]

                if len(window_spread) < 30:
                    zscores.append(np.nan)
                    continue

                mean = window_spread.mean()
                std = window_spread.std()

                if std == 0:
                    zscores.append(0.0)
                else:
                    z = (spread.iloc[i] - mean) / std
                    zscores.append(z)

            return pd.Series(zscores, index=spread.index)

        except Exception as e:
            logger.error(f"Error calculating adaptive z-score: {e}")
            return self.calculate_zscore(spread)

    def calculate_bollinger_bands(
        self,
        spread: pd.Series,
        window: int = 20,
        num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands for spread

        Returns:
            - upper_band
            - middle_band (moving average)
            - lower_band
        """
        try:
            middle = spread.rolling(window=window).mean()
            std = spread.rolling(window=window).std()

            upper = middle + (std * num_std)
            lower = middle - (std * num_std)

            return upper, middle, lower

        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return pd.Series(), pd.Series(), pd.Series()


def detect_mean_reversion_strength(spread: pd.Series) -> float:
    """
    Detect the strength of mean reversion in spread

    Uses Hurst exponent:
    - H < 0.5: Mean reverting
    - H = 0.5: Random walk
    - H > 0.5: Trending

    Returns:
        Mean reversion score (0 to 1, higher is more mean-reverting)
    """
    try:
        if len(spread) < 100:
            return 0.0

        # Calculate Hurst exponent
        lags = range(2, min(100, len(spread) // 2))
        tau = []
        for lag in lags:
            # Calculate standard deviation of lagged differences
            diff = spread.diff(lag).dropna()
            std = diff.std()
            tau.append(std)

        # Fit power law
        tau = np.array(tau)
        lags = np.array(lags)

        if len(tau) < 2 or np.any(tau <= 0):
            return 0.0

        # Linear regression in log-log space
        log_lags = np.log(lags)
        log_tau = np.log(tau)

        poly = np.polyfit(log_lags, log_tau, 1)
        hurst = poly[0]

        # Convert Hurst to mean reversion score
        # H < 0.5 is mean-reverting
        if hurst < 0.5:
            score = (0.5 - hurst) * 2  # Scale to 0-1
        else:
            score = 0.0

        return float(np.clip(score, 0, 1))

    except Exception as e:
        logger.error(f"Error calculating mean reversion strength: {e}")
        return 0.0
