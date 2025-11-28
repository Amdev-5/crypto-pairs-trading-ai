"""Position management"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

from src.data.models import Position, Trade, PositionSide
from src.config import config

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages open positions and trade history"""

    def __init__(self):
        self.open_positions: Dict[str, Position] = {}
        self.closed_trades: List[Trade] = []
        self.daily_pnl: float = 0.0
        self.total_pnl: float = 0.0
        
        logger.info(f"PositionManager initialized. ID: {id(self)}")
        logger.info(f"Initial state: {len(self.open_positions)} open positions")

    def add_position(
        self,
        pair_id: str,
        symbol_a: str,
        symbol_b: str,
        side_a: PositionSide,
        side_b: PositionSide,
        size_a: float,
        size_b: float,
        entry_price_a: float,
        entry_price_b: float,
        hedge_ratio: float,
        entry_zscore: float
    ) -> Position:
        """Add a new position"""
        position = Position(
            pair_id=pair_id,
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            side_a=side_a,
            side_b=side_b,
            size_a=size_a,
            size_b=size_b,
            entry_price_a=entry_price_a,
            entry_price_b=entry_price_b,
            current_price_a=entry_price_a,
            current_price_b=entry_price_b,
            hedge_ratio=hedge_ratio,
            entry_zscore=entry_zscore,
            current_zscore=entry_zscore,
            entry_time=datetime.now(),
            unrealized_pnl=0.0,
            status="open"
        )

        self.open_positions[pair_id] = position
        logger.info(f"Position opened: {pair_id} | {side_a.value} {size_a} {symbol_a}, {side_b.value} {size_b} {symbol_b}")

        return position

    def update_position(
        self,
        pair_id: str,
        current_price_a: float,
        current_price_b: float,
        current_zscore: float
    ):
        """Update position with current prices and P&L"""
        if pair_id not in self.open_positions:
            return

        if current_price_a <= 0 or current_price_b <= 0:
            logger.warning(f"Invalid prices for position update {pair_id}: {current_price_a}, {current_price_b}")
            return

        position = self.open_positions[pair_id]

        # Update prices
        position.current_price_a = current_price_a
        position.current_price_b = current_price_b
        position.current_zscore = current_zscore

        # Calculate unrealized P&L
        pnl_a = self._calculate_pnl(
            side=position.side_a,
            entry_price=position.entry_price_a,
            current_price=current_price_a,
            size=position.size_a
        )

        pnl_b = self._calculate_pnl(
            side=position.side_b,
            entry_price=position.entry_price_b,
            current_price=current_price_b,
            size=position.size_b
        )

        position.unrealized_pnl = pnl_a + pnl_b

    def close_position(
        self,
        pair_id: str,
        exit_price_a: float,
        exit_price_b: float,
        exit_zscore: float,
        reason: str
    ) -> Optional[Trade]:
        """Close a position and record trade"""
        if pair_id not in self.open_positions:
            logger.warning(f"Attempted to close non-existent position: {pair_id}")
            return None

        position = self.open_positions[pair_id]

        # Calculate final P&L
        pnl_a = self._calculate_pnl(
            side=position.side_a,
            entry_price=position.entry_price_a,
            current_price=exit_price_a,
            size=position.size_a
        )

        pnl_b = self._calculate_pnl(
            side=position.side_b,
            entry_price=position.entry_price_b,
            current_price=exit_price_b,
            size=position.size_b
        )

        total_pnl = pnl_a + pnl_b

        # Calculate commission (Bybit: 0.06% taker fee)
        commission_rate = 0.0006
        position_value_a = position.size_a * exit_price_a
        position_value_b = position.size_b * exit_price_b
        commission = (position_value_a + position_value_b) * commission_rate * 2  # Entry + exit

        net_pnl = total_pnl - commission

        # Calculate duration
        duration = (datetime.now() - position.entry_time).total_seconds() / 60  # minutes

        # Calculate P&L percentage
        initial_value = (position.size_a * position.entry_price_a +
                        position.size_b * position.entry_price_b)
        pnl_percent = (net_pnl / initial_value * 100) if initial_value > 0 else 0.0

        # Create trade record
        trade = Trade(
            pair_id=pair_id,
            symbol_a=position.symbol_a,
            symbol_b=position.symbol_b,
            side_a=position.side_a,
            side_b=position.side_b,
            size_a=position.size_a,
            size_b=position.size_b,
            entry_price_a=position.entry_price_a,
            entry_price_b=position.entry_price_b,
            exit_price_a=exit_price_a,
            exit_price_b=exit_price_b,
            hedge_ratio=position.hedge_ratio,
            entry_zscore=position.entry_zscore,
            exit_zscore=exit_zscore,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            duration_minutes=duration,
            pnl=net_pnl,
            pnl_percent=pnl_percent,
            commission=commission,
            reason=reason
        )

        # Update tracking
        self.closed_trades.append(trade)
        self.daily_pnl += net_pnl
        self.total_pnl += net_pnl

        # Remove from open positions
        del self.open_positions[pair_id]

        # Log to production performance tracker
        try:
            from src.monitoring.performance_tracker import performance_tracker
            performance_tracker.log_trade({
                'pair_id': trade.pair_id,
                'pnl': trade.pnl,
                'pnl_percent': trade.pnl_percent,
                'duration_minutes': trade.duration_minutes,
                'strategy': 'multi_strategy',  # TODO: Pass actual strategy name
                'entry_price_a': trade.entry_price_a,
                'exit_price_a': trade.exit_price_a,
                'commission': trade.commission
            })
            performance_tracker.print_performance_report()
        except Exception as e:
            logger.error(f"Error logging to performance tracker: {e}")

        logger.info(
            f"Position closed: {pair_id} | P&L: ${net_pnl:.2f} ({pnl_percent:.2f}%) | "
            f"Duration: {duration:.1f}m | Reason: {reason}"
        )

        return trade

    def _calculate_pnl(
        self,
        side: PositionSide,
        entry_price: float,
        current_price: float,
        size: float
    ) -> float:
        # Calculate P&L
        if side == PositionSide.LONG:
            pnl = (current_price - entry_price) * size
        elif side == PositionSide.SHORT:
            pnl = (entry_price - current_price) * size
        else:
            pnl = 0.0
            
        # Debug massive P&L anomalies
        if abs(pnl) > 10000:
            logger.error(f"🚨 ANOMALY P&L: ${pnl:.2f} | Side: {side} | Size: {size} | Entry: {entry_price} | Current: {current_price}")
            
        return pnl

    def get_position(self, pair_id: str) -> Optional[Position]:
        """Get position by pair_id"""
        return self.open_positions.get(pair_id)

    def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        return list(self.open_positions.values())

    def get_recent_trades(self, limit: int = 100) -> List[Trade]:
        """Get recent closed trades"""
        return self.closed_trades[-limit:]

    def get_position_count(self) -> int:
        """Get number of open positions"""
        return len(self.open_positions)

    def reset_daily_pnl(self):
        """Reset daily P&L (call at start of each day)"""
        self.daily_pnl = 0.0
        logger.info("Daily P&L reset")
    
    def clear_all_history(self):
        """Clear all trade history and reset P&L (use at startup)"""
        num_trades = len(self.closed_trades)
        logger.info(f"🧹 Clearing {num_trades} closed trades from memory...")
        
        if num_trades > 0:
            total_phantom_pnl = sum(t.pnl for t in self.closed_trades)
            logger.warning(f"   Phantom P&L being cleared: ${total_phantom_pnl:.2f}")
            for i, trade in enumerate(self.closed_trades[:5]):  # Show first 5
                logger.info(f"   Trade {i+1}: {trade.pair_id}, P&L: ${trade.pnl:.2f}, Duration: {trade.duration_minutes:.1f}m")
        
        self.closed_trades.clear()
        self.open_positions.clear()  # CRITICAL FIX: Clear open positions too
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        logger.info(f"✅ Memory cleared. New state: {len(self.closed_trades)} trades, {len(self.open_positions)} positions, Daily P&L: ${self.daily_pnl:.2f}")

    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'average_pnl': 0.0,
                'total_pnl': self.total_pnl,
                'daily_pnl': self.daily_pnl
            }

        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]

        return {
            'total_trades': len(self.closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.closed_trades),
            'average_pnl': sum(t.pnl for t in self.closed_trades) / len(self.closed_trades),
            'average_winner': sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0,
            'average_loser': sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0,
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'largest_winner': max((t.pnl for t in self.closed_trades), default=0),
            'largest_loser': min((t.pnl for t in self.closed_trades), default=0),
        }
