"""Orchestrator agent - coordinates all other agents"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import pandas as pd

from src.agents.quant_agent import QuantAgent
from src.agents.sentiment_agent import SentimentAgent
from src.agents.risk_agent import RiskAgent
from src.strategy.strategy_manager import StrategyManager
from src.data.models import Signal, Position, TradeSignal
from src.data.bybit_client import get_bybit_client
from src.config import config

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    Main orchestrator that coordinates all agents

    Decision Flow:
    1. Quant Agent: Statistical analysis and initial signals
    2. Sentiment Agent: News/event analysis and market sentiment
    3. Risk Agent: Position sizing and risk checks
    4. Orchestrator: Final decision based on agent consensus
    """

    def __init__(self):
        self.quant_agent = QuantAgent()
        self.sentiment_agent = SentimentAgent()
        self.risk_agent = RiskAgent()
        self.strategy_manager = StrategyManager()  # Multi-strategy manager
        self.client = get_bybit_client()  # For order book data

        self.agent_config = config.yaml_config.get('agents', {})
        self.orchestrator_config = self.agent_config.get('orchestrator', {})

        self.min_consensus = self.orchestrator_config.get('min_agent_consensus', 2)
        self.enable_override = self.orchestrator_config.get('enable_override', True)

        logger.info("Orchestrator initialized with multi-strategy support")

    async def make_decision(
        self,
        symbol_a: str,
        symbol_b: str,
        price_history_a: pd.Series,
        price_history_b: pd.Series,
        current_positions: List[Position],
        account_balance: float,
        daily_pnl: float
    ) -> Dict[str, Any]:
        """
        Make trading decision for a pair

        Returns:
            Decision dictionary with action, reason, and metadata
        """
        try:
            pair_id = f"{symbol_a}_{symbol_b}"
            logger.info(f"Making decision for {pair_id}...")

            # Check if we have a current position for this pair
            current_position = None
            for pos in current_positions:
                if pos.pair_id == pair_id:
                    current_position = pos
                    break

            # 1. Get quantitative analysis from multiple strategies
            logger.debug("Running multi-strategy analysis...")

            # Run old quant agent for cointegration data
            quant_analysis = await self.quant_agent.analyze_pair(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                price_history_a=price_history_a,
                price_history_b=price_history_b,
                current_position='long_spread' if current_position and current_position.side_a.value == 'Long' else
                                'short_spread' if current_position else None
            )

            # Fetch order book data for OBI strategy
            orderbook_a = self.client.get_orderbook(symbol_a)
            orderbook_b = self.client.get_orderbook(symbol_b)

            # Run new multi-strategy system
            strategy_signal = await self.strategy_manager.generate_aggregated_signal(
                prices_a=price_history_a,
                prices_b=price_history_b,
                pair_id=pair_id,
                current_position='LONG_SPREAD' if current_position and current_position.side_a.value == 'Long' else
                               'SHORT_SPREAD' if current_position else None,
                orderbook_a=orderbook_a,
                orderbook_b=orderbook_b
            )

            logger.info(f"Multi-strategy signal: {strategy_signal.action} "
                       f"(confidence: {strategy_signal.confidence:.2f}, consensus: {strategy_signal.consensus})")

            # Use strategy manager signal if it's strong/moderate, fallback to quant for weak signals
            if strategy_signal.consensus in ['STRONG', 'MODERATE'] and strategy_signal.action != 'HOLD':
                quant_recommendation = {
                    'action': strategy_signal.action,
                    'confidence': strategy_signal.confidence,
                    'reason': f"Multi-strategy {strategy_signal.consensus} consensus: {strategy_signal.action}"
                }
            elif quant_analysis.get('recommendation'):
                quant_recommendation = quant_analysis['recommendation']
            else:
                return self._make_decision_response('HOLD', 'Insufficient data from all strategies', 0.0)

            # 2. Get sentiment analysis (DISABLED)
            logger.debug("Sentiment analysis disabled by user request")
            sentiment_score = 0.0
            sentiment_data = type('obj', (object,), {'summary': 'Sentiment disabled', 'sentiment_score': 0.0})

            # 3. Check for major events (DISABLED)
            # Skipping major events check - trading on pure statistics

            # 4. Get risk management input
            logger.debug("Running risk assessment...")

            # First check general risk limits
            is_safe, violations = self.risk_agent.check_risk_limits(
                current_positions,
                daily_pnl,
                account_balance
            )

            if not is_safe:
                logger.warning(f"Risk violations: {violations}")
                if current_position:
                    # We might need to close positions to reduce risk
                    return self._make_decision_response(
                        'CLOSE',
                        f'Risk limit: {violations[0]}',
                        1.0
                    )
                else:
                    return self._make_decision_response(
                        'HOLD',
                        f'Risk limit: {violations[0]}',
                        1.0
                    )

            # 5. Combine agent recommendations
            decision = self._combine_agent_decisions(
                quant_recommendation=quant_recommendation,
                sentiment_score=sentiment_score,
                sentiment_data=sentiment_data,
                current_position=current_position,
                quant_analysis=quant_analysis
            )

            # 6. Final risk check for the proposed action
            risk_recommendation = self.risk_agent.get_recommendation(
                signal_action=decision['action'],
                current_positions=current_positions,
                account_balance=account_balance,
                daily_pnl=daily_pnl
            )

            if risk_recommendation['action'] != 'APPROVE':
                return self._make_decision_response(
                    risk_recommendation['action'],
                    risk_recommendation['reason'],
                    risk_recommendation['confidence']
                )

            # 7. Calculate position size if opening a position
            if decision['action'] in ['LONG_SPREAD', 'SHORT_SPREAD']:
                size_a, size_b = self.risk_agent.calculate_position_size(
                    pair_id=pair_id,
                    account_balance=account_balance,
                    signal_confidence=decision['confidence']
                )
                decision['position_size_a'] = size_a
                decision['position_size_b'] = size_b
                decision['hedge_ratio'] = quant_analysis['cointegration']['hedge_ratio']

            logger.info(
                f"Decision for {pair_id}: {decision['action']} "
                f"(confidence: {decision['confidence']:.2f})"
            )

            return decision

        except Exception as e:
            logger.error(f"Error making decision: {e}")
            return self._make_decision_response('HOLD', f'Error: {str(e)}', 0.0)

    def _combine_agent_decisions(
        self,
        quant_recommendation: Dict[str, Any],
        sentiment_score: float,
        sentiment_data: Any,
        current_position: Optional[Position],
        quant_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combine recommendations from all agents

        Voting system:
        - Quant Agent: Statistical signal
        - Sentiment Agent: News/event impact
        - Consensus required: min_consensus agents must agree
        """
        quant_action = quant_recommendation['action']
        quant_confidence = quant_recommendation['confidence']

        # Sentiment voting
        # Strong sentiment can influence decisions
        sentiment_action = self._sentiment_to_action(
            sentiment_score,
            quant_action,
            current_position
        )

        # Collect votes
        votes = {
            'quant': {
                'action': quant_action,
                'confidence': quant_confidence,
                'reason': quant_recommendation['reason']
            },
            'sentiment': {
                'action': sentiment_action['action'],
                'confidence': sentiment_action['confidence'],
                'reason': sentiment_action['reason']
            }
        }

        # Count votes for each action
        action_votes = {}
        for agent, vote in votes.items():
            action = vote['action']
            if action not in action_votes:
                action_votes[action] = {
                    'count': 0,
                    'total_confidence': 0.0,
                    'agents': []
                }

            action_votes[action]['count'] += 1
            action_votes[action]['total_confidence'] += vote['confidence']
            action_votes[action]['agents'].append(agent)

        # Find action with most votes
        best_action = max(action_votes.items(), key=lambda x: (x[1]['count'], x[1]['total_confidence']))
        action = best_action[0]
        action_data = best_action[1]

        # Calculate overall confidence
        confidence = action_data['total_confidence'] / len(votes)

        # Build reason
        agent_list = ', '.join(action_data['agents'])
        reason = f"Consensus ({action_data['count']}/{len(votes)} agents: {agent_list})"

        # Add specific details
        if quant_action == action:
            reason += f" | Quant: {votes['quant']['reason']}"
        if sentiment_action['action'] == action:
            reason += f" | Sentiment: {votes['sentiment']['reason']}"

        return self._make_decision_response(
            action=action,
            reason=reason,
            confidence=confidence,
            metadata={
                'votes': votes,
                'sentiment_score': sentiment_score,
                'sentiment_summary': sentiment_data.summary,
                'zscore': quant_analysis['zscore']['zscore'] if quant_analysis.get('zscore') else 0,
                'pvalue': quant_analysis['cointegration']['pvalue'] if quant_analysis.get('cointegration') else 1.0,
                'hedge_ratio': quant_analysis['cointegration']['hedge_ratio'] if quant_analysis.get('cointegration') else 1.0,
                'half_life': quant_analysis['cointegration'].get('half_life') if quant_analysis.get('cointegration') else None,
                'mean_reversion_score': quant_analysis.get('mean_reversion_score', 0),
                'is_cointegrated': quant_analysis['cointegration']['is_cointegrated'] if quant_analysis.get('cointegration') else False
            }
        )

    def _sentiment_to_action(
        self,
        sentiment_score: float,
        quant_action: str,
        current_position: Optional[Position]
    ) -> Dict[str, Any]:
        """
        Convert sentiment score to trading action

        Sentiment influences but doesn't override statistical signals
        """
        # Strong negative sentiment
        if sentiment_score < -0.6:
            if quant_action == 'LONG_SPREAD':
                return {
                    'action': 'HOLD',
                    'confidence': 0.7,
                    'reason': f'Very negative sentiment ({sentiment_score:.2f})'
                }

        # Strong positive sentiment
        elif sentiment_score > 0.6:
            if quant_action == 'SHORT_SPREAD':
                return {
                    'action': 'HOLD',
                    'confidence': 0.7,
                    'reason': f'Very positive sentiment ({sentiment_score:.2f})'
                }

        # Extreme sentiment might warrant closing positions
        if abs(sentiment_score) > 0.8 and current_position:
            return {
                'action': 'CLOSE',
                'confidence': 0.6,
                'reason': f'Extreme sentiment ({sentiment_score:.2f})'
            }

        # Default: agree with quant signal
        # In pure quant mode (sentiment = 0), use high confidence
        if sentiment_score == 0.0:
            return {
                'action': quant_action,
                'confidence': 0.9,  # High confidence in pure quant mode
                'reason': 'Pure quant signal (sentiment disabled)'
            }

        return {
            'action': quant_action,
            'confidence': 0.5 + abs(sentiment_score) * 0.2,
            'reason': f'Sentiment {sentiment_score:.2f} aligns'
        }

    def _make_decision_response(
        self,
        action: str,
        reason: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create standardized decision response"""
        return {
            'action': action,
            'reason': reason,
            'confidence': confidence,
            'timestamp': datetime.now(),
            'metadata': metadata or {}
        }

    async def batch_make_decisions(
        self,
        pairs: List[Dict[str, Any]],
        price_data: Dict[str, pd.Series],
        candle_data: Dict[str, pd.DataFrame],  # Added candle_data
        current_positions: List[Position],
        account_balance: float,
        daily_pnl: float
    ) -> List[Dict[str, Any]]:
        """
        Make decisions for multiple pairs concurrently

        Returns:
            List of decisions
        """
        tasks = []
        pairs_list = []

        for pair in pairs:
            if not pair.get('enabled', True):
                continue

            symbol_a = pair['symbol_a']
            symbol_b = pair['symbol_b']

            if symbol_a not in price_data or symbol_b not in price_data:
                continue

            task = self.make_decision(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                price_history_a=price_data[symbol_a],
                price_history_b=price_data[symbol_b],
                candle_history_a=candle_data.get(symbol_a),  # Pass candles
                candle_history_b=candle_data.get(symbol_b),  # Pass candles
                current_positions=current_positions,
                account_balance=account_balance,
                daily_pnl=daily_pnl
            )
            tasks.append(task)
            pairs_list.append(pair)

        results = await asyncio.gather(*tasks)
        
        # Attach pair info to decisions
        decisions = []
        for decision, pair in zip(results, pairs_list):
            decision['pair'] = pair
            decisions.append(decision)
            
        return decisions

    async def make_decision(
        self,
        symbol_a: str,
        symbol_b: str,
        price_history_a: pd.Series,
        price_history_b: pd.Series,
        candle_history_a: Optional[pd.DataFrame],  # Added
        candle_history_b: Optional[pd.DataFrame],  # Added
        current_positions: List[Position],
        account_balance: float,
        daily_pnl: float
    ) -> Dict[str, Any]:
        """
        Make trading decision for a pair

        Returns:
            Decision dictionary with action, reason, and metadata
        """
        try:
            pair_id = f"{symbol_a}_{symbol_b}"
            logger.info(f"Making decision for {pair_id}...")

            # Check if we have a current position for this pair
            current_position = None
            for pos in current_positions:
                if pos.pair_id == pair_id:
                    current_position = pos
                    break

            # 1. Get quantitative analysis from multiple strategies
            logger.debug("Running multi-strategy analysis...")

            # Run old quant agent for cointegration data
            quant_analysis = await self.quant_agent.analyze_pair(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                price_history_a=price_history_a,
                price_history_b=price_history_b,
                current_position='long_spread' if current_position and current_position.side_a.value == 'Long' else
                                'short_spread' if current_position else None
            )

            # Fetch order book data for OBI strategy
            orderbook_a = self.client.get_orderbook(symbol_a)
            orderbook_b = self.client.get_orderbook(symbol_b)

            # Run new multi-strategy system
            strategy_signal = await self.strategy_manager.generate_aggregated_signal(
                prices_a=price_history_a,
                prices_b=price_history_b,
                candles_a=candle_history_a,  # Pass candles
                candles_b=candle_history_b,  # Pass candles
                pair_id=pair_id,
                current_position='LONG_SPREAD' if current_position and current_position.side_a.value == 'Long' else
                               'SHORT_SPREAD' if current_position else None,
                orderbook_a=orderbook_a,
                orderbook_b=orderbook_b
            )
            # 3. Sentiment Analysis (DISABLED - No API Quota)
            # sentiment_score, sentiment_data = await self.sentiment_agent.analyze_sentiment(
            #     symbol_a=symbol_a,
            #     symbol_b=symbol_b
            # )
            sentiment_score = 0.0  # Neutral
            class DummySentimentData:
                def __init__(self, summary):
                    self.summary = summary
            sentiment_data = DummySentimentData("Sentiment analysis disabled")
            
            # logger.info(f"Sentiment for {symbol_a}: {sentiment_score:.2f} ({sentiment_summary})")

            # 3. Combine all agent recommendations
            # Convert AggregatedSignal to dict for _combine_agent_decisions
            strategy_signal_dict = {
                'action': strategy_signal.action,
                'confidence': strategy_signal.confidence,
                'reason': f"{strategy_signal.consensus} consensus from {len(strategy_signal.strategy_signals)} strategies"
            }
            
            decision = self._combine_agent_decisions(
                quant_recommendation=strategy_signal_dict,
                sentiment_score=sentiment_score,
                sentiment_data=sentiment_data,
                current_position=current_position,
                quant_analysis=quant_analysis
            )

            # 6. Final risk check for the proposed action
            risk_recommendation = self.risk_agent.get_recommendation(
                signal_action=decision['action'],
                current_positions=current_positions,
                account_balance=account_balance,
                daily_pnl=daily_pnl
            )

            if risk_recommendation['action'] != 'APPROVE':
                return self._make_decision_response(
                    risk_recommendation['action'],
                    risk_recommendation['reason'],
                    risk_recommendation['confidence']
                )

            # 7. Calculate position size if opening a position
            if decision['action'] in ['LONG_SPREAD', 'SHORT_SPREAD']:
                size_a, size_b = self.risk_agent.calculate_position_size(
                    pair_id=pair_id,
                    account_balance=account_balance,
                    signal_confidence=decision['confidence']
                )
                decision['position_size_a'] = size_a
                decision['position_size_b'] = size_b
                decision['hedge_ratio'] = quant_analysis['cointegration']['hedge_ratio']

            # Add top-level symbol info for robustness
            decision['symbol_a'] = symbol_a
            decision['symbol_b'] = symbol_b
            decision['pair_id'] = pair_id

            logger.info(
                f"Decision for {pair_id}: {decision['action']} "
                f"(confidence: {decision['confidence']:.2f})"
            )

            return decision

        except Exception as e:
            logger.error(f"Error making decision: {e}")
            return self._make_decision_response('HOLD', f'Error: {str(e)}', 0.0)

    def clear_all_caches(self):
        """Clear all agent caches"""
        self.quant_agent.clear_cache()
        self.sentiment_agent.clear_cache()
        logger.info("All agent caches cleared")

    async def make_all_strategy_decisions(
        self,
        symbol_a: str,
        symbol_b: str,
        price_history_a: pd.Series,
        price_history_b: pd.Series,
        current_positions: List[Position],
        account_balance: float,
        daily_pnl: float
    ) -> List[Dict[str, Any]]:
        """
        Make trading decisions for ALL strategies independently (OR logic)

        Returns a list of decisions, one for EACH strategy that signals

        This allows parallel execution of multiple strategies on the same pair
        """
        try:
            pair_id = f"{symbol_a}_{symbol_b}"
            logger.info(f"Getting individual strategy signals for {pair_id}...")

            # Check if we have a current position for this pair
            current_position = None
            for pos in current_positions:
                if pos.pair_id == pair_id:
                    current_position = pos
                    break

            # Fetch order book data for OBI strategy
            orderbook_a = self.client.get_orderbook(symbol_a)
            orderbook_b = self.client.get_orderbook(symbol_b)

            # Get quantitative analysis (for cointegration data)
            quant_analysis = await self.quant_agent.analyze_pair(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                price_history_a=price_history_a,
                price_history_b=price_history_b,
                current_position='long_spread' if current_position and current_position.side_a.value == 'Long' else
                                'short_spread' if current_position else None
            )

            # Get ALL individual strategy signals (OR logic - no aggregation!)
            strategy_signals = await self.strategy_manager.generate_all_individual_signals(
                prices_a=price_history_a,
                prices_b=price_history_b,
                pair_id=pair_id,
                current_position='LONG_SPREAD' if current_position and current_position.side_a.value == 'Long' else
                               'SHORT_SPREAD' if current_position else None,
                orderbook_a=orderbook_a,
                orderbook_b=orderbook_b
            )

            # Risk check first
            is_safe, violations = self.risk_agent.check_risk_limits(
                current_positions,
                daily_pnl,
                account_balance
            )

            if not is_safe:
                logger.warning(f"Risk violations: {violations}")
                return []  # No trades if risk limits breached

            # Create a decision for EACH strategy signal
            decisions = []

            for strategy_name, signal in strategy_signals.items():
                action = signal['action']

                # Risk check for this specific action
                risk_recommendation = self.risk_agent.get_recommendation(
                    signal_action=action,
                    current_positions=current_positions,
                    account_balance=account_balance,
                    daily_pnl=daily_pnl
                )

                if risk_recommendation['action'] != 'APPROVE':
                    logger.info(f"{strategy_name}: {action} blocked by risk agent")
                    continue

                # Calculate position size if opening a position
                decision = {
                    'action': action,
                    'reason': f"{strategy_name}: {signal.get('details', {}).get('entry_reason', 'Signal')}",
                    'confidence': signal['confidence'],
                    'timestamp': datetime.now(),
                    'strategy': strategy_name,
                    'pair_id': pair_id,
                    'symbol_a': symbol_a,
                    'symbol_b': symbol_b,
                    'metadata': {
                        'strategy_name': strategy_name,
                        'zscore': quant_analysis.get('zscore', {}).get('zscore', 0),
                        'pvalue': quant_analysis.get('cointegration', {}).get('pvalue', 1.0),
                        'hedge_ratio': quant_analysis.get('cointegration', {}).get('hedge_ratio', 1.0),
                        'half_life': quant_analysis.get('cointegration', {}).get('half_life'),
                        'is_cointegrated': quant_analysis.get('cointegration', {}).get('is_cointegrated', False)
                    }
                }

                if action in ['LONG_SPREAD', 'SHORT_SPREAD']:
                    size_a, size_b = self.risk_agent.calculate_position_size(
                        pair_id=pair_id,
                        account_balance=account_balance,
                        signal_confidence=signal['confidence']
                    )
                    decision['position_size_a'] = size_a
                    decision['position_size_b'] = size_b
                    decision['hedge_ratio'] = quant_analysis.get('cointegration', {}).get('hedge_ratio', 1.0)

                decisions.append(decision)

                logger.info(
                    f"✓ {strategy_name}: {action} (confidence: {signal['confidence']:.2f})"
                )

            if decisions:
                logger.info(f"Generated {len(decisions)} decisions for {pair_id} from {len(strategy_signals)} strategy signals")

            return decisions

        except Exception as e:
            logger.error(f"Error making strategy decisions: {e}", exc_info=True)
            return []

    async def batch_make_all_strategy_decisions(
        self,
        pairs: List[Dict[str, Any]],
        price_data: Dict[str, pd.Series],
        current_positions: List[Position],
        account_balance: float,
        daily_pnl: float
    ) -> List[Dict[str, Any]]:
        """
        Make decisions for multiple pairs using OR logic (all strategies independently)

        Returns:
            Flattened list of ALL decisions from ALL strategies across ALL pairs
        """
        all_decisions = []
        tasks = []

        for pair in pairs:
            if not pair.get('enabled', True):
                continue

            symbol_a = pair['symbol_a']
            symbol_b = pair['symbol_b']

            if symbol_a not in price_data or symbol_b not in price_data:
                continue

            task = self.make_all_strategy_decisions(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                price_history_a=price_data[symbol_a],
                price_history_b=price_data[symbol_b],
                current_positions=current_positions,
                account_balance=account_balance,
                daily_pnl=daily_pnl
            )
            tasks.append((pair, task))

        # Run all pairs in parallel
        results = await asyncio.gather(*[task for _, task in tasks])

        # Flatten results and add pair info
        for (pair, _), decisions in zip(tasks, results):
            for decision in decisions:
                decision['pair'] = pair
                all_decisions.append(decision)

        logger.info(f"Generated {len(all_decisions)} total strategy decisions across {len(pairs)} pairs")

        return all_decisions
