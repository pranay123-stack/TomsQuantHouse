"""
Task Definitions for CrewAI Trading Agents
Defines specialized tasks for each agent with clear objectives and dependencies
"""
from typing import Dict, List, Optional, Any, Union
from crewai import Task
from pydantic import BaseModel
import json


class TaskConfig(BaseModel):
    """Configuration for task creation"""
    name: str
    description: str
    agent_role: str
    expected_output: str
    context_key: Optional[str] = None
    dependencies: List[str] = []
    priority: str = "medium"  # low, medium, high, critical
    timeout: int = 300  # seconds


class MarketResearchTasks:
    """Task definitions for Market Research Analyst"""
    
    @staticmethod
    def analyze_market_conditions() -> Task:
        """Task to analyze overall market conditions"""
        return Task(
            description="""
            Analyze current market conditions for major indices and sectors.
            
            Your analysis should include:
            1. Current market trends and momentum
            2. Sector performance comparison
            3. Market volatility assessment
            4. Key economic indicators impact
            5. Identification of market themes and drivers
            
            Use available market data tools to gather comprehensive information.
            Focus on actionable insights that can inform trading strategies.
            """,
            expected_output="""
            Provide a comprehensive market analysis report with:
            - Market overview with key statistics
            - Sector performance breakdown
            - Volatility assessment
            - Economic indicator analysis
            - Trading implications and opportunities
            """,
            agent="Market Research Analyst"
        )
    
    @staticmethod
    def research_company(symbol: str) -> Task:
        """Task to research a specific company"""
        return Task(
            description=f"""
            Conduct comprehensive research on company: {symbol}
            
            Your research should cover:
            1. Fundamental analysis (financial metrics, ratios)
            2. Technical analysis and price action
            3. News sentiment and market perception
            4. Competitive positioning
            5. Growth prospects and risks
            6. Analyst recommendations and price targets
            
            Use market data tools and news sentiment analysis.
            Provide investment thesis with supporting data.
            """,
            expected_output=f"""
            Company research report for {symbol} including:
            - Fundamental analysis summary
            - Technical analysis insights
            - Sentiment analysis results
            - Investment recommendation with rationale
            - Key risks and opportunities
            - Price target and timeline
            """,
            agent="Market Research Analyst"
        )
    
    @staticmethod
    def identify_trading_opportunities() -> Task:
        """Task to identify specific trading opportunities"""
        return Task(
            description="""
            Identify specific trading opportunities based on market analysis.
            
            Consider:
            1. High-volume price movements
            2. Sector rotation opportunities
            3. Earnings and event-driven trades
            4. Technical breakout patterns
            5. Risk-reward asymmetry situations
            
            Use cached market analysis and technical indicators.
            Focus on opportunities with clear entry/exit criteria.
            """,
            expected_output="""
            List of trading opportunities with:
            - Symbol and opportunity type
            - Entry criteria and rationale
            - Expected return potential
            - Risk assessment
            - Recommended position size
            - Time horizon for trade
            """
        )
    
    @staticmethod
    def analyze_sector_trends() -> Task:
        """Task to analyze sector rotation and trends"""
        return Task(
            description="""
            Analyze current sector trends and rotation patterns.
            
            Examine:
            1. Sector performance over different timeframes
            2. Relative strength indicators
            3. Money flow analysis
            4. Sector correlation changes
            5. Economic cycle implications
            
            Identify sectors showing strength or weakness.
            Look for rotation opportunities.
            """,
            expected_output="""
            Sector analysis report including:
            - Performance rankings by sector
            - Rotation patterns identified
            - Strong/weak sectors with rationale
            - Sector allocation recommendations
            - Risk considerations by sector
            """
        )


class MLPredictionTasks:
    """Task definitions for ML Prediction Engineer"""
    
    @staticmethod
    def build_price_prediction_model(symbol: str, model_type: str = "random_forest") -> Task:
        """Task to build price prediction model"""
        return Task(
            description=f"""
            Build and train a price prediction model for {symbol} using {model_type}.
            
            Your process should include:
            1. Feature engineering from price, volume, and technical indicators
            2. Data preprocessing and normalization
            3. Model training with proper validation
            4. Hyperparameter optimization
            5. Model evaluation and performance metrics
            6. Feature importance analysis
            
            Use historical data and ensure model robustness.
            Provide clear performance metrics and limitations.
            """,
            expected_output=f"""
            Model development report for {symbol}:
            - Model architecture and parameters
            - Training data statistics
            - Performance metrics (MSE, MAE, R²)
            - Feature importance ranking
            - Backtesting results
            - Model limitations and recommendations
            """,
            agent="ML Prediction Engineer"
        )
    
    @staticmethod
    def generate_price_predictions(symbol: str, model_type: str = "random_forest") -> Task:
        """Task to generate price predictions"""
        return Task(
            description=f"""
            Generate price predictions for {symbol} using the trained {model_type} model.
            
            Provide predictions for:
            1. Next day price movement
            2. Short-term trend (1 week)
            3. Medium-term outlook (1 month)
            4. Confidence intervals
            5. Risk assessment
            
            Include model uncertainty quantification.
            Explain prediction rationale and key factors.
            """,
            expected_output=f"""
            Price prediction report for {symbol}:
            - Next day prediction with confidence interval
            - Short-term outlook (1 week)
            - Medium-term projection (1 month)
            - Model confidence metrics
            - Key influencing factors
            - Risk considerations
            """
        )
    
    @staticmethod
    def backtest_trading_strategy(symbol: str, strategy: str = "momentum") -> Task:
        """Task to backtest trading strategy"""
        return Task(
            description=f"""
            Backtest the {strategy} trading strategy for {symbol}.
            
            Analysis should include:
            1. Historical performance metrics
            2. Win/loss ratio and average returns
            3. Maximum drawdown analysis
            4. Sharpe ratio and risk-adjusted returns
            5. Trade frequency and holding periods
            6. Market condition sensitivity
            
            Use sufficient historical data for statistical significance.
            Identify strategy strengths and weaknesses.
            """,
            expected_output=f"""
            Backtest results for {symbol} {strategy} strategy:
            - Total return and performance metrics
            - Risk metrics (drawdown, volatility)
            - Trade statistics (win rate, avg return)
            - Performance by market conditions
            - Strategy optimization recommendations
            """
        )
    
    @staticmethod
    def assess_model_performance(symbol: str, model_type: str = "random_forest") -> Task:
        """Task to assess model performance and reliability"""
        return Task(
            description=f"""
            Assess the performance and reliability of the {model_type} model for {symbol}.
            
            Evaluation criteria:
            1. Prediction accuracy metrics
            2. Model stability over time
            3. Overfitting assessment
            4. Feature stability analysis
            5. Model degradation detection
            6. Comparison with benchmarks
            
            Provide recommendations for model maintenance.
            """,
            expected_output=f"""
            Model performance assessment for {symbol}:
            - Accuracy and reliability metrics
            - Model stability analysis
            - Overfitting assessment
            - Feature importance stability
            - Maintenance recommendations
            - Model refresh schedule
            """
        )


class RiskManagementTasks:
    """Task definitions for Chief Risk Officer"""
    
    @staticmethod
    def assess_portfolio_risk(portfolio_data: Dict[str, Any]) -> Task:
        """Task to assess overall portfolio risk"""
        return Task(
            description=f"""
            Conduct comprehensive risk assessment for the trading portfolio.
            
            Analysis should cover:
            1. Value at Risk (VaR) calculations
            2. Portfolio volatility and correlation
            3. Maximum drawdown analysis
            4. Beta and systematic risk
            5. Concentration risk assessment
            6. Stress testing scenarios
            
            Use portfolio composition and historical returns.
            Provide risk metrics with confidence intervals.
            """,
            expected_output="""
            Portfolio risk assessment report:
            - VaR metrics at different confidence levels
            - Volatility and correlation analysis
            - Drawdown statistics and periods
            - Risk decomposition by position
            - Stress test results
            - Risk management recommendations
            """,
            agent="Chief Risk Officer"
        )
    
    @staticmethod
    def check_trade_compliance(trade_request: Dict[str, Any]) -> Task:
        """Task to check trade compliance"""
        return Task(
            description="""
            Check if the proposed trade complies with risk management policies.
            
            Compliance checks:
            1. Position size limits
            2. Sector concentration rules
            3. Risk tolerance parameters
            4. Regulatory requirements
            5. Liquidity considerations
            6. Correlation exposure limits
            
            Flag any violations requiring approval.
            """,
            expected_output="""
            Trade compliance report:
            - Compliance status (pass/fail)
            - Detailed violation analysis
            - Risk impact assessment
            - Approval requirements
            - Alternative recommendations
            """
        )
    
    @staticmethod
    def calculate_risk_metrics(positions: Dict[str, Any]) -> Task:
        """Task to calculate detailed risk metrics"""
        return Task(
            description="""
            Calculate detailed risk metrics for current positions.
            
            Metrics to calculate:
            1. Individual position VaR
            2. Position beta calculations
            3. Concentration metrics
            4. Liquidity risk assessment
            5. Correlation analysis
            6. Scenario analysis
            
            Provide actionable risk insights.
            """,
            expected_output="""
            Risk metrics report:
            - Individual position risk metrics
            - Portfolio-level risk indicators
            - Risk concentration analysis
            - Liquidity assessment
            - Risk optimization suggestions
            """
        )
    
    @staticmethod
    def run_stress_tests(portfolio_data: Dict[str, Any]) -> Task:
        """Task to run portfolio stress tests"""
        return Task(
            description="""
            Run stress tests on the portfolio under various scenarios.
            
            Stress scenarios:
            1. Market crash (-30% equity shock)
            2. Interest rate shock (+200bps)
            3. Volatility spike (3x normal)
            4. Correlation breakdown
            5. Liquidity crisis
            6. Custom scenarios
            
            Quantify potential losses and recovery times.
            """,
            expected_output="""
            Stress test results:
            - Loss projections by scenario
            - Portfolio resilience analysis
            - Recovery time estimates
            - Mitigation strategies
            - Risk monitoring recommendations
            """
        )


class ExecutionTasks:
    """Task definitions for Execution Trader"""
    
    @staticmethod
    def execute_trade(trade_request: Dict[str, Any]) -> Task:
        """Task to execute a trade with optimal strategy"""
        return Task(
            description=f"""
            Execute the trade request with optimal execution strategy.
            
            Trade details: {json.dumps(trade_request, indent=2)}
            
            Execution process:
            1. Determine optimal execution strategy
            2. Calculate market impact estimates
            3. Execute with minimal slippage
            4. Monitor execution quality
            5. Report execution results
            
            Minimize market impact and transaction costs.
            """,
            expected_output="""
            Trade execution report:
            - Execution strategy used
            - Execution prices and quantities
            - Market impact and slippage
            - Transaction costs
            - Execution quality metrics
            - Post-trade analysis
            """,
            agent="Execution Trader"
        )
    
    @staticmethod
    def optimize_execution_strategy(order_characteristics: Dict[str, Any]) -> Task:
        """Task to optimize execution strategy"""
        return Task(
            description="""
            Determine the optimal execution strategy for the given order characteristics.
            
            Consider:
            1. Order size relative to market volume
            2. Market liquidity and conditions
            3. Time urgency requirements
            4. Market volatility
            5. Historical execution quality
            
            Recommend specific strategy with rationale.
            """,
            expected_output="""
            Strategy optimization report:
            - Recommended execution strategy
            - Rationale and analysis
            - Expected market impact
            - Alternative strategies comparison
            - Execution timeline
            - Risk considerations
            """
        )
    
    @staticmethod
    def monitor_market_conditions(symbols: List[str]) -> Task:
        """Task to monitor market conditions for execution timing"""
        return Task(
            description=f"""
            Monitor market conditions for symbols: {symbols}
            
            Monitor for:
            1. Price movements and volatility
            2. Volume patterns
            3. Bid-ask spreads
            4. Market microstructure
            5. Optimal execution windows
            
            Provide timing recommendations for orders.
            """,
            expected_output="""
            Market monitoring report:
            - Current market conditions for each symbol
            - Execution timing recommendations
            - Liquidity assessment
            - Volatility analysis
            - Optimal execution windows
            """
        )
    
    @staticmethod
    def analyze_execution_performance(limit: int = 10) -> Task:
        """Task to analyze execution performance"""
        return Task(
            description=f"""
            Analyze execution performance for recent {limit} trades.
            
            Analysis should cover:
            1. Execution quality vs. benchmarks
            2. Slippage analysis
            3. Strategy effectiveness
            4. Cost analysis
            5. Performance trends
            
            Identify areas for improvement.
            """,
            expected_output="""
            Execution performance analysis:
            - Performance metrics summary
            - Slippage analysis by strategy
            - Cost breakdown
            - Performance trends
            - Improvement recommendations
            """
        )


class TaskOrchestrator:
    """Orchestrates task dependencies and execution flow"""
    
    def __init__(self, crew_id: str):
        self.crew_id = crew_id
        self.task_registry = {}
    
    def register_task(self, task: Task, dependencies: List[str] = None) -> str:
        """Register task with dependencies"""
        task_id = f"{task.agent}_{task.description[:50]}..."
        self.task_registry[task_id] = {
            "task": task,
            "dependencies": dependencies or [],
            "completed": False,
            "result": None
        }
        return task_id
    
    def get_execution_order(self, required_tasks: List[str]) -> List[str]:
        """Determine execution order based on dependencies"""
        # Simple topological sort for task dependencies
        ordered_tasks = []
        remaining_tasks = set(required_tasks)
        
        while remaining_tasks:
            # Find tasks with no unresolved dependencies
            ready_tasks = []
            for task_id in remaining_tasks:
                if task_id in self.task_registry:
                    deps = self.task_registry[task_id]["dependencies"]
                    if not any(dep in remaining_tasks for dep in deps):
                        ready_tasks.append(task_id)
            
            if not ready_tasks:
                # Handle circular dependencies or missing tasks
                break
            
            ordered_tasks.extend(ready_tasks)
            remaining_tasks -= set(ready_tasks)
        
        return ordered_tasks
    
    def update_task_result(self, task_id: str, result: Any):
        """Update task result in registry"""
        if task_id in self.task_registry:
            self.task_registry[task_id]["result"] = result
            self.task_registry[task_id]["completed"] = True


# Task factory functions
def create_trading_analysis_workflow(symbol: str) -> Dict[str, Task]:
    """Create a complete workflow for trading analysis"""
    return {
        "market_research": MarketResearchTasks.research_company(symbol),
        "ml_prediction": MLPredictionTasks.build_price_prediction_model(symbol),
        "risk_assessment": RiskManagementTasks.calculate_risk_metrics({"symbol": symbol}),
        "execution_analysis": ExecutionTasks.optimize_execution_strategy({"symbol": symbol})
    }


def create_trade_execution_workflow(trade_request: Dict[str, Any]) -> Dict[str, Task]:
    """Create workflow for trade execution"""
    return {
        "compliance_check": RiskManagementTasks.check_trade_compliance(trade_request),
        "execution_optimization": ExecutionTasks.optimize_execution_strategy(trade_request),
        "trade_execution": ExecutionTasks.execute_trade(trade_request)
    }


def create_portfolio_review_workflow(portfolio_data: Dict[str, Any]) -> Dict[str, Task]:
    """Create workflow for portfolio review"""
    return {
        "market_analysis": MarketResearchTasks.analyze_market_conditions(),
        "risk_assessment": RiskManagementTasks.assess_portfolio_risk(portfolio_data),
        "performance_analysis": ExecutionTasks.analyze_execution_performance(),
        "stress_testing": RiskManagementTasks.run_stress_tests(portfolio_data)
    }