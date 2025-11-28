"""
Order Rate Limiter
Prevents Bybit IOC errors by throttling order submission with intelligent cooldowns
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from collections import deque

logger = logging.getLogger(__name__)


class OrderRateLimiter:
    """
    Smart rate limiter for order execution
    Prevents IOC errors by managing order submission rate
    """
    
    def __init__(self):
        # Bybit limits: ~10 orders/second for testnet, ~50/second for mainnet
        self.max_orders_per_second = 5  # Conservative for testnet
        self.max_orders_per_minute = 100
        
        # Track recent orders
        self.recent_orders = deque(maxlen=self.max_orders_per_minute)
        
        # Cooldown state
        self.in_cooldown = False
        self.cooldown_until: Optional[datetime] = None
        self.consecutive_errors = 0
        
        # Adaptive cooldown (increases with consecutive errors)
        self.base_cooldown_seconds = 2.0
        self.max_cooldown_seconds = 30.0
        
    async def acquire(self, symbol: str) -> bool:
        """
        Request permission to place an order
        Returns True if order can proceed, False if should wait
        """
        now = datetime.now()
        
        # Check if in cooldown period
        if self.in_cooldown and self.cooldown_until:
            if now < self.cooldown_until:
                wait_seconds = (self.cooldown_until - now).total_seconds()
                logger.warning(f"⏸️  In cooldown for {wait_seconds:.1f}s. Waiting...")
                await asyncio.sleep(wait_seconds)
            else:
                # Cooldown expired
                self.in_cooldown = False
                self.cooldown_until = None
                logger.info("✅ Cooldown period ended")
        
        # Remove orders older than 1 second
        cutoff_1s = now - timedelta(seconds=1)
        while self.recent_orders and self.recent_orders[0] < cutoff_1s:
            self.recent_orders.popleft()
        
        # Check rate limits
        orders_last_second = len(self.recent_orders)
        
        if orders_last_second >= self.max_orders_per_second:
            # Hit per-second limit, wait briefly
            wait_time = 1.0 / self.max_orders_per_second
            logger.info(f"⏱️  Rate limit: {orders_last_second} orders/sec. Waiting {wait_time:.2f}s...")
            await asyncio.sleep(wait_time)
        
        # Record this order
        self.recent_orders.append(now)
        return True
    
    def report_error(self, error_msg: str):
        """
        Report an IOC or rate limit error
        Triggers adaptive cooldown
        """
        self.consecutive_errors += 1
        
        # Calculate adaptive cooldown (exponential backoff)
        cooldown_seconds = min(
            self.base_cooldown_seconds * (2 ** (self.consecutive_errors - 1)),
            self.max_cooldown_seconds
        )
        
        self.in_cooldown = True
        self.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
        
        logger.warning(
            f"🚨 Order error detected (#{self.consecutive_errors}): {error_msg}\n"
            f"   Entering cooldown for {cooldown_seconds:.1f}s until {self.cooldown_until.strftime('%H:%M:%S')}"
        )
    
    def report_success(self):
        """
        Report successful order execution
        Resets error counter
        """
        if self.consecutive_errors > 0:
            logger.info(f"✅ Order successful! Resetting error counter (was {self.consecutive_errors})")
            self.consecutive_errors = 0
    
    def get_status(self) -> dict:
        """Get current rate limiter status"""
        now = datetime.now()
        orders_last_second = sum(1 for t in self.recent_orders if t > now - timedelta(seconds=1))
        
        return {
            'orders_last_second': orders_last_second,
            'total_recent_orders': len(self.recent_orders),
            'in_cooldown': self.in_cooldown,
            'cooldown_remaining': (self.cooldown_until - now).total_seconds() if self.cooldown_until and now < self.cooldown_until else 0,
            'consecutive_errors': self.consecutive_errors
        }


# Global rate limiter instance
_rate_limiter = OrderRateLimiter()


def get_rate_limiter() -> OrderRateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter
