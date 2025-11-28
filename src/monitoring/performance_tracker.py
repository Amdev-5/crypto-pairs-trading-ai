"""Production-grade performance tracking and statistics"""

import json
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Track and analyze trading performance metrics"""
    
    def __init__(self):
        self.metrics_file = "logs/performance_metrics.json"
        self.session_start = datetime.now()
        self.metrics = {
            'session_start': self.session_start.isoformat(),
            'trades': [],
            'daily_stats': {},
            'strategy_performance': {}
        }
    
    def log_trade(self, trade_data: Dict):
        """Log a completed trade"""
        self.metrics['trades'].append({
            'timestamp': datetime.now().isoformat(),
            'pair_id': trade_data.get('pair_id'),
            'pnl': trade_data.get('pnl', 0),
            'pnl_percent': trade_data.get('pnl_percent', 0),
            'duration_minutes': trade_data.get('duration_minutes', 0),
            'strategy': trade_data.get('strategy', 'unknown'),
            'entry_price_a': trade_data.get('entry_price_a'),
            'exit_price_a': trade_data.get('exit_price_a'),
            'commission': trade_data.get('commission', 0)
        })
        
        # Update strategy performance
        strategy = trade_data.get('strategy', 'unknown')
        if strategy not in self.metrics['strategy_performance']:
            self.metrics['strategy_performance'][strategy] = {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl': 0,
                'avg_pnl': 0
            }
        
        perf = self.metrics['strategy_performance'][strategy]
        perf['total_trades'] += 1
        perf['total_pnl'] += trade_data.get('pnl', 0)
        
        if trade_data.get('pnl', 0) > 0:
            perf['wins'] += 1
        else:
            perf['losses'] += 1
        
        perf['avg_pnl'] = perf['total_pnl'] / perf['total_trades']
        perf['win_rate'] = perf['wins'] / perf['total_trades']
        
        self._save_metrics()
    
    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        trades = self.metrics['trades']
        
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0
            }
        
        total_pnl = sum(t['pnl'] for t in trades)
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = len(wins) / len(trades) if trades else 0
        avg_pnl = total_pnl / len(trades)
        
        # Calculate Sharpe Ratio (simplified)
        if len(trades) > 1:
            returns = [t['pnl_percent'] for t in trades]
            mean_return = sum(returns) / len(returns)
            std_return = (sum((r - mean_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = (mean_return / std_return) if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Profit Factor
        gross_profit = sum(t['pnl'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            'total_trades': len(trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': profit_factor,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'avg_win': sum(t['pnl'] for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        }
    
    def print_performance_report(self):
        """Print detailed performance report"""
        stats = self.get_session_stats()
        
        print("\n" + "=" * 80)
        print("📊 PRODUCTION PERFORMANCE REPORT")
        print("=" * 80)
        print(f"Session Start: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Win Rate: {stats['win_rate']*100:.2f}%")
        print(f"Total P&L: ${stats['total_pnl']:.2f}")
        print(f"Average P&L: ${stats['avg_pnl']:.2f}")
        print(f"Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")
        print(f"Gross Profit: ${stats['gross_profit']:.2f}")
        print(f"Gross Loss: ${stats['gross_loss']:.2f}")
        print(f"Average Win: ${stats['avg_win']:.2f}")
        print(f"Average Loss: ${stats['avg_loss']:.2f}")
        
        print("\n📈 STRATEGY BREAKDOWN:")
        print("-" * 80)
        for strategy, perf in self.metrics['strategy_performance'].items():
            print(f"{strategy}:")
            print(f"  Trades: {perf['total_trades']}")
            print(f"  Win Rate: {perf.get('win_rate', 0)*100:.2f}%")
            print(f"  Total P&L: ${perf['total_pnl']:.2f}")
            print(f"  Avg P&L: ${perf['avg_pnl']:.2f}")
        
        print("=" * 80)
        
        # Performance grade
        if stats['total_trades'] >= 10:
            if stats['win_rate'] >= 0.6 and stats['sharpe_ratio'] >= 1.5:
                print("🏆 GRADE: EXCELLENT - Wall Street Level!")
            elif stats['win_rate'] >= 0.55 and stats['sharpe_ratio'] >= 1.0:
                print("✅ GRADE: GOOD - Profitable System")
            elif stats['win_rate'] >= 0.5:
                print("⚠️  GRADE: FAIR - Needs Optimization")
            else:
                print("❌ GRADE: POOR - Requires Immediate Fixes")
        else:
            print("ℹ️  Need more trades for accurate grading (minimum 10)")
        
        print("=" * 80 + "\n")
    
    def _save_metrics(self):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")


# Global tracker instance
performance_tracker = PerformanceTracker()
