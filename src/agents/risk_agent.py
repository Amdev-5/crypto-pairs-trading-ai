"""Risk management agent"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from src.data.models import Position, RiskMetrics
from src.config import config

logger = logging.getLogger(__name__)


class RiskAgent:
    """
    Risk management agent

    Responsibilities:
    - Position sizing
    - Stop-loss management
    - Daily loss limits
    - Drawdown monitoring
    - Portfolio risk assessment
    """

    def __init__(self):
        self.trading_config = config.trading
        self.risk_config = config.get_trading_pairs()  # From YAML

        self.daily_pnl_history: List[float] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.max_equity: float = 0.0
        self.current_drawdown: float = 0.0

    def calculate_position_size(
        self,
        pair_id: str,
        account_balance: float,
        signal_confidence: float,
        volatility: Optional[float] = None
    ) -> tuple[float, float]:
        """
        Calculate position sizes for both assets in pair

        Uses Kelly Criterion with confidence adjustment
        
        Dynamic Sizing:
        - If Win Rate > 55% (min 5 trades): Increase size by 50-100%
        """
        try:
            # Base position size from config
            base_size = self.trading_config.max_position_size
            
            # --- DYNAMIC SIZING LOGIC ---
            try:
                from src.monitoring.performance_tracker import performance_tracker
                stats = performance_tracker.get_session_stats()
                win_rate = stats.get('win_rate', 0)
                total_trades = stats.get('total_trades', 0)
                
                if total_trades >= 5:
                    if win_rate >= 0.60:
                        base_size *= 2.0  # Double size for excellent performance
                        logger.info(f"🔥 HOT STREAK: Doubling position size! Win rate: {win_rate*100:.1f}%")
                    elif win_rate >= 0.55:
                        base_size *= 1.5  # 50% increase for good performance
                        logger.info(f"✅ Good Performance: Increasing size by 50%. Win rate: {win_rate*100:.1f}%")
            except Exception as e:
                logger.warning(f"Could not get performance stats for dynamic sizing: {e}")
            # ----------------------------

            # Adjust for confidence (0.5 to 1.0 multiplier)
            confidence_multiplier = 0.5 + (signal_confidence * 0.5)

            # Adjust for volatility if provided
            if volatility and volatility > 0:
                # Higher volatility = smaller position
                vol_multiplier = min(1.0, 0.5 / volatility) if volatility > 0.5 else 1.0
            else:
                vol_multiplier = 1.0

            # Calculate risk per trade
            risk_amount = account_balance * self.trading_config.risk_per_trade

            # Final position size
            position_size = min(
                base_size * confidence_multiplier * vol_multiplier,
                risk_amount * 10  # Max 10x the risk amount
            )

            # Ensure we don't exceed account balance
            position_size = min(position_size, account_balance * 0.2)  # Max 20% per position
            
            # Enforce minimum position size to meet exchange requirements
            # Bybit requires minimum 0.001 BTC (~$95-100 at current prices)
            # But with 1% risk and smaller base size, we need higher minimum
            min_position_size = 500.0  # $500 minimum to ensure BTC orders work
            position_size = max(position_size, min_position_size)

            logger.debug(
                f"Position size for {pair_id}: ${position_size:.2f} "
                f"(confidence: {signal_confidence:.2f}, vol_mult: {vol_multiplier:.2f})"
            )

            return position_size, position_size  # Equal sizes for both legs

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 100.0, 100.0  # Minimum safe size

    def check_risk_limits(
        self,
        current_positions: List[Position],
        daily_pnl: float,
        account_balance: float
    ) -> tuple[bool, List[str]]:
        """
        Check if all risk limits are respected

        Returns:
            - is_safe: bool
            - violations: List of violation messages
        """
        violations = []

        # 1. Check max concurrent positions
        if len(current_positions) >= self.trading_config.max_concurrent_pairs:
            violations.append(
                f"Max concurrent positions reached: {len(current_positions)}"
            )

        # 2. Check daily loss limit
        if daily_pnl < -self.trading_config.daily_loss_limit:
            violations.append(
                f"Daily loss limit exceeded: ${daily_pnl:.2f}"
            )

        # 3. Check total exposure
        # Position sizes are in CONTRACTS (qty), so we must multiply by price to get USD value
        total_exposure = 0.0
        for pos in current_positions:
            # Use current price if available, else entry price
            price_a = pos.current_price_a if pos.current_price_a > 0 else pos.entry_price_a
            price_b = pos.current_price_b if pos.current_price_b > 0 else pos.entry_price_b
            
            exposure_a = pos.size_a * price_a
            exposure_b = pos.size_b * price_b
            
            total_exposure += (exposure_a + exposure_b)
            
            # Debug log for large positions
            if (exposure_a + exposure_b) > 100000:
                logger.warning(f"Large position detected: {pos.pair_id} | A: {pos.size_a} * {price_a} = ${exposure_a:.2f} | B: {pos.size_b} * {price_b} = ${exposure_b:.2f}")

        max_exposure = account_balance * 0.8  # Max 80% of balance
        if total_exposure > max_exposure:
            violations.append(
                f"Total exposure too high: ${total_exposure:.2f} > ${max_exposure:.2f}"
            )

        # 4. Check drawdown
        self._update_drawdown(account_balance)
        if self.current_drawdown > 0.20:  # 20% drawdown
            violations.append(
                f"High drawdown: {self.current_drawdown * 100:.1f}%"
            )

        is_safe = len(violations) == 0
        return is_safe, violations

    def should_close_position(
        self,
        position: Position,
        current_price_a: float,
        current_price_b: float,
        current_zscore: float
    ) -> tuple[bool, str]:
        """
        Determine if a position should be closed

        Returns:
            - should_close: bool
            - reason: str
        """
        zscore_config = config.zscore
        
        # 0. MINIMUM HOLDING TIME - Prevent rapid open/close
        holding_time_delta = datetime.now() - position.entry_time
        holding_seconds = holding_time_delta.total_seconds()
        MIN_HOLDING_SECONDS = 30  # Quick in, quick out for HFT
        
        # Emergency Stop Loss (Always active)
        if position.unrealized_pnl and position.unrealized_pnl < -100:  # -$100 stop loss
             return True, f"Emergency stop loss: ${position.unrealized_pnl:.2f}"

        # Enforce minimum holding time for NON-emergency exits
        if holding_seconds < MIN_HOLDING_SECONDS:
            return False, f"Holding time {holding_seconds:.1f}s < {MIN_HOLDING_SECONDS}s"

        # Calculate P&L percentage
        position_value = position.size_a * position.entry_price_a
        pnl_pct = (position.unrealized_pnl / position_value * 100) if position_value > 0 else 0.0
        
        # AGGRESSIVE EXIT: Take profit at 0.2% (covers fees + small profit)
        if pnl_pct >= 0.2:  # Already checked holding_seconds >= 30 above
            return True, f'Quick profit: {pnl_pct:.2f}% (held {holding_seconds:.0f}s)'
        
        # VERY AGGRESSIVE: Exit at breakeven if held > 2 minutes
        if pnl_pct >= 0.0 and holding_seconds >= 120:
            return True, f'Breakeven exit after {holding_seconds:.0f}s'
        
        # Trailing Stop Logic (Tighter for HFT)
        ACTIVATION_THRESHOLD = 0.3  # Activate at 0.3% profit
        TRAILING_DIST = 0.15  # Trail by 0.15%
        
        if pnl_pct >= ACTIVATION_THRESHOLD:
            # Track max profit
            if not hasattr(position, 'max_profit_pct'):
                position.max_profit_pct = pnl_pct
            else:
                position.max_profit_pct = max(position.max_profit_pct, pnl_pct)
            
            # Exit if profit drops by TRAILING_DIST from max
            if pnl_pct < (position.max_profit_pct - TRAILING_DIST):
                return True, f'Trailing stop: {pnl_pct:.2f}% (max was {position.max_profit_pct:.2f}%)'
        
        # TIGHT stop loss (-0.3% of position value)
        if pnl_pct <= -0.3:
            return True, f"P&L stop-loss: {pnl_pct:.2f}%"

        # 2. Stop-loss: z-score too extreme
        if abs(current_zscore) > zscore_config.stoploss_threshold:
            return True, f"Stop-loss: z-score {current_zscore:.2f}"

        # 3. Exit: mean reversion (z-score back to normal)
        if abs(current_zscore) < zscore_config.exit_threshold:
            return True, f"Mean reversion: z-score {current_zscore:.2f}"

        # 4. Time-based exit: holding too long
        max_holding_hours = config.yaml_config.get('strategy', {}).get('signals', {}).get('max_holding_period_hours', 24)

        if holding_time_delta > timedelta(hours=max_holding_hours):
            return True, f"Max holding period exceeded: {holding_seconds / 3600:.1f} hours"

        # 5. P&L-based stop-loss
        if position.unrealized_pnl:
            # Stop-loss at -0.5% of position value
            position_value = position.size_a * position.entry_price_a
            stop_loss_amount = -position_value * 0.005  # -0.5%

            if position.unrealized_pnl < stop_loss_amount:
                return True, f"P&L stop-loss: ${position.unrealized_pnl:.2f}"

        return False, ""

    def calculate_risk_metrics(
        self,
        current_positions: List[Position],
        trade_history: List[Dict[str, Any]],
        account_balance: float,
        daily_pnl: float
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        try:
            # Unrealized P&L
            unrealized_pnl = sum(
                pos.unrealized_pnl or 0.0
                for pos in current_positions
            )

            # Sharpe ratio (if we have enough trades)
            sharpe_ratio = None
            if len(trade_history) >= 30:
                returns = [trade['pnl_percent'] / 100 for trade in trade_history]
                mean_return = sum(returns) / len(returns)
                std_return = (sum((r - mean_return) ** 2 for r in returns) / len(returns)) ** 0.5

                if std_return > 0:
                    # Annualized Sharpe (assuming ~100 trades per year)
                    sharpe_ratio = (mean_return / std_return) * (100 ** 0.5)

            # Win rate
            win_rate = None
            if trade_history:
                wins = sum(1 for trade in trade_history if trade['pnl'] > 0)
                win_rate = wins / len(trade_history)

            # Average latency (placeholder)
            avg_latency = None

            # Total exposure
            # size_a and size_b are already in USD, so just sum them
            total_exposure = sum(
                pos.size_a + pos.size_b
                for pos in current_positions
            )

            return RiskMetrics(
                timestamp=datetime.now(),
                total_positions=len(current_positions),
                total_exposure=total_exposure,
                daily_pnl=daily_pnl,
                daily_pnl_percent=(daily_pnl / account_balance * 100) if account_balance > 0 else 0,
                unrealized_pnl=unrealized_pnl,
                max_drawdown=self.current_drawdown,
                sharpe_ratio=sharpe_ratio,
                win_rate=win_rate,
                average_latency_ms=avg_latency
            )

        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(
                timestamp=datetime.now(),
                total_positions=0,
                total_exposure=0.0,
                daily_pnl=0.0,
                daily_pnl_percent=0.0,
                unrealized_pnl=0.0,
                max_drawdown=0.0
            )

    def _update_drawdown(self, current_equity: float):
        """Update drawdown calculation"""
        if current_equity > self.max_equity:
            self.max_equity = current_equity

        if self.max_equity > 0:
            self.current_drawdown = (self.max_equity - current_equity) / self.max_equity
        else:
            self.current_drawdown = 0.0

    def record_trade(self, trade: Dict[str, Any]):
        """Record completed trade for analysis"""
        self.trade_history.append(trade)

        # Keep last 1000 trades
        if len(self.trade_history) > 1000:
            self.trade_history = self.trade_history[-1000:]

    def get_recommendation(
        self,
        signal_action: str,
        current_positions: List[Position],
        account_balance: float,
        daily_pnl: float
    ) -> Dict[str, Any]:
        """
        Get risk management recommendation

        Returns:
            Dictionary with action and reason
        """
        is_safe, violations = self.check_risk_limits(
            current_positions,
            daily_pnl,
            account_balance
        )

        if not is_safe:
            return {
                'action': 'PAUSE',
                'reason': f"Risk violations: {'; '.join(violations)}",
                'confidence': 1.0
            }

        # If signal wants to open a position
        if signal_action in ['LONG_SPREAD', 'SHORT_SPREAD']:
            if len(current_positions) >= self.trading_config.max_concurrent_pairs:
                return {
                    'action': 'HOLD',
                    'reason': 'Max positions reached',
                    'confidence': 1.0
                }

        return {
            'action': 'APPROVE',
            'reason': 'Risk checks passed',
            'confidence': 1.0
        }
