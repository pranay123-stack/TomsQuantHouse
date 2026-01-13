# Abacus.AI QuantConnect LEAN Integration

A comprehensive integration system for ingesting Abacus.AI machine learning predictions into QuantConnect LEAN trading algorithms with real-time capabilities, caching, backtesting, and live trading support.

## 🚀 Features

- **PythonData Integration**: Custom data source for Abacus.AI ML predictions
- **Real-time Communication**: Redis-based streaming of prediction updates
- **Smart Caching**: ObjectStore caching to reduce API calls and improve performance
- **Backtesting Framework**: Historical simulation with prediction data
- **Live Trading Engine**: Production-ready trading with risk management
- **Configuration Management**: Environment-based configuration system
- **Error Handling**: Robust error handling and recovery mechanisms
- **Performance Monitoring**: Comprehensive metrics and monitoring

## 📁 Directory Structure

```
code/lean/
├── algorithms/
│   ├── main.py              # Main algorithm template
│   └── live_trading.py      # Live trading engine
├── config/
│   ├── config.py           # Configuration management
│   ├── redis_manager.py    # Redis communication
│   └── prediction_cache.py # ObjectStore caching
├── data/
│   └── abacus_ai_predictions.py  # PythonData class
├── research/
│   └── backtesting_framework.py  # Backtesting system
└── example_complete.py      # Complete demonstration
```

## 🛠 Installation & Setup

### 1. Prerequisites

```bash
# Install required dependencies
pip install redis pandas numpy matplotlib seaborn

# Install QuantConnect LEAN CLI (if not already installed)
pip install lean-cli

# Start Redis server (for real-time data)
redis-server
```

### 2. Configuration

Edit `config/config.py` to set up your environment:

```python
from config.config import get_config

# Development environment
config = get_config('development', {
    'symbols': ['AAPL', 'GOOGL'],
    'initial_capital': 10000,
    'enable_live_trading': False
})
```

### 3. Abacus.AI API Setup

Set your Abacus.AI API credentials:

```python
# In your environment variables or config
config.api_key = "your_abacus_ai_api_key"
config.api_base_url = "https://api.abacus.ai"
```

## 🎯 Quick Start

### Basic Algorithm

```python
from algorithms.main import AbacusAILeanAlgorithm

# Create and initialize algorithm
algorithm = AbacusAILeanAlgorithm()
algorithm.Initialize()

# The algorithm will automatically:
# - Load Abacus.AI predictions
# - Execute trades based on ML signals
# - Apply risk management
# - Track performance
```

### Custom Configuration

```python
from config.config import get_strategy_config
from algorithms.main import AbacusAILeanAlgorithm

class CustomAbacusAI(AbacusAILeanAlgorithm):
    def Initialize(self):
        # Use conservative strategy
        config = get_strategy_config('conservative', {
            'symbols': ['AAPL', 'TSLA'],
            'initial_capital': 50000
        })
        
        # Apply configuration
        self.SetCash(config.initial_capital)
        # ... rest of initialization
```

## 📊 Backtesting

### Basic Backtest

```python
from research.backtesting_framework import run_abacus_backtest

# Run quick backtest
results = run_abacus_backtest(
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 3, 31),
    initial_capital=50000
)

print(f"Total Return: {results.total_return:.2%}")
print(f"Sharpe Ratio: {results.sharpe_ratio:.3f}")
```

### Advanced Backtesting

```python
from research.backtesting_framework import AbacusAIBacktestFramework

# Create backtester
backtester = AbacusAIBacktestFramework(['AAPL', 'GOOGL'], 100000)

# Load historical data
backtester.load_historical_predictions(start_date, end_date)

# Configure strategy
strategy_config = {
    'min_confidence': 0.7,
    'max_position_size': 0.2,
    'rebalance_frequency': 3,
    'stop_loss_pct': 0.05,
    'take_profit_pct': 0.15
}

# Run backtest
results = backtester.run_backtest(strategy_config)

# Generate report
report = backtester.generate_report()
print(report)

# Plot results
backtester.plot_results('backtest_results.png')
```

## 🔄 Real-time Trading

### Redis Integration

```python
from config.redis_manager import get_redis_manager

# Initialize Redis manager
redis_manager = get_redis_manager(
    host='localhost',
    port=6379
)

# Subscribe to predictions
def handle_prediction(prediction):
    print(f"New prediction: {prediction.symbol} - {prediction.direction}")
    # Trigger trading logic

redis_manager.subscribe_to_predictions(['AAPL', 'GOOGL'], handle_prediction)
```

### Live Trading Engine

```python
from algorithms.live_trading import get_trading_engine

# Initialize trading engine
trading_engine = get_trading_engine(
    algorithm=self,
    symbols=['AAPL', 'GOOGL'],
    config={
        'enable_redis': True,
        'max_position_pct': 0.05,
        'min_confidence': 0.7
    }
)

# Start trading
success = trading_engine.start_trading()
if success:
    print("Live trading started")
```

## 💾 Caching System

### Smart Caching

```python
from config.prediction_cache import get_prediction_cache

# Initialize cache
cache = get_prediction_cache(algorithm, {
    'default_ttl': 3600,  # 1 hour
    'max_cache_size': 100
})

# Get cached prediction
prediction = cache.get(
    'AAPL_prediction_20240101',
    fallback_func=abacus_api.get_prediction,
    symbol='AAPL',
    date=datetime.now()
)

# Cache statistics
stats = cache.get_cache_stats()
print(f"Hit Rate: {stats['hit_rate']:.2%}")
```

## ⚙️ Configuration Options

### Environment Configurations

```python
from config.config import get_config

# Development
dev_config = get_config('development')

# Testing
test_config = get_config('testing')

# Production
prod_config = get_config('production', {
    'enable_live_trading': True,
    'initial_capital': 1000000,
    'alert_email': 'trading@company.com'
})
```

### Strategy Configurations

```python
from config.config import get_strategy_config

# Conservative strategy
conservative = get_strategy_config('conservative')

# Aggressive strategy  
aggressive = get_strategy_config('aggressive', {
    'max_position_size': 0.3,
    'max_daily_trades': 20
})
```

## 🔧 Advanced Usage

### Custom Data Source

```python
from data.abacus_ai_predictions import AbacusAIPredictionsData

class CustomAbacusData(AbacusAIPredictionsData):
    def _fetch_abacus_predictions(self, symbol, date):
        # Custom prediction fetching logic
        # Connect to your specific Abacus.AI endpoint
        return prediction_data
```

### Custom Risk Management

```python
from algorithms.live_trading import AbacusAITradingEngine

class CustomTradingEngine(AbacusAITradingEngine):
    def _update_risk_metrics(self):
        # Custom risk calculation
        self.risk_metrics.custom_metric = self.calculate_custom_risk()
        super()._update_risk_metrics()
```

## 📈 Performance Monitoring

### Metrics Tracking

```python
# Automatic performance tracking
stats = trading_engine.get_status()
print(f"Daily P&L: ${stats['risk_metrics']['daily_pnl']:,.2f}")
print(f"Current Drawdown: {stats['risk_metrics']['current_drawdown']:.2%}")
```

### Alert System

```python
# Configure alerts in config
config = get_config('production', {
    'enable_alerts': True,
    'alert_email': 'trader@company.com',
    'alert_webhook': 'https://hooks.slack.com/...'
})
```

## 🧪 Testing

### Run Complete Example

```bash
cd code/lean/
python example_complete.py
```

This will demonstrate:
- Backtesting with historical data
- Cache performance
- Redis integration (if available)
- Configuration management

### Unit Tests

```python
# Test cache functionality
from config.prediction_cache import get_prediction_cache
cache = get_prediction_cache(mock_algorithm)
assert cache.get('test_key') is not None
```

## 🚨 Risk Management

### Built-in Risk Controls

- **Position Limits**: Maximum position size per symbol
- **Daily Loss Limits**: Maximum daily loss threshold
- **Drawdown Protection**: Automatic trading pause on excessive drawdown
- **Stop Loss**: Configurable stop loss percentages
- **Take Profit**: Configurable take profit levels

### Custom Risk Rules

```python
# Add custom risk checks
def custom_risk_check(portfolio_value, market_conditions):
    if market_conditions['vix'] > 30:
        return False  # Pause trading during high volatility
    return True

# Integrate with trading engine
trading_engine.custom_risk_check = custom_risk_check
```

## 📝 Logging and Debugging

### Algorithm Logging

```python
# Built-in logging
self.Debug(f"Prediction confidence: {confidence}")
self.Debug(f"Trade executed: {symbol} {quantity} shares")
self.Debug(f"Portfolio value: ${portfolio_value:,.2f}")
```

### Performance Analysis

```python
# Weekly performance reports
self.Schedule.On(
    self.DateRules.DayOfWeek(DayOfWeek.Friday),
    self.TimeRules.At(16, 0),
    self._weekly_performance_report
)
```

## 🔍 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Start Redis server
   redis-server
   ```

2. **ObjectStore Not Available**
   ```python
   # Enable caching
   config.enable_caching = True
   ```

3. **API Rate Limits**
   ```python
   # Increase cache TTL
   config.cache_default_ttl = 7200  # 2 hours
   ```

### Debug Mode

```python
# Enable debug logging
config = get_config('development')
config.cache_enable_stats = True
```

## 📚 API Reference

### Key Classes

- `AbacusAIPredictionsData`: PythonData class for ML predictions
- `AbacusAILeanAlgorithm`: Main algorithm template
- `AbacusAIBacktestFramework`: Backtesting system
- `AbacusAITradingEngine`: Live trading engine
- `AbacusPredictionCache`: Caching system
- `AbacusRedisManager`: Redis communication

### Configuration

- `AbacusAIConfig`: Complete configuration class
- `get_config()`: Environment-based config retrieval
- `get_strategy_config()`: Strategy-specific configs

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## 📄 License

This integration system is provided as-is for educational and research purposes. Please ensure compliance with Abacus.AI and QuantConnect terms of service.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the example implementation
3. Check QuantConnect and Abacus.AI documentation
4. Create an issue with detailed reproduction steps

---

**Note**: This is a comprehensive integration system. Start with the basic example and gradually add complexity based on your requirements. Always test thoroughly before deploying to live trading environments.