# Pairs Trading Dashboard

Real-time monitoring dashboard for the cryptocurrency pairs trading system.

## Features

- Real-time position monitoring
- P&L tracking and visualization
- Trade history with detailed metrics
- Z-score and spread charts
- Risk metrics dashboard
- Live market data feed

## Setup

1. Install dependencies:
```bash
npm install
```

2. Configure API endpoint:
Edit `next.config.js` to point to your trading engine API (default: http://localhost:8000)

3. Run development server:
```bash
npm run dev
```

4. Open http://localhost:3000

## Production Build

```bash
npm run build
npm start
```

## Components

- `/app/page.tsx` - Main dashboard
- `/app/positions` - Position management
- `/app/trades` - Trade history
- `/app/analytics` - Performance analytics

## API Integration

The dashboard connects to the FastAPI server running on the trading engine.

Make sure the trading engine is running before starting the dashboard.
