-- Database schema for pairs trading system
-- PostgreSQL with TimescaleDB extension

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Price data table
CREATE TABLE IF NOT EXISTS price_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    UNIQUE(symbol, timestamp)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('price_data', 'timestamp', if_not_exists => TRUE);

-- Create index on symbol for faster queries
CREATE INDEX IF NOT EXISTS idx_price_data_symbol ON price_data(symbol, timestamp DESC);

-- Tick data table (for HFT)
CREATE TABLE IF NOT EXISTS tick_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    side VARCHAR(10) NOT NULL
);

SELECT create_hypertable('tick_data', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_tick_data_symbol ON tick_data(symbol, timestamp DESC);

-- Positions table
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    pair_id VARCHAR(50) NOT NULL,
    symbol_a VARCHAR(20) NOT NULL,
    symbol_b VARCHAR(20) NOT NULL,
    side_a VARCHAR(10) NOT NULL,
    side_b VARCHAR(10) NOT NULL,
    size_a DECIMAL(20, 8) NOT NULL,
    size_b DECIMAL(20, 8) NOT NULL,
    entry_price_a DECIMAL(20, 8) NOT NULL,
    entry_price_b DECIMAL(20, 8) NOT NULL,
    current_price_a DECIMAL(20, 8),
    current_price_b DECIMAL(20, 8),
    hedge_ratio DECIMAL(10, 6) NOT NULL,
    entry_zscore DECIMAL(10, 4) NOT NULL,
    current_zscore DECIMAL(10, 4),
    entry_time TIMESTAMPTZ NOT NULL,
    unrealized_pnl DECIMAL(20, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    UNIQUE(pair_id, entry_time)
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_pair ON positions(pair_id);

-- Trades table (closed positions)
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    pair_id VARCHAR(50) NOT NULL,
    symbol_a VARCHAR(20) NOT NULL,
    symbol_b VARCHAR(20) NOT NULL,
    side_a VARCHAR(10) NOT NULL,
    side_b VARCHAR(10) NOT NULL,
    size_a DECIMAL(20, 8) NOT NULL,
    size_b DECIMAL(20, 8) NOT NULL,
    entry_price_a DECIMAL(20, 8) NOT NULL,
    entry_price_b DECIMAL(20, 8) NOT NULL,
    exit_price_a DECIMAL(20, 8) NOT NULL,
    exit_price_b DECIMAL(20, 8) NOT NULL,
    hedge_ratio DECIMAL(10, 6) NOT NULL,
    entry_zscore DECIMAL(10, 4) NOT NULL,
    exit_zscore DECIMAL(10, 4) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ NOT NULL,
    duration_minutes DECIMAL(10, 2) NOT NULL,
    pnl DECIMAL(20, 2) NOT NULL,
    pnl_percent DECIMAL(10, 4) NOT NULL,
    commission DECIMAL(20, 2) NOT NULL,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_trades_pair ON trades(pair_id);
CREATE INDEX IF NOT EXISTS idx_trades_exit_time ON trades(exit_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_pnl ON trades(pnl);

-- Cointegration results table
CREATE TABLE IF NOT EXISTS cointegration_results (
    id SERIAL PRIMARY KEY,
    symbol_a VARCHAR(20) NOT NULL,
    symbol_b VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    is_cointegrated BOOLEAN NOT NULL,
    pvalue DECIMAL(10, 6) NOT NULL,
    test_statistic DECIMAL(10, 6) NOT NULL,
    hedge_ratio DECIMAL(10, 6) NOT NULL,
    r_squared DECIMAL(10, 6) NOT NULL,
    half_life DECIMAL(10, 2),
    UNIQUE(symbol_a, symbol_b, timestamp)
);

SELECT create_hypertable('cointegration_results', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_coint_pair ON cointegration_results(symbol_a, symbol_b, timestamp DESC);

-- Z-score data table
CREATE TABLE IF NOT EXISTS zscore_data (
    id SERIAL PRIMARY KEY,
    symbol_a VARCHAR(20) NOT NULL,
    symbol_b VARCHAR(20) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    spread DECIMAL(20, 8) NOT NULL,
    zscore DECIMAL(10, 4) NOT NULL,
    mean DECIMAL(20, 8) NOT NULL,
    std DECIMAL(20, 8) NOT NULL,
    UNIQUE(symbol_a, symbol_b, timestamp)
);

SELECT create_hypertable('zscore_data', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_zscore_pair ON zscore_data(symbol_a, symbol_b, timestamp DESC);

-- Signals table
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    pair_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    signal VARCHAR(20) NOT NULL,
    zscore DECIMAL(10, 4) NOT NULL,
    spread DECIMAL(20, 8) NOT NULL,
    hedge_ratio DECIMAL(10, 6) NOT NULL,
    confidence DECIMAL(5, 4) NOT NULL,
    sentiment_score DECIMAL(5, 4),
    reason TEXT,
    executed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_signals_pair ON signals(pair_id);

-- Sentiment data table
CREATE TABLE IF NOT EXISTS sentiment_data (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    sentiment_score DECIMAL(5, 4) NOT NULL,
    confidence DECIMAL(5, 4) NOT NULL,
    news_count INTEGER NOT NULL,
    major_events TEXT[],
    summary TEXT
);

SELECT create_hypertable('sentiment_data', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_sentiment_symbol ON sentiment_data(symbol, timestamp DESC);

-- Risk metrics table
CREATE TABLE IF NOT EXISTS risk_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    total_positions INTEGER NOT NULL,
    total_exposure DECIMAL(20, 2) NOT NULL,
    daily_pnl DECIMAL(20, 2) NOT NULL,
    daily_pnl_percent DECIMAL(10, 4) NOT NULL,
    unrealized_pnl DECIMAL(20, 2) NOT NULL,
    max_drawdown DECIMAL(10, 4) NOT NULL,
    sharpe_ratio DECIMAL(10, 4),
    win_rate DECIMAL(5, 4),
    average_latency_ms DECIMAL(10, 2)
);

SELECT create_hypertable('risk_metrics', 'timestamp', if_not_exists => TRUE);

-- System logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(20) NOT NULL,
    module VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(level);

-- Performance summary view
CREATE OR REPLACE VIEW performance_summary AS
SELECT
    DATE(exit_time) as trade_date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losing_trades,
    ROUND(CAST(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS DECIMAL) / COUNT(*), 4) as win_rate,
    ROUND(SUM(pnl), 2) as total_pnl,
    ROUND(AVG(pnl), 2) as avg_pnl,
    ROUND(MAX(pnl), 2) as best_trade,
    ROUND(MIN(pnl), 2) as worst_trade,
    ROUND(AVG(duration_minutes), 2) as avg_duration_minutes,
    ROUND(SUM(commission), 2) as total_commission
FROM trades
GROUP BY DATE(exit_time)
ORDER BY trade_date DESC;

-- Pair performance view
CREATE OR REPLACE VIEW pair_performance AS
SELECT
    pair_id,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
    ROUND(CAST(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS DECIMAL) / COUNT(*), 4) as win_rate,
    ROUND(SUM(pnl), 2) as total_pnl,
    ROUND(AVG(pnl), 2) as avg_pnl,
    ROUND(AVG(duration_minutes), 2) as avg_duration_minutes,
    ROUND(STDDEV(pnl), 2) as pnl_stddev
FROM trades
GROUP BY pair_id
ORDER BY total_pnl DESC;

-- Create retention policy for old data (optional)
-- Keeps 1 year of tick data, unlimited for other tables
SELECT add_retention_policy('tick_data', INTERVAL '365 days', if_not_exists => TRUE);

-- Continuous aggregates for performance (optional)
-- 1-hour OHLCV
CREATE MATERIALIZED VIEW IF NOT EXISTS price_data_1h
WITH (timescaledb.continuous) AS
SELECT
    symbol,
    time_bucket('1 hour', timestamp) AS bucket,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume
FROM price_data
GROUP BY symbol, bucket;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('price_data_1h',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- Insert sample data (for testing)
-- Uncomment to add test data
/*
INSERT INTO price_data (symbol, timestamp, open, high, low, close, volume) VALUES
    ('BTCUSDT', NOW() - INTERVAL '1 hour', 50000, 50100, 49900, 50050, 100),
    ('ETHUSDT', NOW() - INTERVAL '1 hour', 3000, 3010, 2990, 3005, 500);
*/

COMMENT ON TABLE price_data IS 'Historical OHLCV price data';
COMMENT ON TABLE tick_data IS 'Real-time tick-level price data';
COMMENT ON TABLE positions IS 'Currently open positions';
COMMENT ON TABLE trades IS 'Completed trades history';
COMMENT ON TABLE cointegration_results IS 'Cointegration test results over time';
COMMENT ON TABLE zscore_data IS 'Z-score calculations for pairs';
COMMENT ON TABLE signals IS 'Trading signals generated by the system';
COMMENT ON TABLE sentiment_data IS 'Sentiment analysis results from Gemini';
COMMENT ON TABLE risk_metrics IS 'Risk management metrics over time';
