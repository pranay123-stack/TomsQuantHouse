# CrewAI Trading Agent System

A comprehensive multi-agent system for automated trading that leverages CrewAI, machine learning, and advanced risk management to make intelligent trading decisions.

## 🚀 Features

### Specialized Agents
- **Market Research Analyst**: Conducts market analysis, company research, and identifies trading opportunities
- **ML Prediction Engineer**: Builds and deploys machine learning models for price prediction and strategy backtesting
- **Chief Risk Officer**: Manages portfolio risk, compliance checking, and regulatory oversight
- **Execution Trader**: Handles optimal trade execution with minimal market impact

### Advanced Capabilities
- **Role-based Task Delegation**: Each agent has domain-specific expertise and responsibilities
- **Redis Memory Integration**: Crew-wide memory storage for context sharing and state persistence
- **Intelligent Caching**: Reduces redundant tool calls and optimizes performance
- **Task Chaining**: Dependencies and context passing between agents for complex workflows
- **Human-in-the-Loop Approvals**: Critical decisions require manual approval with customizable thresholds
- **Real-time Monitoring**: Continuous market monitoring and alert generation
- **RESTful API**: FastAPI interface for external integration

### Risk Management
- **VaR Calculations**: Value at Risk with multiple confidence levels
- **Stress Testing**: Portfolio analysis under various market scenarios
- **Compliance Checking**: Regulatory and policy compliance validation
- **Position Limits**: Dynamic position sizing and concentration limits

### Execution Excellence
- **Optimal Strategies**: TWAP, VWAP, Iceberg, and Immediate execution strategies
- **Market Impact Analysis**: Real-time impact estimation and minimization
- **Execution Analytics**: Performance tracking and slippage analysis

## 📁 Project Structure

```
crewai/
├── agents/                 # Specialized agent implementations
│   ├── market_research_analyst.py
│   ├── ml_prediction_engineer.py
│   ├── chief_risk_officer.py
│   └── execution_trader.py
├── tasks/                  # Task definitions and workflows
│   └── task_definitions.py
├── orchestration/          # System orchestration
│   ├── crew_orchestrator.py
│   └── approval_workflow.py
├── cache/                  # Caching system
│   └── cache_manager.py
├── utils/                  # Utility modules
│   └── memory_manager.py
├── api/                    # REST API interface
│   └── server.py
├── config/                 # Configuration
│   └── settings.py
├── examples/               # Integration examples
│   └── integration_examples.py
└── requirements.txt        # Dependencies
```

## 🛠 Installation

1. **Clone and Setup**:
```bash
cd code/crewai
pip install -r requirements.txt
```

2. **Redis Setup** (Required for memory management):
```bash
# Install Redis
sudo apt-get install redis-server

# Start Redis
redis-server

# Verify Redis is running
redis-cli ping
```

3. **Environment Configuration**:
Create a `.env` file in the root directory:
```env
# API Keys
openai_api_key=your_openai_api_key
alpha_vantage_api_key=your_alpha_vantage_key

# Redis Configuration
redis_host=localhost
redis_port=6379
redis_db=0

# Trading Parameters
max_position_size=10000
risk_tolerance=0.02
max_drawdown=0.05

# Approval Thresholds
approval_required_amount=50000
high_risk_threshold=0.05
```

## 🚀 Quick Start

### Basic Usage

1. **Run Integration Examples**:
```bash
python examples/integration_examples.py examples
```

2. **Start the API Server**:
```bash
python examples/integration_examples.py api
```

3. **Access API Documentation**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Programmatic Integration

```python
import asyncio
from orchestration.crew_orchestrator import create_crew_orchestrator

async def main():
    # Initialize crew
    orchestrator = await create_crew_orchestrator("my_trading_crew", async_mode=True)
    await orchestrator.initialize()
    
    # Run complete analysis
    result = await orchestrator.run_complete_analysis("AAPL")
    print("Analysis Result:", result)
    
    # Execute trade
    trade_request = {
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 100,
        "execution_strategy": "twap"
    }
    trade_result = await orchestrator.execute_trade_workflow(trade_request)
    print("Trade Result:", trade_result)
    
    # Cleanup
    await orchestrator.shutdown()

asyncio.run(main())
```

## 🔧 API Reference

### Core Endpoints

#### Health Check
```http
GET /health
```

#### Market Analysis
```http
POST /analysis/complete
{
  "symbols": ["AAPL", "MSFT"],
  "analysis_type": "complete"
}
```

#### Trade Execution
```http
POST /trade/submit
{
  "symbol": "AAPL",
  "side": "buy",
  "quantity": 100,
  "execution_strategy": "twap"
}
```

#### Portfolio Review
```http
POST /portfolio/review
{
  "positions": {"AAPL": {"quantity": 100}},
  "cash": 10000,
  "total_value": 25000
}
```

#### Approval Management
```http
GET /approvals/pending
POST /approvals/{approval_id}/decision
GET /approvals/{approval_id}/status
```

### WebSocket Integration

Connect to real-time updates:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/client123');

// Subscribe to alerts
ws.send(JSON.stringify({
  type: 'subscribe_alerts'
}));

// Receive alerts
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Alert:', data);
};
```

## 🧠 Agent Architecture

### Market Research Analyst
- **Responsibilities**: Market analysis, company research, opportunity identification
- **Tools**: Market data fetcher, news sentiment analyzer, economic data tools
- **Output**: Market conditions, sector analysis, trading opportunities

### ML Prediction Engineer
- **Responsibilities**: Model building, prediction generation, backtesting
- **Tools**: Feature engineering, model training, prediction tools
- **Output**: Price predictions, model performance, strategy backtests

### Chief Risk Officer
- **Responsibilities**: Risk assessment, compliance checking, portfolio oversight
- **Tools**: Risk calculator, compliance checker, stress testing tools
- **Output**: Risk metrics, compliance status, stress test results

### Execution Trader
- **Responsibilities**: Trade execution, market monitoring, execution optimization
- **Tools**: Order execution, market monitoring, strategy optimization
- **Output**: Execution results, market conditions, performance analytics

## 📊 Memory Management

The system uses Redis for crew-wide memory storage:

### Memory Types
- **Crew Memory**: Shared context across all agents
- **Agent Memory**: Agent-specific knowledge and state
- **Cache Storage**: Cached data to avoid redundant computations
- **Portfolio State**: Current portfolio positions and values

### Key Features
- Automatic TTL expiration
- Cross-agent context sharing
- State persistence across restarts
- Performance optimization through caching

## 🔒 Approval Workflow

### Approval Types
- **Trade Execution**: High-value or risky trades
- **Risk Violations**: Breaches of risk parameters
- **Strategy Changes**: Modifications to trading strategies
- **Emergency Stops**: Immediate position liquidation

### Approval Process
1. **Automatic Submission**: System identifies need for approval
2. **Risk Assessment**: CRO evaluates compliance and risk
3. **Human Review**: Designated approvers review request
4. **Decision Processing**: Approval/rejection with notes
5. **Execution/Blocking**: Trade proceeds or is blocked

### Auto-Approval Logic
Low-risk transactions are automatically approved:
```python
# Auto-approve criteria
if (trade_amount < 10000 and 
    risk_score < 0.3 and 
    position_within_limits):
    # Auto-approve
    approval_status = "approved"
```

## 📈 Risk Management

### Risk Metrics
- **Value at Risk (VaR)**: Potential loss estimates
- **Volatility Analysis**: Price movement statistics
- **Correlation Analysis**: Asset relationship mapping
- **Maximum Drawdown**: Historical loss patterns
- **Beta Calculation**: Market sensitivity measures

### Stress Testing
Simulates portfolio performance under:
- Market crashes (-30% equity shock)
- Interest rate shocks (+200bps)
- Volatility spikes (3x normal)
- Correlation breakdowns
- Liquidity crises

### Compliance Monitoring
- Position limits enforcement
- Sector concentration rules
- Regulatory requirement checking
- Liquidity assessment

## ⚡ Performance Optimization

### Caching Strategy
- **Market Data**: 5-minute cache for price data
- **Predictions**: 30-minute cache for ML predictions
- **Risk Metrics**: 15-minute cache for risk calculations
- **Company Data**: 1-hour cache for fundamental data

### Parallel Processing
- Independent analyses run simultaneously
- Market data fetching parallelized
- Multi-symbol analysis supported
- Asynchronous execution throughout

### Resource Management
- Automatic memory cleanup
- Connection pooling
- Lazy loading of components
- Graceful error handling

## 🔧 Configuration

### Trading Parameters
```python
# config/settings.py
class TradingSettings(BaseSettings):
    max_position_size: float = 10000.0
    risk_tolerance: float = 0.02
    max_drawdown: float = 0.05
    approval_required_amount: float = 50000.0
    high_risk_threshold: float = 0.05
```

### Agent Configuration
Each agent can be customized:
```python
analyst = MarketResearchAnalyst(crew_id="my_crew")
analyst.agent.llm_config = {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
}
```

### Redis Configuration
```python
memory_manager = CrewMemoryManager(
    redis_url="redis://localhost:6379/0"
)
```

## 🧪 Testing

### Unit Tests
```bash
cd tests
python -m pytest unit/
```

### Integration Tests
```bash
python -m pytest integration/
```

### End-to-End Tests
```bash
python -m pytest e2e/
```

### Performance Tests
```bash
python -m pytest performance/
```

## 📚 Examples

### Complete Analysis Workflow
```python
# Analyze a single stock
result = await orchestrator.run_complete_analysis("AAPL")

# Parallel analysis for multiple stocks
results = await orchestrator.run_parallel_analysis(["AAPL", "MSFT", "GOOGL"])
```

### Trade Execution with Approval
```python
# Submit high-value trade
trade_request = {
    "symbol": "TSLA",
    "side": "buy", 
    "quantity": 500,
    "execution_strategy": "twap"
}

result = await orchestrator.execute_trade_workflow(trade_request)
# If approval required, returns approval_id
# Otherwise executes immediately
```

### Portfolio Risk Assessment
```python
portfolio_data = {
    "positions": {"AAPL": {"quantity": 100}, "MSFT": {"quantity": 50}},
    "returns_data": [0.01, -0.02, 0.03] * 100  # Historical returns
}

risk_assessment = await orchestrator.chief_risk_officer.assess_portfolio_risk(portfolio_data)
```

### Custom Strategy Implementation
```python
class CustomStrategy:
    async def run(self, orchestrator):
        # Step 1: Market analysis
        market = await orchestrator.market_research_analyst.analyze_market_conditions()
        
        # Step 2: Identify opportunities
        opportunities = await orchestrator.market_research_analyst.identify_opportunities()
        
        # Step 3: For each opportunity
        for opp in opportunities["opportunities"]:
            analysis = await orchestrator.run_complete_analysis(opp["symbol"])
            
            # Step 4: Risk assessment
            risk = await orchestrator.chief_risk_officer.assess_portfolio_risk(portfolio_data)
            
            # Step 5: Decision and execution
            if self.should_trade(analysis, risk):
                await orchestrator.execute_trade_workflow(trade_request)
```

## 🚨 Error Handling

### Graceful Degradation
- Failed components don't crash the entire system
- Fallback mechanisms for missing data
- Circuit breakers for external API failures
- Comprehensive logging and monitoring

### Error Recovery
- Automatic retry mechanisms
- State recovery from memory
- Manual intervention capabilities
- Health check monitoring

## 🔍 Monitoring & Analytics

### Metrics Dashboard
```http
GET /metrics/crew
```

Returns:
- Tasks completed/failed
- Approval request statistics
- Execution success rates
- Memory usage statistics
- Cache hit rates

### Alert System
- High-risk situations
- Execution failures
- Memory usage warnings
- System health issues

### Performance Tracking
- Response time monitoring
- Resource utilization
- Success/failure rates
- Cache effectiveness

## 🛡 Security

### API Security
- Input validation and sanitization
- Rate limiting
- Authentication (configurable)
- HTTPS enforcement (production)

### Data Protection
- Encrypted storage (configurable)
- Secure communication
- Access logging
- Audit trails

## 🔄 Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  crewai-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crewai-trading
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crewai-trading
  template:
    metadata:
      labels:
        app: crewai-trading
    spec:
      containers:
      - name: crewai-api
        image: crewai-trading:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "redis-service"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Documentation
- API docs: http://localhost:8000/docs
- Architecture docs: `/docs` directory
- Examples: `/examples` directory

### Common Issues

**Redis Connection Error**:
```bash
# Check Redis status
redis-cli ping

# Start Redis if not running
redis-server
```

**Memory Issues**:
```python
# Check memory usage
metrics = await orchestrator.get_crew_metrics()
print(metrics["memory_usage"])

# Clear cache
await cache_manager.clear_category("market_data")
```

**API Key Issues**:
```bash
# Verify environment variables
python -c "from config.settings import settings; print(settings.openai_api_key)"
```

### Getting Help
- Create an issue for bugs
- Check existing issues for solutions
- Review logs for error details
- Test with minimal examples

## 🎯 Roadmap

### Short Term
- [ ] Additional ML models (LSTM, Transformer)
- [ ] Enhanced visualization dashboard
- [ ] More execution strategies
- [ ] Improved caching algorithms

### Medium Term
- [ ] Multi-asset portfolio optimization
- [ ] Options trading strategies
- [ ] Real-time news integration
- [ ] Advanced risk models

### Long Term
- [ ] Multi-timeframe analysis
- [ ] Portfolio rebalancing automation
- [ ] Regulatory reporting automation
- [ ] Cloud deployment templates

---

Built with ❤️ using CrewAI, FastAPI, and modern AI technologies for intelligent trading automation.