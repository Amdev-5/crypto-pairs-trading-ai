"""Cointegration analysis for pairs trading"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict
from statsmodels.tsa.stattools import adfuller, coint
from statsmodels.regression.linear_model import OLS
import logging

logger = logging.getLogger(__name__)


class CointegrationAnalyzer:
    """Analyzes cointegration between asset pairs"""

    def __init__(self, pvalue_threshold: float = 0.05):
        self.pvalue_threshold = pvalue_threshold

    def test_cointegration(
        self,
        price_a: pd.Series,
        price_b: pd.Series,
        method: str = "engle_granger"
    ) -> Tuple[bool, float, float, float, Optional[float]]:
        """
        Test cointegration between two price series

        Returns:
            - is_cointegrated: bool
            - pvalue: float
            - test_statistic: float
            - hedge_ratio: float (beta from regression)
            - half_life: Optional[float] (mean reversion speed in periods)
        """
        try:
            # Ensure inputs are pandas Series
            if not isinstance(price_a, pd.Series):
                price_a = pd.Series(price_a)
            if not isinstance(price_b, pd.Series):
                price_b = pd.Series(price_b)

            # Align price series by index (timestamps) - CRITICAL FIX
            # Ensure index is datetime
            price_a.index = pd.to_datetime(price_a.index)
            price_b.index = pd.to_datetime(price_b.index)

            # Force unique indices by grouping by index and taking mean
            # ALWAYS do this to be safe against any duplicates
            price_a = price_a.groupby(level=0).mean()
            price_b = price_b.groupby(level=0).mean()
            
            # Sort index
            price_a = price_a.sort_index()
            price_b = price_b.sort_index()
            
            # Create DataFrame with aligned indices using merge
            df_a = price_a.to_frame(name='a')
            df_b = price_b.to_frame(name='b')
            
            # Inner join on index
            df = df_a.join(df_b, how='inner')
            df = df.dropna()  # Remove any NaN values
            
            # Inner join on index
            df = df_a.join(df_b, how='inner')
            df = df.dropna()  # Remove any NaN values

            if len(df) < 30:
                logger.warning(f"Price series too short after alignment: {len(df)} points")
                return False, 1.0, 0.0, 1.0, None

            price_a = df['a']
            price_b = df['b']

            if method == "engle_granger":
                return self._engle_granger_test(price_a, price_b)
            elif method == "johansen":
                return self._johansen_test(price_a, price_b)
            else:
                raise ValueError(f"Unknown method: {method}")

        except Exception as e:
            logger.error(f"Error in cointegration test: {e}")
            return False, 1.0, 0.0, 1.0, None

    def _engle_granger_test(
        self,
        price_a: pd.Series,
        price_b: pd.Series
    ) -> Tuple[bool, float, float, float, Optional[float]]:
        """
        Engle-Granger two-step cointegration test

        Step 1: Regress price_b on price_a to get hedge ratio
        Step 2: Test if residuals are stationary (ADF test)
        """
        try:
            # Step 1: OLS regression to get hedge ratio
            X = np.array(price_a).reshape(-1, 1)
            y = np.array(price_b)

            # Add constant
            X_with_const = np.column_stack([np.ones(len(X)), X])

            # OLS regression
            model = OLS(y, X_with_const).fit()
            hedge_ratio = model.params[1]  # Beta coefficient
            r_squared = model.rsquared

            # Calculate spread (residuals)
            spread = y - (model.params[0] + hedge_ratio * X.flatten())

            # Step 2: Test if spread is stationary
            adf_result = adfuller(spread, maxlag=1)
            test_statistic = adf_result[0]
            pvalue = adf_result[1]

            # Calculate half-life of mean reversion
            half_life = self._calculate_half_life(spread)

            # Check cointegration (AGGRESSIVE - lower R² requirement)
            is_cointegrated = (
                pvalue < self.pvalue_threshold and
                r_squared > 0.1  # Very low R² requirement for more trades
            )

            half_life_str = f"{half_life:.2f}" if half_life else "N/A"
            logger.debug(
                f"Cointegration test: p-value={pvalue:.4f}, "
                f"hedge_ratio={hedge_ratio:.4f}, R²={r_squared:.4f}, "
                f"half_life={half_life_str}"
            )

            return is_cointegrated, pvalue, test_statistic, hedge_ratio, half_life

        except Exception as e:
            logger.error(f"Error in Engle-Granger test: {e}")
            return False, 1.0, 0.0, 1.0, None

    def _johansen_test(
        self,
        price_a: pd.Series,
        price_b: pd.Series
    ) -> Tuple[bool, float, float, float, Optional[float]]:
        """
        Johansen cointegration test (placeholder)

        Note: Requires vecm from statsmodels
        """
        # Fallback to Engle-Granger for now
        logger.warning("Johansen test not implemented, using Engle-Granger")
        return self._engle_granger_test(price_a, price_b)

    def _calculate_half_life(self, spread: np.ndarray) -> Optional[float]:
        """
        Calculate half-life of mean reversion

        Uses Ornstein-Uhlenbeck process:
        Δspread(t) = θ(μ - spread(t-1))Δt + σε(t)

        Half-life = -ln(2) / θ
        """
        try:
            spread_lag = spread[:-1]
            spread_diff = np.diff(spread)

            # Regression: Δspread = α + β*spread_lag
            X = spread_lag.reshape(-1, 1)
            y = spread_diff

            if len(X) < 10:
                return None

            model = OLS(y, np.column_stack([np.ones(len(X)), X])).fit()
            theta = model.params[1]

            if theta >= 0:  # Not mean-reverting
                return None

            half_life = -np.log(2) / theta

            # Sanity check: half-life should be reasonable
            if half_life <= 0 or half_life > len(spread):
                return None

            return half_life

        except Exception as e:
            logger.error(f"Error calculating half-life: {e}")
            return None

    def calculate_hedge_ratio(
        self,
        price_a: pd.Series,
        price_b: pd.Series,
        method: str = "ols"
    ) -> Tuple[float, float]:
        """
        Calculate hedge ratio (beta) between two assets

        Returns:
            - hedge_ratio: float
            - r_squared: float
        """
        try:
            X = np.array(price_a).reshape(-1, 1)
            y = np.array(price_b)

            X_with_const = np.column_stack([np.ones(len(X)), X])
            model = OLS(y, X_with_const).fit()

            hedge_ratio = model.params[1]
            r_squared = model.rsquared

            return hedge_ratio, r_squared

        except Exception as e:
            logger.error(f"Error calculating hedge ratio: {e}")
            return 1.0, 0.0

    def calculate_spread(
        self,
        price_a: pd.Series,
        price_b: pd.Series,
        hedge_ratio: float
    ) -> pd.Series:
        """
        Calculate spread between two assets

        Spread = price_b - hedge_ratio * price_a
        """
        return price_b - hedge_ratio * price_a

    def rolling_cointegration(
        self,
        price_a: pd.Series,
        price_b: pd.Series,
        window: int = 120
    ) -> pd.DataFrame:
        """
        Perform rolling window cointegration analysis

        Returns DataFrame with:
        - hedge_ratio
        - pvalue
        - is_cointegrated
        - half_life
        """
        results = []

        for i in range(window, len(price_a)):
            window_a = price_a.iloc[i - window:i]
            window_b = price_b.iloc[i - window:i]

            is_coint, pvalue, _, hedge_ratio, half_life = self.test_cointegration(
                window_a, window_b
            )

            results.append({
                'timestamp': price_a.index[i],
                'hedge_ratio': hedge_ratio,
                'pvalue': pvalue,
                'is_cointegrated': is_coint,
                'half_life': half_life
            })

        return pd.DataFrame(results)

    def test_stationarity(self, series: pd.Series) -> Tuple[bool, float]:
        """
        Test if a series is stationary using ADF test

        Returns:
            - is_stationary: bool
            - pvalue: float
        """
        try:
            result = adfuller(series.dropna(), maxlag=1)
            pvalue = result[1]
            is_stationary = pvalue < self.pvalue_threshold

            return is_stationary, pvalue

        except Exception as e:
            logger.error(f"Error in stationarity test: {e}")
            return False, 1.0


def calculate_optimal_hedge_ratio(
    price_a: np.ndarray,
    price_b: np.ndarray,
    method: str = "ols"
) -> float:
    """
    Calculate optimal hedge ratio

    Methods:
    - ols: Ordinary Least Squares
    - variance: Minimize portfolio variance
    """
    if method == "ols":
        # β from regression price_b = α + β * price_a
        X = price_a.reshape(-1, 1)
        y = price_b
        X_with_const = np.column_stack([np.ones(len(X)), X])
        model = OLS(y, X_with_const).fit()
        return model.params[1]

    elif method == "variance":
        # Minimize variance of portfolio: Var(price_b - h * price_a)
        cov = np.cov(price_a, price_b)[0, 1]
        var_a = np.var(price_a)
        return cov / var_a if var_a > 0 else 1.0

    else:
        raise ValueError(f"Unknown method: {method}")
