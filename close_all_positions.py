"""
Emergency script to close ALL open positions immediately.
Use this when you need to flatten your book instantly.
"""

import asyncio
import logging
import sys
from src.execution.position_manager import PositionManager
from src.execution.order_manager import OrderManager
from src.data.models import PositionSide, OrderType, OrderSide

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("EmergencyClose")

async def close_all():
    """Close all open positions immediately"""
    logger.info("🚨 INITIATING EMERGENCY CLOSE OF ALL POSITIONS 🚨")
    
    position_manager = PositionManager()
    order_manager = OrderManager()
    
    # Get all open positions
    positions = position_manager.get_all_positions()
    
    if not positions:
        logger.info("✅ No open positions found. You are flat.")
        return

    logger.info(f"Found {len(positions)} open positions. Closing now...")
    
    tasks = []
    for pos in positions:
        logger.info(f"Closing {pos.pair_id} (Size: {pos.size_a} / {pos.size_b})...")
        
        # Close Leg A
        side_a = OrderSide.SELL if pos.side_a == PositionSide.LONG else OrderSide.BUY
        task_a = order_manager.client.place_order(
            symbol=pos.symbol_a,
            side=side_a,
            order_type=OrderType.MARKET,
            qty=str(pos.qty_a),  # Use stored quantity
            reduce_only=True
        )
        tasks.append(task_a)
        
        # Close Leg B
        side_b = OrderSide.SELL if pos.side_b == PositionSide.LONG else OrderSide.BUY
        task_b = order_manager.client.place_order(
            symbol=pos.symbol_b,
            side=side_b,
            order_type=OrderType.MARKET,
            qty=str(pos.qty_b),  # Use stored quantity
            reduce_only=True
        )
        tasks.append(task_b)
        
    # Execute all close orders in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check results
    success_count = 0
    for res in results:
        if isinstance(res, Exception):
            logger.error(f"❌ Failed to close position: {res}")
        else:
            success_count += 1
            
    logger.info(f"✅ Successfully sent {success_count}/{len(tasks)} close orders.")
    
    # Clear local memory
    position_manager.clear_all_history()
    logger.info("🧹 Local position history cleared.")

if __name__ == "__main__":
    asyncio.run(close_all())
