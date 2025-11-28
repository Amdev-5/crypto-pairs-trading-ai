"""Configuration management"""

import os
from typing import Any, Dict, List
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class BybitConfig(BaseModel):
    """Bybit API configuration"""
    api_key: str = Field(..., description="Bybit API key")
    api_secret: str = Field(..., description="Bybit API secret")
    testnet: bool = Field(default=True, description="Use testnet")


class GeminiConfig(BaseModel):
    """Google Gemini configuration"""
    api_key: str = Field(..., description="Gemini API key")
    model: str = Field(default="gemini-2.5-flash-preview-05-20")


class DatabaseConfig(BaseModel):
    """Database configuration"""
    url: str = Field(..., description="PostgreSQL connection URL")
    redis_url: str = Field(..., description="Redis connection URL")


class TradingConfig(BaseModel):
    """Trading parameters"""
    enabled: bool = Field(default=False)
    max_position_size: float = Field(default=1000.0)
    max_concurrent_pairs: int = Field(default=5)
    daily_loss_limit: float = Field(default=500.0)
    risk_per_trade: float = Field(default=0.02)


class ZScoreConfig(BaseModel):
    """Z-score thresholds"""
    entry_threshold: float = Field(default=2.0)
    exit_threshold: float = Field(default=0.5)
    stoploss_threshold: float = Field(default=3.0)


class CointegrationConfig(BaseModel):
    """Cointegration parameters"""
    window: int = Field(default=120, description="Window in minutes")
    pvalue_threshold: float = Field(default=0.05)
    hedge_ratio_update_interval: int = Field(default=240, description="Minutes")


class SentimentConfig(BaseModel):
    """Sentiment agent configuration"""
    update_interval: int = Field(default=900, description="Seconds")
    news_lookback_hours: int = Field(default=24)
    enable_google_search: bool = Field(default=True)


class Settings(BaseSettings):
    """Application settings"""

    # API keys
    bybit_api_key: str
    bybit_api_secret: str
    bybit_testnet: bool = True

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash-preview-05-20"

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/pairs_trading"
    redis_url: str = "redis://localhost:6379/0"

    # Trading
    trading_enabled: bool = True
    max_position_size: float = 1000.0
    max_concurrent_pairs: int = 15  # Increased for volume approach
    daily_loss_limit: float = 1000000.0  # Temporarily very high
    risk_per_trade: float = 0.01  # 1% risk per trade

    # Z-Score
    zscore_entry_threshold: float = 2.5  # Increased for quality
    zscore_exit_threshold: float = 0.3   # Decreased to capture profit
    zscore_stoploss_threshold: float = 4.0  # Increased for room

    # Cointegration
    cointegration_window: int = 120
    cointegration_pvalue_threshold: float = 0.05
    hedge_ratio_update_interval: int = 240

    # Sentiment
    sentiment_update_interval: int = 900
    news_lookback_hours: int = 24
    enable_google_search: bool = True

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/trading.log"

    # Monitoring
    enable_prometheus: bool = True
    prometheus_port: int = 9090

    class Config:
        env_file = ".env"
        case_sensitive = False


class ConfigManager:
    """Manages application configuration"""

    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.settings = Settings()
        self.yaml_config = self._load_yaml()

    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML configuration"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        return {}

    def get_trading_pairs(self) -> List[Dict[str, Any]]:
        """Get list of trading pairs"""
        return self.yaml_config.get('trading', {}).get('pairs', [])

    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy configuration"""
        return self.yaml_config.get('strategy', {})

    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for specific agent"""
        return self.yaml_config.get('agents', {}).get(agent_name, {})

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self.yaml_config.get('monitoring', {})

    @property
    def bybit(self) -> BybitConfig:
        """Get Bybit configuration"""
        return BybitConfig(
            api_key=self.settings.bybit_api_key,
            api_secret=self.settings.bybit_api_secret,
            testnet=self.settings.bybit_testnet
        )

    @property
    def gemini(self) -> GeminiConfig:
        """Get Gemini configuration"""
        return GeminiConfig(
            api_key=self.settings.gemini_api_key,
            model=self.settings.gemini_model
        )

    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration"""
        return DatabaseConfig(
            url=self.settings.database_url,
            redis_url=self.settings.redis_url
        )

    @property
    def trading(self) -> TradingConfig:
        """Get trading configuration"""
        return TradingConfig(
            enabled=self.settings.trading_enabled,
            max_position_size=self.settings.max_position_size,
            max_concurrent_pairs=self.settings.max_concurrent_pairs,
            daily_loss_limit=self.settings.daily_loss_limit,
            risk_per_trade=self.settings.risk_per_trade
        )

    @property
    def zscore(self) -> ZScoreConfig:
        """Get z-score configuration"""
        return ZScoreConfig(
            entry_threshold=self.settings.zscore_entry_threshold,
            exit_threshold=self.settings.zscore_exit_threshold,
            stoploss_threshold=self.settings.zscore_stoploss_threshold
        )

    @property
    def cointegration(self) -> CointegrationConfig:
        """Get cointegration configuration"""
        return CointegrationConfig(
            window=self.settings.cointegration_window,
            pvalue_threshold=self.settings.cointegration_pvalue_threshold,
            hedge_ratio_update_interval=self.settings.hedge_ratio_update_interval
        )

    @property
    def sentiment(self) -> SentimentConfig:
        """Get sentiment configuration"""
        return SentimentConfig(
            update_interval=self.settings.sentiment_update_interval,
            news_lookback_hours=self.settings.news_lookback_hours,
            enable_google_search=self.settings.enable_google_search
        )


# Global config instance
config = ConfigManager()
