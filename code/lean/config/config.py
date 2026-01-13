"""
Configuration Management for Abacus.AI LEAN Integration
Centralized configuration for all components
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class AbacusAIConfig:
    """Complete configuration for Abacus.AI LEAN integration"""
    
    # API Configuration
    api_base_url: str = "https://api.abacus.ai"
    api_timeout: int = 30
    api_rate_limit: int = 100  # requests per minute
    api_key: str = ""  # Set via environment variable
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_timeout: int = 5
    redis_connection_pool_size: int = 10
    
    # Algorithm Configuration
    symbols: List[str] = field(default_factory=lambda: ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'])
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 100000.0
    cash: float = 100000.0
    
    # Trading Parameters
    lookback_days: int = 30
    min_confidence: float = 0.6
    max_position_size: float = 0.25
    rebalance_frequency: int = 1
    position_hold_days: int = 5
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.15
    volatility_threshold: float = 0.3
    sentiment_filter: float = -0.5
    
    # Risk Management
    max_daily_loss: float = 0.02  # 2%
    max_portfolio_risk: float = 0.1  # 10%
    max_drawdown: float = 0.15  # 15%
    max_position_pct: float = 0.05  # 5%
    max_daily_trades: int = 10
    min_order_value: float = 100.0
    
    # Cache Configuration
    cache_default_ttl: int = 3600  # 1 hour
    cache_max_size: int = 100
    cache_auto_cleanup: bool = True
    cache_cleanup_interval: int = 86400  # 24 hours
    cache_enable_compression: bool = False
    cache_enable_stats: bool = True
    
    # Feature Flags
    enable_live_trading: bool = False
    enable_redis: bool = False
    enable_caching: bool = True
    enable_backtesting: bool = True
    enable_real_time_updates: bool = False
    enable_monitoring: bool = True
    enable_alerts: bool = True
    
    # Performance Settings
    update_frequency: int = 60  # seconds
    max_concurrent_predictions: int = 5
    timeout_predictions: int = 30
    retry_attempts: int = 3
    
    # Data Sources
    primary_data_source: str = "lean"  # lean, redis, api
    fallback_data_sources: List[str] = field(default_factory=lambda: ["redis", "api"])
    
    # Monitoring and Alerts
    alert_email: str = ""
    alert_webhook: str = ""
    metrics_retention_days: int = 30
    health_check_interval: int = 300  # 5 minutes
    
    # Backtesting Configuration
    benchmark_symbol: str = "SPY"
    benchmark_enabled: bool = True
    transaction_costs: float = 0.001  # 0.1%
    slippage: float = 0.0005  # 0.05%
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.__dict__
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AbacusAIConfig':
        """Create configuration from dictionary"""
        return cls(**config_dict)
    
    def update(self, updates: Dict[str, Any]) -> 'AbacusAIConfig':
        """Update configuration with new values"""
        updated_dict = self.to_dict()
        updated_dict.update(updates)
        return self.from_dict(updated_dict)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate required fields
        if self.initial_capital <= 0:
            errors.append("initial_capital must be positive")
        
        if self.min_confidence < 0 or self.min_confidence > 1:
            errors.append("min_confidence must be between 0 and 1")
        
        if self.max_position_size <= 0 or self.max_position_size > 1:
            errors.append("max_position_size must be between 0 and 1")
        
        if len(self.symbols) == 0:
            errors.append("symbols list cannot be empty")
        
        # Validate trading parameters
        if self.stop_loss_pct < 0 or self.stop_loss_pct > 1:
            errors.append("stop_loss_pct must be between 0 and 1")
        
        if self.take_profit_pct < 0 or self.take_profit_pct > 1:
            errors.append("take_profit_pct must be between 0 and 1")
        
        # Validate dates
        try:
            from datetime import datetime
            datetime.strptime(self.start_date, '%Y-%m-%d')
            datetime.strptime(self.end_date, '%Y-%m-%d')
        except ValueError:
            errors.append("start_date and end_date must be in YYYY-MM-DD format")
        
        return errors


# Predefined configurations for different environments
ENVIRONMENTS = {
    'development': AbacusAIConfig(
        enable_live_trading=False,
        enable_redis=False,
        symbols=['AAPL', 'GOOGL'],
        initial_capital=10000,
        cache_max_size=50,
        update_frequency=30
    ),
    
    'testing': AbacusAIConfig(
        enable_live_trading=False,
        enable_redis=True,
        enable_backtesting=True,
        symbols=['AAPL', 'GOOGL', 'MSFT'],
        initial_capital=50000,
        min_confidence=0.5,
        cache_max_size=25,
        rebalance_frequency=7
    ),
    
    'staging': AbacusAIConfig(
        enable_live_trading=False,
        enable_redis=True,
        enable_real_time_updates=True,
        symbols=['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'],
        initial_capital=100000,
        min_confidence=0.6,
        cache_max_size=100,
        rebalance_frequency=3,
        enable_monitoring=True,
        enable_alerts=True
    ),
    
    'production': AbacusAIConfig(
        enable_live_trading=True,
        enable_redis=True,
        enable_real_time_updates=True,
        enable_monitoring=True,
        enable_alerts=True,
        symbols=['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META'],
        initial_capital=1000000,
        min_confidence=0.7,
        max_position_size=0.2,
        cache_max_size=500,
        rebalance_frequency=1,
        max_daily_trades=20,
        alert_email="trading@example.com",
        health_check_interval=60
    )
}


def get_config(environment: str = 'development', overrides: Dict[str, Any] = None) -> AbacusAIConfig:
    """
    Get configuration for specified environment
    
    Args:
        environment: Environment name (development, testing, staging, production)
        overrides: Configuration overrides
        
    Returns:
        AbacusAIConfig instance
    """
    if environment not in ENVIRONMENTS:
        environment = 'development'
    
    config = ENVIRONMENTS[environment]
    
    if overrides:
        config = config.update(overrides)
    
    # Validate configuration
    errors = config.validate()
    if errors:
        raise ValueError(f"Configuration validation failed: {errors}")
    
    return config


def create_custom_config(symbols: List[str], 
                        initial_capital: float = 100000,
                        enable_live_trading: bool = False,
                        **kwargs) -> AbacusAIConfig:
    """
    Create custom configuration
    
    Args:
        symbols: List of symbols to trade
        initial_capital: Starting capital
        enable_live_trading: Enable live trading
        **kwargs: Additional configuration parameters
        
    Returns:
        AbacusAIConfig instance
    """
    base_config = {
        'symbols': symbols,
        'initial_capital': initial_capital,
        'cash': initial_capital,
        'enable_live_trading': enable_live_trading,
        **kwargs
    }
    
    return AbacusAIConfig.from_dict(base_config)


# Trading strategy configurations
STRATEGY_CONFIGS = {
    'conservative': AbacusAIConfig(
        min_confidence=0.8,
        max_position_size=0.1,
        max_daily_trades=3,
        rebalance_frequency=7,
        sentiment_filter=0.0  # Only trade on positive sentiment
    ),
    
    'moderate': AbacusAIConfig(
        min_confidence=0.6,
        max_position_size=0.2,
        max_daily_trades=5,
        rebalance_frequency=3,
        sentiment_filter=-0.3
    ),
    
    'aggressive': AbacusAIConfig(
        min_confidence=0.5,
        max_position_size=0.3,
        max_daily_trades=10,
        rebalance_frequency=1,
        sentiment_filter=-0.7  # Allow trading on negative sentiment
    )
}


def get_strategy_config(strategy_name: str, **overrides) -> AbacusAIConfig:
    """
    Get configuration for specific trading strategy
    
    Args:
        strategy_name: Strategy name (conservative, moderate, aggressive)
        **overrides: Configuration overrides
        
    Returns:
        AbacusAIConfig instance
    """
    if strategy_name not in STRATEGY_CONFIGS:
        strategy_name = 'moderate'
    
    config = STRATEGY_CONFIGS[strategy_name]
    
    if overrides:
        config = config.update(overrides)
    
    return config