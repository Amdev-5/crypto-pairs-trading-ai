"""Real-time trading dashboard"""

import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import json
from datetime import datetime
from pathlib import Path

app = FastAPI()

# Global state to share data between trading engine and dashboard
dashboard_data = {
    "pairs": {},
    "account_balance": 0.0,
    "available_balance": 0.0,
    "total_pnl": 0.0,
    "daily_pnl": 0.0,
    "win_rate": 0.0,
    "total_trades": 0,
    "positions": [],
    "max_position_size": 1000.0,  # From .env
    "risk_per_trade": 0.02,  # 2% from .env
    "last_update": datetime.now().isoformat()
}

@app.get("/")
async def get_dashboard():
    """Serve the dashboard HTML"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Crypto Pairs Trading Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #0a0e27;
                color: #fff;
                padding: 20px;
            }

            .header {
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 10px;
            }

            h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }

            .balance {
                font-size: 1.5em;
                color: #4ade80;
                margin-bottom: 20px;
            }

            .stats-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }

            .stat-box {
                background: rgba(255, 255, 255, 0.1);
                padding: 10px;
                border-radius: 8px;
                text-align: center;
            }

            .stat-box .stat-label {
                font-size: 0.85em;
                color: #94a3b8;
                margin-bottom: 5px;
            }

            .stat-box .stat-value {
                font-size: 1.2em;
                font-weight: bold;
                color: #fff;
            }

            .pairs-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }

            .pair-card {
                background: #1e293b;
                border-radius: 10px;
                padding: 20px;
                border: 2px solid #334155;
                transition: all 0.3s;
            }

            .pair-card:hover {
                border-color: #667eea;
                transform: translateY(-5px);
            }

            .pair-header {
                font-size: 1.5em;
                font-weight: bold;
                margin-bottom: 15px;
                color: #60a5fa;
            }

            .stat {
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #334155;
            }

            .stat:last-child {
                border-bottom: none;
            }

            .stat-label {
                color: #94a3b8;
            }

            .stat-value {
                font-weight: bold;
            }

            .positive {
                color: #4ade80;
            }

            .negative {
                color: #f87171;
            }

            .neutral {
                color: #fbbf24;
            }

            .cointegrated {
                background: #065f46;
                color: #4ade80;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85em;
            }

            .not-cointegrated {
                background: #7f1d1d;
                color: #f87171;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85em;
            }

            .last-update {
                text-align: center;
                color: #64748b;
                margin-top: 20px;
            }

            .zscore-bar {
                width: 100%;
                height: 30px;
                background: #0f172a;
                border-radius: 5px;
                position: relative;
                margin-top: 10px;
                overflow: hidden;
            }

            .zscore-fill {
                height: 100%;
                background: linear-gradient(90deg, #f87171, #fbbf24, #4ade80);
                transition: width 0.3s;
            }

            .zscore-marker {
                position: absolute;
                top: 0;
                height: 100%;
                width: 3px;
                background: white;
            }

            .signal {
                display: inline-block;
                padding: 6px 16px;
                border-radius: 20px;
                font-weight: bold;
                margin-top: 10px;
            }

            .signal.long {
                background: #065f46;
                color: #4ade80;
            }

            .signal.short {
                background: #7f1d1d;
                color: #f87171;
            }

            .signal.hold {
                background: #422006;
                color: #fbbf24;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 Crypto Pairs Trading Dashboard</h1>
            <div class="balance">Total Balance: $<span id="balance">0.00</span></div>
            <div class="stats-row">
                <div class="stat-box">
                    <div class="stat-label">Available</div>
                    <div class="stat-value">$<span id="available">0.00</span></div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total P&L</div>
                    <div class="stat-value" id="total-pnl">$0.00</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Daily P&L</div>
                    <div class="stat-value" id="daily-pnl">$0.00</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Win Rate</div>
                    <div class="stat-value"><span id="win-rate">0</span>%</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Total Trades</div>
                    <div class="stat-value" id="total-trades">0</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Max Position</div>
                    <div class="stat-value">$<span id="max-position">1000</span></div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Risk/Trade</div>
                    <div class="stat-value"><span id="risk-per-trade">2</span>%</div>
                </div>
            </div>
            <div style="margin-top: 10px; color: #cbd5e1;">
                Mode: <span id="mode">PURE QUANT (Testnet)</span>
            </div>
        </div>

        <div class="pairs-grid" id="pairs-container">
            <!-- Pairs will be inserted here -->
        </div>

        <div class="last-update">
            Last Update: <span id="last-update">--</span>
        </div>

        <script>
            const ws = new WebSocket('ws://localhost:5000/ws');

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };

            function updateDashboard(data) {
                // Update balance and financial stats
                document.getElementById('balance').textContent = data.account_balance.toFixed(2);
                document.getElementById('available').textContent = (data.available_balance || data.account_balance).toFixed(2);

                // Update P&L with color coding
                const totalPnl = data.total_pnl || 0;
                const dailyPnl = data.daily_pnl || 0;
                const totalPnlEl = document.getElementById('total-pnl');
                const dailyPnlEl = document.getElementById('daily-pnl');

                totalPnlEl.textContent = `$${totalPnl.toFixed(2)}`;
                totalPnlEl.className = totalPnl >= 0 ? 'stat-value positive' : 'stat-value negative';

                dailyPnlEl.textContent = `$${dailyPnl.toFixed(2)}`;
                dailyPnlEl.className = dailyPnl >= 0 ? 'stat-value positive' : 'stat-value negative';

                // Update win rate and trades
                document.getElementById('win-rate').textContent = ((data.win_rate || 0) * 100).toFixed(1);
                document.getElementById('total-trades').textContent = data.total_trades || 0;

                // Update risk parameters
                document.getElementById('max-position').textContent = (data.max_position_size || 1000).toFixed(0);
                document.getElementById('risk-per-trade').textContent = ((data.risk_per_trade || 0.02) * 100).toFixed(0);

                // Update last update time
                const now = new Date();
                document.getElementById('last-update').textContent = now.toLocaleTimeString();

                // Update pairs
                const container = document.getElementById('pairs-container');
                container.innerHTML = '';

                for (const [pairId, pairData] of Object.entries(data.pairs)) {
                    const card = createPairCard(pairId, pairData);
                    container.innerHTML += card;
                }
            }

            function createPairCard(pairId, data) {
                const zscore = data.zscore || 0;
                const pvalue = data.cointegration?.pvalue || 1.0;
                const isCointegrated = pvalue < 0.2;
                const hedgeRatio = data.cointegration?.hedge_ratio || 1.0;
                const halfLife = data.cointegration?.half_life || 'N/A';
                const signal = data.signal || 'HOLD';
                const confidence = data.confidence || 0;
                const positionSizeA = data.position_size_a || 0;
                const positionSizeB = data.position_size_b || 0;
                const currentPriceA = data.current_price_a || 0;
                const currentPriceB = data.current_price_b || 0;

                const zscorePercent = Math.min(Math.abs(zscore) / 3 * 100, 100);
                const zscoreColor = Math.abs(zscore) > 1.5 ? 'positive' : Math.abs(zscore) > 0.5 ? 'neutral' : '';

                // Calculate lot sizes (contracts)
                const lotSizeA = currentPriceA > 0 ? (positionSizeA / currentPriceA).toFixed(4) : '0.0000';
                const lotSizeB = currentPriceB > 0 ? (positionSizeB / currentPriceB).toFixed(4) : '0.0000';

                return `
                    <div class="pair-card">
                        <div class="pair-header">${pairId}</div>

                        <div class="stat">
                            <span class="stat-label">Current Prices:</span>
                            <span class="stat-value">${currentPriceA.toFixed(2)} / ${currentPriceB.toFixed(2)}</span>
                        </div>

                        <div class="stat">
                            <span class="stat-label">Z-Score:</span>
                            <span class="stat-value ${zscoreColor}">${zscore.toFixed(3)}</span>
                        </div>

                        <div class="zscore-bar">
                            <div class="zscore-fill" style="width: ${zscorePercent}%"></div>
                            <div class="zscore-marker" style="left: 50%"></div>
                        </div>

                        <div class="stat">
                            <span class="stat-label">Cointegration:</span>
                            <span class="${isCointegrated ? 'cointegrated' : 'not-cointegrated'}">
                                ${isCointegrated ? '✓ Yes' : '✗ No'}
                            </span>
                        </div>

                        <div class="stat">
                            <span class="stat-label">P-Value:</span>
                            <span class="stat-value">${pvalue.toFixed(4)}</span>
                        </div>

                        <div class="stat">
                            <span class="stat-label">Hedge Ratio:</span>
                            <span class="stat-value">${hedgeRatio.toFixed(4)}</span>
                        </div>

                        <div class="stat">
                            <span class="stat-label">Half-Life:</span>
                            <span class="stat-value">${halfLife !== 'N/A' ? halfLife.toFixed(2) + ' min' : 'N/A'}</span>
                        </div>

                        <div class="stat">
                            <span class="stat-label">Position Size (USD):</span>
                            <span class="stat-value">$${positionSizeA.toFixed(2)} / $${positionSizeB.toFixed(2)}</span>
                        </div>

                        <div class="stat">
                            <span class="stat-label">Lot Size (Contracts):</span>
                            <span class="stat-value">${lotSizeA} / ${lotSizeB}</span>
                        </div>

                        <div class="stat">
                            <span class="stat-label">Signal:</span>
                            <span class="signal ${signal.toLowerCase()}">${signal}</span>
                        </div>

                        <div class="stat">
                            <span class="stat-label">Confidence:</span>
                            <span class="stat-value">${(confidence * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                `;
            }

            // Request updates every 2 seconds
            setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                }
            }, 2000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    try:
        while True:
            # Wait for ping from client
            await websocket.receive_text()

            # Load latest data from file
            _load_dashboard_data()

            # Send current data
            await websocket.send_text(json.dumps(dashboard_data))
    except Exception as e:
        print(f"WebSocket error: {e}")

def update_dashboard(pair_id: str, data: dict):
    """Update dashboard data from trading engine"""
    dashboard_data["pairs"][pair_id] = data
    dashboard_data["last_update"] = datetime.now().isoformat()
    _save_dashboard_data()

def update_balance(balance: float):
    """Update account balance"""
    dashboard_data["account_balance"] = balance
    dashboard_data["available_balance"] = balance
    _save_dashboard_data()

def update_stats(stats: dict):
    """Update trading statistics"""
    dashboard_data["total_pnl"] = stats.get("total_pnl", 0.0)
    dashboard_data["daily_pnl"] = stats.get("daily_pnl", 0.0)
    dashboard_data["win_rate"] = stats.get("win_rate", 0.0)
    dashboard_data["total_trades"] = stats.get("total_trades", 0)
    dashboard_data["available_balance"] = stats.get("available_balance", dashboard_data["account_balance"])
    dashboard_data["last_update"] = datetime.now().isoformat()
    _save_dashboard_data()

def _save_dashboard_data():
    """Save dashboard data to file"""
    try:
        data_file = Path("/tmp/bybit_dashboard_data.json")
        with open(data_file, 'w') as f:
            json.dump(dashboard_data, f)
    except Exception as e:
        print(f"Error saving dashboard data: {e}")

def _load_dashboard_data():
    """Load dashboard data from file"""
    try:
        data_file = Path("/tmp/bybit_dashboard_data.json")
        if data_file.exists():
            with open(data_file, 'r') as f:
                loaded_data = json.load(f)
                dashboard_data.update(loaded_data)
    except Exception as e:
        print(f"Error loading dashboard data: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
