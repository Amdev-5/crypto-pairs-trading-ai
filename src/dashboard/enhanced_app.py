"""Enhanced Production-Grade Multi-Strategy Dashboard"""

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from datetime import datetime
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Bybit Multi-Strategy Trading Dashboard")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
dashboard_state = {
    'strategies': {
        'correlation_rsi': {
            'name': 'Correlation + RSI',
            'status': 'ACTIVE',
            'trades': 1,
            'wins': 0,
            'pnl': -0.09,
            'win_rate': 0.0,
            'weight': 0.6,
            'current_signal': {'action': 'SHORT_SPREAD', 'pair': 'ETH/XRP', 'confidence': 0.55}
        },
        'mean_reversion': {
            'name': 'Mean Reversion',
            'status': 'ACTIVE',
            'trades': 0,
            'wins': 0,
            'pnl': 0.0,
            'win_rate': 0.0,
            'weight': 0.4,
            'current_signal': {'action': 'HOLD', 'pair': '', 'confidence': 0.0}
        }
    },
    'positions': [],
    'trades': [
        {
            'pair': 'ETH/XRP',
            'action': 'SHORT_SPREAD',
            'strategy': 'Correlation+RSI',
            'pnl': -0.09,
            'timestamp': '2025-11-27 15:08'
        }
    ],
    'balance': 84294.0,
    'total_pnl': -0.09,
    'last_update': datetime.now().isoformat()
}

# WebSocket connections
active_connections = []


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("WebSocket client connected")
    try:
        while True:
            # Send updates every second
            await websocket.send_json(dashboard_state)
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.get("/api/strategies")
async def get_strategies():
    """Get all strategy statuses and signals"""
    return dashboard_state['strategies']


@app.get("/api/performance")
async def get_performance():
    """Get performance metrics for all strategies"""
    return {
        'total_pnl': dashboard_state['total_pnl'],
        'balance': dashboard_state['balance'],
        'strategies': dashboard_state['strategies']
    }


@app.get("/api/positions")
async def get_positions():
    """Get current open positions"""
    return dashboard_state['positions']


@app.get("/api/trades")
async def get_trades():
    """Get recent trade history"""
    return dashboard_state['trades']


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve production-grade dashboard"""
    return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bybit Multi-Strategy Trading Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes pulse-signal {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
        .signal-active { animation: pulse-signal 2s infinite; }

        @keyframes slide-in {
            from { transform: translateY(-10px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .slide-in { animation: slide-in 0.3s ease-out; }
    </style>
</head>
<body class="bg-gray-900 text-white font-sans">
    <!-- Header -->
    <nav class="bg-gradient-to-r from-blue-900 to-purple-900 border-b border-gray-700 px-6 py-4 shadow-lg">
        <div class="flex justify-between items-center">
            <div class="flex items-center gap-3">
                <h1 class="text-3xl font-bold">🚀 Multi-Strategy Trading</h1>
                <span class="bg-green-500 text-white text-xs px-2 py-1 rounded-full animate-pulse">LIVE</span>
            </div>
            <div class="flex gap-4">
                <div class="bg-green-600 px-6 py-3 rounded-lg shadow">
                    <div class="text-xs text-green-200">Balance</div>
                    <div class="text-xl font-bold">$<span id="balance">84,294</span></div>
                </div>
                <div class="bg-blue-600 px-6 py-3 rounded-lg shadow">
                    <div class="text-xs text-blue-200">Total P&L</div>
                    <div class="text-xl font-bold" id="total-pnl">-$0.09</div>
                </div>
            </div>
        </div>
    </nav>

    <div class="container mx-auto px-6 py-6">
        <!-- Strategy Cards Grid -->
        <div class="mb-8">
            <h2 class="text-2xl font-bold mb-4">Active Strategies</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <!-- Strategy 1: Correlation + RSI -->
                <div class="bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg p-6 border-2 border-green-500 shadow-xl slide-in">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xl font-bold">Correlation + RSI</h3>
                        <span class="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-semibold">ACTIVE</span>
                    </div>
                    <div class="space-y-3">
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">Trades:</span>
                            <span class="font-bold text-lg" id="corr-trades">1</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">Win Rate:</span>
                            <span class="font-bold text-lg" id="corr-winrate">0%</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">P&L:</span>
                            <span class="font-bold text-lg text-red-400" id="corr-pnl">-$0.09</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">Weight:</span>
                            <span class="font-bold text-lg" id="corr-weight">60%</span>
                        </div>
                    </div>
                    <div class="mt-4 pt-4 border-t border-gray-700">
                        <div class="text-sm font-semibold mb-2 text-gray-300">Current Signal:</div>
                        <div class="bg-yellow-600 text-white px-4 py-3 rounded-lg signal-active text-center font-bold">
                            SHORT ETH/XRP (55%)
                        </div>
                    </div>
                </div>

                <!-- Strategy 2: Mean Reversion -->
                <div class="bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg p-6 border-2 border-blue-500 shadow-xl slide-in" style="animation-delay: 0.1s;">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xl font-bold">Mean Reversion</h3>
                        <span class="bg-blue-500 text-white px-3 py-1 rounded-full text-sm font-semibold">ACTIVE</span>
                    </div>
                    <div class="space-y-3">
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">Trades:</span>
                            <span class="font-bold text-lg" id="mr-trades">0</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">Win Rate:</span>
                            <span class="font-bold text-lg" id="mr-winrate">0%</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">P&L:</span>
                            <span class="font-bold text-lg" id="mr-pnl">$0.00</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">Weight:</span>
                            <span class="font-bold text-lg" id="mr-weight">40%</span>
                        </div>
                    </div>
                    <div class="mt-4 pt-4 border-t border-gray-700">
                        <div class="text-sm font-semibold mb-2 text-gray-300">Current Signal:</div>
                        <div class="bg-gray-600 text-white px-4 py-3 rounded-lg text-center font-bold">
                            HOLD (Waiting)
                        </div>
                    </div>
                </div>

                <!-- Strategy 3: Coming Soon -->
                <div class="bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg p-6 border-2 border-purple-500 shadow-xl opacity-50 slide-in" style="animation-delay: 0.2s;">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xl font-bold">Momentum Divergence</h3>
                        <span class="bg-gray-500 text-white px-3 py-1 rounded-full text-sm font-semibold">COMING SOON</span>
                    </div>
                    <div class="space-y-3">
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">Trades:</span>
                            <span class="font-bold text-lg">-</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">Win Rate:</span>
                            <span class="font-bold text-lg">-</span>
                        </div>
                        <div class="flex justify-between items-center">
                            <span class="text-gray-400">P&L:</span>
                            <span class="font-bold text-lg">-</span>
                        </div>
                    </div>
                    <div class="mt-4 pt-4 border-t border-gray-700">
                        <div class="text-sm font-semibold mb-2 text-gray-300">Status:</div>
                        <div class="bg-gray-700 text-gray-400 px-4 py-3 rounded-lg text-center">
                            In Development
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Positions Table -->
        <div class="bg-gray-800 rounded-lg p-6 mb-8 shadow-xl">
            <h2 class="text-2xl font-bold mb-4">Open Positions</h2>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="border-b border-gray-700">
                        <tr class="text-gray-400">
                            <th class="pb-3 font-semibold">Pair</th>
                            <th class="pb-3 font-semibold">Side</th>
                            <th class="pb-3 font-semibold">Size</th>
                            <th class="pb-3 font-semibold">Entry</th>
                            <th class="pb-3 font-semibold">Current</th>
                            <th class="pb-3 font-semibold">P&L</th>
                            <th class="pb-3 font-semibold">Strategy</th>
                        </tr>
                    </thead>
                    <tbody id="positions-table">
                        <tr><td colspan="7" class="py-8 text-center text-gray-500 text-lg">No open positions</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Trade History -->
        <div class="bg-gray-800 rounded-lg p-6 shadow-xl">
            <h2 class="text-2xl font-bold mb-4">Recent Trades</h2>
            <div class="space-y-3" id="trades-list">
                <div class="bg-gradient-to-r from-gray-700 to-gray-800 p-5 rounded-lg flex justify-between items-center hover:from-gray-600 hover:to-gray-700 transition-all">
                    <div>
                        <div class="font-bold text-lg">ETH/XRP - SHORT SPREAD</div>
                        <div class="text-sm text-gray-400 mt-1">Correlation+RSI Strategy</div>
                    </div>
                    <div class="text-right">
                        <div class="text-red-400 font-bold text-lg">-$0.09</div>
                        <div class="text-sm text-gray-400 mt-1">2025-11-27 15:08</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // WebSocket connection
        let ws = null;

        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:5001/ws');

            ws.onopen = function() {
                console.log('WebSocket connected');
            };

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };

            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };

            ws.onclose = function() {
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
        }

        function updateDashboard(data) {
            // Update balance
            if (data.balance !== undefined) {
                document.getElementById('balance').textContent = data.balance.toLocaleString('en-US', {minimumFractionDigits: 0});
            }

            // Update total P&L
            if (data.total_pnl !== undefined) {
                const pnlElem = document.getElementById('total-pnl');
                const sign = data.total_pnl >= 0 ? '+' : '';
                pnlElem.textContent = sign + '$' + data.total_pnl.toFixed(2);
                pnlElem.className = 'text-xl font-bold ' + (data.total_pnl >= 0 ? 'text-green-400' : 'text-red-400');
            }

            // Update strategy cards
            if (data.strategies) {
                // Correlation+RSI
                if (data.strategies.correlation_rsi) {
                    const strat = data.strategies.correlation_rsi;
                    document.getElementById('corr-trades').textContent = strat.trades;
                    document.getElementById('corr-winrate').textContent = (strat.win_rate * 100).toFixed(1) + '%';

                    const corrPnlElem = document.getElementById('corr-pnl');
                    const sign = strat.pnl >= 0 ? '+' : '';
                    corrPnlElem.textContent = sign + '$' + strat.pnl.toFixed(2);
                    corrPnlElem.className = 'font-bold text-lg ' + (strat.pnl >= 0 ? 'text-green-400' : 'text-red-400');

                    document.getElementById('corr-weight').textContent = (strat.weight * 100).toFixed(0) + '%';
                }

                // Mean Reversion
                if (data.strategies.mean_reversion) {
                    const strat = data.strategies.mean_reversion;
                    document.getElementById('mr-trades').textContent = strat.trades;
                    document.getElementById('mr-winrate').textContent = (strat.win_rate * 100).toFixed(1) + '%';

                    const mrPnlElem = document.getElementById('mr-pnl');
                    const sign = strat.pnl >= 0 ? '+' : '';
                    mrPnlElem.textContent = sign + '$' + strat.pnl.toFixed(2);
                    mrPnlElem.className = 'font-bold text-lg ' + (strat.pnl >= 0 ? 'text-green-400' : 'text-gray-400');

                    document.getElementById('mr-weight').textContent = (strat.weight * 100).toFixed(0) + '%';
                }
            }
        }

        // Initial connection
        connectWebSocket();

        // Also poll REST API as backup
        setInterval(() => {
            fetch('/api/performance')
                .then(r => r.json())
                .then(updateDashboard)
                .catch(e => console.error('Failed to fetch performance:', e));
        }, 5000);
    </script>
</body>
</html>
    '''


def update_dashboard_data(
    strategies: dict = None,
    positions: list = None,
    trades: list = None,
    balance: float = None,
    total_pnl: float = None
):
    """Update dashboard state (called from trading engine)"""
    global dashboard_state

    if strategies:
        dashboard_state['strategies'] = strategies
    if positions is not None:
        dashboard_state['positions'] = positions
    if trades is not None:
        dashboard_state['trades'] = trades
    if balance is not None:
        dashboard_state['balance'] = balance
    if total_pnl is not None:
        dashboard_state['total_pnl'] = total_pnl

    dashboard_state['last_update'] = datetime.now().isoformat()

    # Notify all connected WebSocket clients
    for connection in active_connections:
        try:
            asyncio.create_task(connection.send_json(dashboard_state))
        except Exception as e:
            logger.error(f"Failed to send update to WebSocket client: {e}")


if __name__ == "__main__":
    import uvicorn
    print("Starting Enhanced Multi-Strategy Dashboard on http://localhost:5001")
    uvicorn.run(app, host="0.0.0.0", port=5001)
