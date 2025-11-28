"""Quantitative analysis agent"""

import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from src.data.models import Signal, CointegrationResult, ZScoreData
from src.strategy.cointegration import CointegrationAnalyzer
from src.strategy.zscore import ZScoreCalculator, detect_mean_reversion_strength
from src.strategy.signals import SignalGenerator
from src.config import config

logger = logging.getLogger(__name__)


class QuantAgent:
    """
    Quantitative analysis agent

    Responsibilities:
    - Statistical analysis (cointegration, z-score)
    - Signal generation based on mathematical models
    - Spread calculation and monitoring
    - Mean reversion detection
    """

    def __init__(self):
        self.coint_analyzer = CointegrationAnalyzer()
        self.zscore_calculator = ZScoreCalculator()
        self.signal_generator = SignalGenerator()

        self.pair_states: Dict[str, Dict[str, Any]] = {}
        self.last_analysis: Dict[str, datetime] = {}

    async def analyze_pair(
        self,
        symbol_a: str,
        symbol_b: str,
        price_history_a: pd.Series,
        price_history_b: pd.Series,
        current_position: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive quantitative analysis on a pair

        Returns:
            Dictionary with analysis results
        """
        try:
            pair_id = f"{symbol_a}_{symbol_b}"
            logger.debug(f"Analyzing {pair_id}...")

            if len(price_history_a) < 30 or len(price_history_b) < 30:
                logger.warning(f"Insufficient data for {pair_id}")
                return self._empty_analysis(pair_id)

            # 1. Cointegration analysis
            is_coint, pvalue, test_stat, hedge_ratio, half_life = \
                self.coint_analyzer.test_cointegration(price_history_a, price_history_b)

            coint_result = CointegrationResult(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                timestamp=datetime.now(),
                is_cointegrated=is_coint,
                pvalue=pvalue,
                test_statistic=test_stat,
                critical_values={'1%': -3.43, '5%': -2.86, '10%': -2.57},
                hedge_ratio=hedge_ratio,
                r_squared=0.0,  # Calculate if needed
                half_life=half_life
            )

            # 2. Calculate spread
            spread = self.coint_analyzer.calculate_spread(
                price_history_a,
                price_history_b,
                hedge_ratio
            )

            # 3. Calculate z-score
            current_spread = float(spread.iloc[-1])
            zscore = self.zscore_calculator.calculate_current_zscore(
                current_spread,
                spread[:-1]
            )

            zscore_data = ZScoreData(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                timestamp=datetime.now(),
                spread=current_spread,
                zscore=zscore,
                mean=float(spread.mean()),
                std=float(spread.std())
            )

            # 4. Mean reversion strength
            mean_reversion_score = detect_mean_reversion_strength(spread)

            # 5. Generate signal (without sentiment, that comes from sentiment agent)
            signal = self.signal_generator.generate_signal(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                price_history_a=price_history_a,
                price_history_b=price_history_b,
                current_position=current_position,
                sentiment_score=None  # Will be added by orchestrator
            )

            # 6. Calculate additional metrics
            spread_stats = self.zscore_calculator.calculate_spread_statistics(spread)

            analysis = {
                'pair_id': pair_id,
                'timestamp': datetime.now(),
                'cointegration': coint_result.dict(),
                'zscore': zscore_data.dict(),
                'signal': signal.dict() if signal else None,
                'mean_reversion_score': mean_reversion_score,
                'spread_stats': spread_stats,
                'recommendation': self._get_recommendation(
                    is_coint,
                    zscore,
                    mean_reversion_score,
                    current_position
                )
            }

            # Cache state
            self.pair_states[pair_id] = analysis
            self.last_analysis[pair_id] = datetime.now()

            return analysis

        except Exception as e:
            logger.error(f"Error in quant analysis: {e}")
            return self._empty_analysis(f"{symbol_a}_{symbol_b}")

    def _get_recommendation(
        self,
        is_cointegrated: bool,
        zscore: float,
        mean_reversion_score: float,
        current_position: Optional[str]
    ) -> Dict[str, Any]:
        """
        Generate trading recommendation

        Returns:
            Dictionary with recommendation details
        """
        if not is_cointegrated:
            return {
                'action': 'CLOSE' if current_position else 'AVOID',
                'reason': 'Pair not cointegrated',
                'confidence': 0.0
            }

        if mean_reversion_score < 0.3:
            return {
                'action': 'AVOID',
                'reason': 'Weak mean reversion',
                'confidence': 0.2
            }

        # Check z-score thresholds
        zscore_config = config.zscore

        if abs(zscore) > zscore_config.stoploss_threshold:
            return {
                'action': 'CLOSE',
                'reason': f'Stop-loss: z-score {zscore:.2f}',
                'confidence': 0.9
            }

        if zscore > zscore_config.entry_threshold:
            return {
                'action': 'SHORT_SPREAD',
                'reason': f'Z-score high: {zscore:.2f}',
                'confidence': min(0.9, (zscore - 2.0) * 0.3 + 0.5)
            }

        if zscore < -zscore_config.entry_threshold:
            return {
                'action': 'LONG_SPREAD',
                'reason': f'Z-score low: {zscore:.2f}',
                'confidence': min(0.9, (-zscore - 2.0) * 0.3 + 0.5)
            }

        if abs(zscore) < zscore_config.exit_threshold and current_position:
            return {
                'action': 'CLOSE',
                'reason': f'Mean reversion complete: z-score {zscore:.2f}',
                'confidence': 0.7
            }

        return {
            'action': 'HOLD',
            'reason': f'Z-score neutral: {zscore:.2f}',
            'confidence': 0.5
        }

    def _empty_analysis(self, pair_id: str) -> Dict[str, Any]:
        """Return empty analysis"""
        return {
            'pair_id': pair_id,
            'timestamp': datetime.now(),
            'cointegration': None,
            'zscore': None,
            'signal': None,
            'mean_reversion_score': 0.0,
            'spread_stats': {},
            'recommendation': {
                'action': 'AVOID',
                'reason': 'Insufficient data',
                'confidence': 0.0
            }
        }

    async def analyze_multiple_pairs(
        self,
        pairs: List[Dict[str, Any]],
        price_data: Dict[str, pd.Series],
        current_positions: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Analyze multiple pairs"""
        analyses = []

        for pair in pairs:
            if not pair.get('enabled', True):
                continue

            symbol_a = pair['symbol_a']
            symbol_b = pair['symbol_b']

            if symbol_a not in price_data or symbol_b not in price_data:
                continue

            analysis = await self.analyze_pair(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                price_history_a=price_data[symbol_a],
                price_history_b=price_data[symbol_b],
                current_position=current_positions.get(f"{symbol_a}_{symbol_b}")
            )

            analyses.append(analysis)

        return analyses

    def get_pair_state(self, pair_id: str) -> Optional[Dict[str, Any]]:
        """Get cached state for a pair"""
        return self.pair_states.get(pair_id)

    def clear_cache(self):
        """Clear cached states"""
        self.pair_states.clear()
        self.last_analysis.clear()
