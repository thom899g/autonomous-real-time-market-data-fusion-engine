"""
Configuration and environment management for Market Data Fusion Engine.
Centralizes all configurable parameters with validation.
"""
import os
import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from dotenv import load_dotenv
import structlog

load_dotenv()

logger = structlog.get_logger(__name__)

@dataclass
class ExchangeConfig:
    """Configuration for each exchange connection"""
    name: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    rate_limit: int = 1000
    enabled: bool = True

@dataclass
class MLConfig:
    """Machine Learning pipeline configuration"""
    model_update_interval: int = 3600  # seconds
    training_window_days: int = 90
    prediction_horizon_minutes: int = 60
    feature_lookback: int = 100  # candles
    anomaly_threshold: float = 2.5  # std deviations

@dataclass
class FirebaseConfig:
    """Firebase configuration with validation"""
    project_id: str
    private_key_id: str
    private_key: str
    client_email: str
    client_id: str
    
    @classmethod
    def from_env(cls):
        """Load Firebase config from environment variables with validation"""
        required_vars = [
            'FIREBASE_PROJECT_ID',
            'FIREBASE_PRIVATE_KEY_ID', 
            'FIREBASE_PRIVATE_KEY',
            'FIREBASE_CLIENT_EMAIL',
            'FIREBASE_CLIENT_ID'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing Firebase environment variables: {missing}")
        
        # Handle newline escape characters in private key
        private_key = os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n')
        
        return cls(
            project_id=os.getenv('FIREBASE_PROJECT_ID', ''),
            private_key_id=os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
            private_key=private_key,
            client_email=os.getenv('FIREBASE_CLIENT_EMAIL', ''),
            client_id=os.getenv('FIREBASE_CLIENT_ID', '')
        )

class MarketDataConfig:
    """Main configuration manager"""
    
    def __init__(self):
        self.exchanges: List[ExchangeConfig] = self._load_exchanges()
        self.symbols: List[str] = self._load_symbols()
        self.firebase: FirebaseConfig = FirebaseConfig.from_env()
        self.ml_config: MLConfig = MLConfig()
        
        # Real-time processing
        self.streaming_interval: int = int(os.getenv('STREAMING_INTERVAL', '60'))
        self.max_workers: int = int(os.getenv('MAX_WORKERS', '5'))
        self.batch_size: int = int(os.getenv('BATCH_SIZE', '100'))
        
        # Data retention
        self.data_retention_days: int = int(os.getenv('DATA_RETENTION_DAYS', '30'))
        
        logger.info("Configuration loaded", config_type="market_data")
    
    def _load_exchanges(self) -> List[ExchangeConfig]:
        """Load exchange configurations from environment"""
        exchanges = []
        exchange_names = ['binance', 'coinbase', 'kraken', 'bitstamp']
        
        for name in exchange_names:
            api_key_var = f"{name.upper()}_API_KEY"
            api_secret_var = f"{name.upper()}_API_SECRET"
            
            exchanges.append(ExchangeConfig(
                name=name,
                api_key=os.getenv(api_key_var),
                api_secret=os.getenv(api_secret_var),
                enabled=bool(os.getenv(f"{name.upper()}_ENABLED", "true").lower() == "true")
            ))
        
        return exchanges
    
    def _load_symbols(self) -> List[str]:
        """Load trading symbols from environment or default"""
        symbols_env = os.getenv('TRADING_SYMBOLS', 'BTC/USDT,ETH/USDT,BNB/USDT')
        return [s.strip() for s in symbols_env.split(',')]
    
    def validate(self) -> bool:
        """