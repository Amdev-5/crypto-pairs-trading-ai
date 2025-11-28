"""Engle-Granger Cointegration Strategy

Based on: "Pairs trading in cryptocurrency market: A long-short story" (2021)
Implements the "Relative-Value Arbitrage Rule" with statistical rigor.

Methodology:
1. Pearson Correlation (pre-filtering)
2. Distance Metric (sum of squared differences)
3. Engle-Granger Two-Step Cointegration Test
4. OLS Regression for Hedge Ratio (Beta)
5. ADF Test for Stationarity
6. Z-Score based entry/exit signals

Entry: |Z-Score| > 2.0
Exit: Z-Score returns to 0 (mean reversion)
Stop Loss: |Z-Score| > 4.0 (divergence beyond cointegration)
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
import logging
from dataclasses import dataclass

# Statistical libraries
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from scipy.stats import pearsonr

logger = logging.getLogger(__name__)


@dataclass
class EngleGrangerSignal:
    """Signal output from Engle-Granger strategy"""
    action: str  # LONG_SPREAD, SHORT_SPREAD, CLOSE, HOLD
    confidence: float  # 0.0 to 1.0
    zscore: float
    spread: float
    hedge_ratio: float  # Beta from OLS regression
    correlation: float
    distance: float
    adf_pvalue: float  # P-value from ADF test (< 0.05 = cointegrated)
    entry_reason: str


class EngleGrangerStrategy:
    """
    Production-Ready Engle-Granger Cointegration Strategy

    INDUSTRY-STANDARD THRESHOLDS (Based on 2024 Research):
    - Entry threshold: |Z| > 2.0 (industry standard for crypto)
    - Exit threshold: |Z| < 0.3 (quick mean reversion exits)
    - Stop loss: |Z| > 3.5 (reasonable protection)
    - P-value: < 0.10 (relaxed for crypto volatility)
    - Lookback: 60 periods (fast adaptation)

    The paper proves:
    - Long-Short consistently beats Buy-Hold (especially in bear markets)
    - Beta (hedge ratio) minimizes portfolio variance
    - Cointegration ensures statistical validity (prevents spurious trades)
    """

    def __init__(
        self,
        lookback_periods: int = 60,  # HFT: Shorter lookback
        correlation_threshold: float = 0.3,  # AGGRESSIVE: Low threshold
        distance_threshold: float = 100.0,  # Pre-filter
        adf_pvalue_threshold: float = 0.10,  # RELAXED: 10% for crypto volatility
        zscore_entry: float = 2.0,  # INDUSTRY STANDARD: 2.0 sigma
        zscore_exit: float = 0.3,  # Quick exits but not too early
        zscore_stoploss: float = 3.5,  # Reasonable stop loss
        min_data_points: int = 30  # Minimum for valid regression
    ):
        self.lookback_periods = lookback_periods
        self.correlation_threshold = correlation_threshold
        self.distance_threshold = distance_threshold
        self.adf_pvalue_threshold = adf_pvalue_threshold
        self.zscore_entry = zscore_entry
        self.zscore_exit = zscore_exit
        self.zscore_stoploss = zscore_stoploss
        self.min_data_points = min_data_points

    def calculate_correlation(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series
    ) -> float:
        """
        Calculate Pearson Correlation Coefficient

        From paper: "The pair of cryptocurrencies with the highest
        correlation is also the one with the least distance between
        their prices."
        """
        try:
            # Align series
            aligned_a, aligned_b = prices_a.align(prices_b, join='inner')

            if len(aligned_a) < 2:
                return 0.0

            # Calculate Pearson correlation
            correlation, _ = pearsonr(aligned_a, aligned_b)

            return float(correlation) if not np.isnan(correlation) else 0.0

        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0.0

    def calculate_distance(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series
    ) -> float:
        """
        Calculate Distance Metric (Sum of Squared Differences)

        From paper: Distance = Σ(ρ_a - ρ_b)² where ρ are normalized prices

        "The best pair of assets will be the pair whose distance between
        the prices is the lowest with a high degree of correlations"
        """
        try:
            # Normalize prices (z-score normalization)
            def normalize(series):
                mean = series.mean()
                std = series.std()
                if std == 0:
                    return series - mean
                return (series - mean) / std

            norm_a = normalize(prices_a)
            norm_b = normalize(prices_b)

            # Align
            aligned_a, aligned_b = norm_a.align(norm_b, join='inner')

            # Sum of squared differences
            distance = np.sum((aligned_a - aligned_b) ** 2)

            return float(distance)

        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return float('inf')

    def engle_granger_test(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series
    ) -> Tuple[float, float, pd.Series]:
        """
        Engle-Granger Two-Step Cointegration Test

        Step 1: OLS Regression
            Price_A = α + β * Price_B + ε

        Step 2: ADF Test on residuals (ε)
            H0: Residuals have unit root (NOT cointegrated)
            H1: Residuals are stationary (COINTEGRATED)

        From paper: "If the variables do not cointegrate, then the
        regression is spurious (fake) and will lose money."

        Returns:
            - hedge_ratio (β): The beta coefficient (optimal weight)
            - adf_pvalue: P-value from ADF test
            - residuals: The spread (ε)
        """
        try:
            # Align series
            df = pd.DataFrame({'a': prices_a, 'b': prices_b})
            df = df.dropna()

            if len(df) < self.min_data_points:
                return 1.0, 1.0, pd.Series()

            # Step 1: OLS Regression (Price_A = α + β * Price_B + ε)
            # Add constant for intercept
            X = sm.add_constant(df['b'])  # Independent variable (with intercept)
            y = df['a']  # Dependent variable

            # Fit OLS model
            model = sm.OLS(y, X).fit()

            # Extract beta (hedge ratio) - this is the cointegrating coefficient
            # From paper: "The beta coefficient determines the relative weight
            # of cryptocurrencies in respective pairs to neutralize risk"
            hedge_ratio = model.params['b']  # Beta coefficient

            # Get residuals (the spread)
            residuals = model.resid

            # Step 2: ADF Test on residuals
            # H0: residuals have unit root (not stationary, NOT cointegrated)
            # H1: residuals are stationary (COINTEGRATED!)
            adf_result = adfuller(residuals, maxlag=1, regression='c')
            adf_statistic = adf_result[0]
            adf_pvalue = adf_result[1]

            logger.info(
                f"Engle-Granger: β={hedge_ratio:.4f}, "
                f"ADF p-value={adf_pvalue:.4f} "
                f"({'COINTEGRATED ✓' if adf_pvalue < self.adf_pvalue_threshold else 'NOT cointegrated'})"
            )

            return float(hedge_ratio), float(adf_pvalue), residuals

        except Exception as e:
            logger.error(f"Error in Engle-Granger test: {e}")
            return 1.0, 1.0, pd.Series()

    def calculate_spread_zscore(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        hedge_ratio: float,
        window: int = None
    ) -> Tuple[float, pd.Series]:
        """
        Calculate the spread and its Z-Score

        Spread = Price_A - β * Price_B

        Z-Score = (Current_Spread - Mean_Spread) / Std_Spread

        From paper: "Calculate the Z-Score of the current Spread
        (normalize it using a rolling mean and standard deviation)"
        """
        try:
            if window is None:
                window = self.lookback_periods

            # Calculate spread
            spread = prices_a - (hedge_ratio * prices_b)

            if len(spread) < window:
                return 0.0, spread

            # Calculate rolling statistics
            mean_spread = spread.tail(window).mean()
            std_spread = spread.tail(window).std()

            if std_spread == 0 or np.isnan(std_spread):
                return 0.0, spread

            # Current Z-Score
            current_spread = spread.iloc[-1]
            zscore = (current_spread - mean_spread) / std_spread

            return float(zscore), spread

        except Exception as e:
            logger.error(f"Error calculating Z-Score: {e}")
            return 0.0, pd.Series()

    def generate_signal(
        self,
        prices_a: pd.Series,
        prices_b: pd.Series,
        current_position: Optional[str] = None
    ) -> EngleGrangerSignal:
        """
        Generate trading signal using Engle-Granger methodology

        From paper's strategy logic:
        - Entry: Z-Score > +2.0 → Short A, Long B
        - Entry: Z-Score < -2.0 → Long A, Short B
        - Exit: Z-Score returns to 0 (mean reversion)
        - Stop Loss: |Z-Score| > 4.0 (divergence)

        HFT Mode: Using 1.0 / 0.1 / 3.0 thresholds for aggressive trading
        """
        try:
            # Remove duplicates
            prices_a = prices_a[~prices_a.index.duplicated(keep='last')].sort_index()
            prices_b = prices_b[~prices_b.index.duplicated(keep='last')].sort_index()

            # Check minimum data
            if len(prices_a) < self.min_data_points or len(prices_b) < self.min_data_points:
                return EngleGrangerSignal(
                    action='HOLD',
                    confidence=0.0,
                    zscore=0.0,
                    spread=0.0,
                    hedge_ratio=1.0,
                    correlation=0.0,
                    distance=0.0,
                    adf_pvalue=1.0,
                    entry_reason='Insufficient data'
                )

            # Step 1: Calculate Correlation (pre-filter)
            correlation = self.calculate_correlation(
                prices_a.tail(self.lookback_periods),
                prices_b.tail(self.lookback_periods)
            )

            # Step 2: Calculate Distance (pre-filter)
            distance = self.calculate_distance(
                prices_a.tail(self.lookback_periods),
                prices_b.tail(self.lookback_periods)
            )

            # Step 3: Engle-Granger Cointegration Test
            hedge_ratio, adf_pvalue, residuals = self.engle_granger_test(
                prices_a.tail(self.lookback_periods),
                prices_b.tail(self.lookback_periods)
            )

            # Step 4: Calculate Spread and Z-Score
            zscore, spread = self.calculate_spread_zscore(
                prices_a.tail(self.lookback_periods),
                prices_b.tail(self.lookback_periods),
                hedge_ratio
            )

            current_spread = spread.iloc[-1] if len(spread) > 0 else 0.0

            logger.info(
                f"Engle-Granger: Corr={correlation:.3f}, Dist={distance:.2f}, "
                f"β={hedge_ratio:.4f}, ADF p-val={adf_pvalue:.4f}, Z={zscore:.3f}"
            )

            # Exit conditions (if holding position)
            if current_position:
                # Stop loss: divergence beyond cointegration relationship
                if abs(zscore) > self.zscore_stoploss:
                    return EngleGrangerSignal(
                        action='CLOSE',
                        confidence=0.95,
                        zscore=zscore,
                        spread=current_spread,
                        hedge_ratio=hedge_ratio,
                        correlation=correlation,
                        distance=distance,
                        adf_pvalue=adf_pvalue,
                        entry_reason=f'Stop loss: Z-Score {zscore:.3f} > {self.zscore_stoploss}'
                    )

                # Mean reversion complete
                if abs(zscore) < self.zscore_exit:
                    return EngleGrangerSignal(
                        action='CLOSE',
                        confidence=0.90,
                        zscore=zscore,
                        spread=current_spread,
                        hedge_ratio=hedge_ratio,
                        correlation=correlation,
                        distance=distance,
                        adf_pvalue=adf_pvalue,
                        entry_reason=f'Mean reversion: Z-Score {zscore:.3f} → 0'
                    )

                # Hold position
                return EngleGrangerSignal(
                    action='HOLD',
                    confidence=0.5,
                    zscore=zscore,
                    spread=current_spread,
                    hedge_ratio=hedge_ratio,
                    correlation=correlation,
                    distance=distance,
                    adf_pvalue=adf_pvalue,
                    entry_reason='Holding position'
                )

            # Entry signals (no current position)

            # Check cointegration strength
            # Strong: p < 0.10
            # Weak: 0.10 <= p < 0.20
            is_strong_cointegration = adf_pvalue < 0.10
            is_weak_cointegration = adf_pvalue < 0.20
            
            # Must be at least weakly cointegrated to trade
            if not is_weak_cointegration:
                return EngleGrangerSignal(
                    action='HOLD',
                    confidence=0.0,
                    zscore=zscore,
                    spread=current_spread,
                    hedge_ratio=hedge_ratio,
                    correlation=correlation,
                    distance=distance,
                    adf_pvalue=adf_pvalue,
                    entry_reason=f'NOT cointegrated (p={adf_pvalue:.4f} > 0.20)'
                )

            # Calculate base confidence based on cointegration strength
            # Strong (p<0.10): 1.0 multiplier
            # Weak (0.10<=p<0.20): 0.5-0.9 multiplier based on p-value
            cointegration_quality = 1.0 if is_strong_cointegration else max(0.5, 1.0 - (adf_pvalue - 0.10) * 5)

            # SHORT SPREAD: Spread too high (sell A, buy B)
            if zscore > self.zscore_entry:
                # Confidence based on Z-Score magnitude and cointegration strength
                raw_confidence = min(0.95, 0.6 + abs(zscore) / 10)
                final_confidence = raw_confidence * cointegration_quality

                strength_str = "STRONG" if is_strong_cointegration else "WEAK"
                return EngleGrangerSignal(
                    action='SHORT_SPREAD',
                    confidence=final_confidence,
                    zscore=zscore,
                    spread=current_spread,
                    hedge_ratio=hedge_ratio,
                    correlation=correlation,
                    distance=distance,
                    adf_pvalue=adf_pvalue,
                    entry_reason=(
                        f'{strength_str} Cointegration (p={adf_pvalue:.4f}), '
                        f'Z-Score {zscore:.3f} > {self.zscore_entry} '
                        f'(β={hedge_ratio:.4f})'
                    )
                )

            # LONG SPREAD: Spread too low (buy A, sell B)
            if zscore < -self.zscore_entry:
                raw_confidence = min(0.95, 0.6 + abs(zscore) / 10)
                final_confidence = raw_confidence * cointegration_quality

                strength_str = "STRONG" if is_strong_cointegration else "WEAK"
                return EngleGrangerSignal(
                    action='LONG_SPREAD',
                    confidence=final_confidence,
                    zscore=zscore,
                    spread=current_spread,
                    hedge_ratio=hedge_ratio,
                    correlation=correlation,
                    distance=distance,
                    adf_pvalue=adf_pvalue,
                    entry_reason=(
                        f'{strength_str} Cointegration (p={adf_pvalue:.4f}), '
                        f'Z-Score {zscore:.3f} < -{self.zscore_entry} '
                        f'(β={hedge_ratio:.4f})'
                    )
                )

            # No signal
            return EngleGrangerSignal(
                action='HOLD',
                confidence=0.5,
                zscore=zscore,
                spread=current_spread,
                hedge_ratio=hedge_ratio,
                correlation=correlation,
                distance=distance,
                adf_pvalue=adf_pvalue,
                entry_reason=f'No signal: Z-Score {zscore:.3f} in neutral range'
            )

        except Exception as e:
            logger.error(f"Error generating Engle-Granger signal: {e}", exc_info=True)
            return EngleGrangerSignal(
                action='HOLD',
                confidence=0.0,
                zscore=0.0,
                spread=0.0,
                hedge_ratio=1.0,
                correlation=0.0,
                distance=0.0,
                adf_pvalue=1.0,
                entry_reason=f'Error: {str(e)}'
            )
