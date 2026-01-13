#!/usr/bin/env python3
"""
Letta Agent Creation Script
Creates trading-focused agents with persistent memory blocks for:
- Trading strategies
- Market conditions
- Risk parameters
- Learned patterns
"""

import os
import json
import requests
from typing import Dict, List, Any
from datetime import datetime

class LettaAgentCreator:
    def __init__(self, base_url: str = "http://localhost:8283", api_key: str = "your-secret-api-key-here"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def create_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Letta agent with the specified configuration"""
        url = f"{self.base_url}/api/agents"
        
        try:
            response = requests.post(url, headers=self.headers, json=agent_config)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error creating agent: {e}")
            return {}
    
    def add_memory_block(self, agent_id: str, memory_config: Dict[str, Any]) -> Dict[str, Any]:
        """Add a memory block to an agent"""
        url = f"{self.base_url}/api/agents/{agent_id}/memory"
        
        try:
            response = requests.post(url, headers=self.headers, json=memory_config)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error adding memory block: {e}")
            return {}
    
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent details including memory"""
        url = f"{self.base_url}/api/agents/{agent_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting agent: {e}")
            return {}
    
    def create_trading_strategist_agent(self) -> str:
        """Create a specialized trading strategist agent"""
        agent_config = {
            "name": "trading_strategist",
            "description": "Advanced trading strategy agent with market analysis capabilities",
            "system_prompt": """You are an expert trading strategist with deep knowledge of financial markets, 
            risk management, and quantitative analysis. You help develop and optimize trading strategies based on 
            market conditions, historical data, and risk parameters. You have access to persistent memory that 
            stores your trading knowledge, strategies, and learned patterns.

            Your core responsibilities:
            1. Analyze market data and identify trading opportunities
            2. Develop and refine trading strategies based on backtesting
            3. Provide risk-adjusted recommendations
            4. Learn from past trades and market patterns
            5. Adapt strategies to changing market conditions

            Always prioritize capital preservation while seeking optimal risk-adjusted returns.""",
            "model": "gpt-4",
            "tools": ["python_code", "web_search", "file_operations"],
            "metadata": {
                "specialization": "trading",
                "expertise": ["technical_analysis", "risk_management", "strategy_optimization"],
                "created_by": "letta_setup_script"
            }
        }
        
        agent = self.create_agent(agent_config)
        if not agent:
            return ""
        
        agent_id = agent.get("id", "")
        
        # Add trading strategy memory blocks
        self._add_trading_memory_blocks(agent_id)
        
        print(f"Created trading strategist agent: {agent_id}")
        return agent_id
    
    def create_market_analyst_agent(self) -> str:
        """Create a market analysis agent"""
        agent_config = {
            "name": "market_analyst",
            "description": "Market analysis agent specializing in real-time market condition assessment",
            "system_prompt": """You are a skilled market analyst with expertise in interpreting market data, 
            identifying trends, and providing insights into current market conditions. You analyze various 
            market indicators and provide actionable intelligence.

            Your core responsibilities:
            1. Monitor and analyze real-time market data
            2. Identify market trends and turning points
            3. Assess market sentiment and breadth
            4. Provide context for trading decisions
            5. Track key economic indicators and news events

            You have access to persistent memory that stores market patterns and conditions you've analyzed.""",
            "model": "claude-3-sonnet",
            "tools": ["python_code", "web_search", "data_analysis"],
            "metadata": {
                "specialization": "market_analysis",
                "expertise": ["trend_analysis", "market_indicators", "sentiment_analysis"],
                "created_by": "letta_setup_script"
            }
        }
        
        agent = self.create_agent(agent_config)
        if not agent:
            return ""
        
        agent_id = agent.get("id", "")
        
        # Add market analysis memory blocks
        self._add_market_analysis_memory_blocks(agent_id)
        
        print(f"Created market analyst agent: {agent_id}")
        return agent_id
    
    def create_risk_manager_agent(self) -> str:
        """Create a risk management agent"""
        agent_config = {
            "name": "risk_manager",
            "description": "Risk management agent focused on portfolio protection and risk assessment",
            "system_prompt": """You are a risk management expert specializing in portfolio protection, 
            position sizing, and risk assessment. You help ensure trading decisions align with risk 
            parameters and help protect capital during volatile market conditions.

            Your core responsibilities:
            1. Assess and manage portfolio risk
            2. Calculate optimal position sizes
            3. Set and monitor stop-loss levels
            4. Provide risk-adjusted trade recommendations
            5. Maintain discipline during drawdown periods

            You have access to persistent memory that stores risk parameters and management rules.""",
            "model": "gpt-4",
            "tools": ["python_code", "data_analysis", "calculation_tools"],
            "metadata": {
                "specialization": "risk_management",
                "expertise": ["position_sizing", "stop_loss", "portfolio_risk"],
                "created_by": "letta_setup_script"
            }
        }
        
        agent = self.create_agent(agent_config)
        if not agent:
            return ""
        
        agent_id = agent.get("id", "")
        
        # Add risk management memory blocks
        self._add_risk_management_memory_blocks(agent_id)
        
        print(f"Created risk manager agent: {agent_id}")
        return agent_id
    
    def _add_trading_memory_blocks(self, agent_id: str):
        """Add memory blocks for trading strategist agent"""
        memory_blocks = [
            {
                "block_type": "trading_strategy",
                "title": "Core Trading Principles",
                "content": """Core Trading Principles:
                1. Always manage risk first - position sizing based on account risk tolerance
                2. Use stop-losses on every trade without exception
                3. Follow the trend unless strong counter-trend signals emerge
                4. Diversify across multiple timeframes and instruments
                5. Document all trades for pattern analysis
                6. Never risk more than 1-2% per trade
                7. Wait for high-probability setups""",
                "value_type": "string",
                "metadata": {
                    "priority": "high",
                    "category": "core_principles",
                    "last_updated": datetime.now().isoformat()
                }
            },
            {
                "block_type": "learned_patterns",
                "title": "High Probability Setups",
                "content": """High Probability Setups (Win Rates):
                1. Pullback to 20-day MA after breakout - 75% win rate
                2. False breakouts that reverse within 2 hours - 68% win rate  
                3. Gap fills on high volume with support/resistance - 72% win rate
                4. Earnings announcements with pre-market momentum - 65% win rate
                5. Triple bottom bounce with volume confirmation - 70% win rate
                6. News-driven spikes with initial momentum fade - 62% win rate""",
                "value_type": "string",
                "metadata": {
                    "patterns": {
                        "pattern1": {"win_rate": 0.75, "type": "technical"},
                        "pattern2": {"win_rate": 0.68, "type": "reversal"},
                        "pattern3": {"win_rate": 0.72, "type": "gap_fill"},
                        "pattern4": {"win_rate": 0.65, "type": "earnings"},
                        "pattern5": {"win_rate": 0.70, "type": "technical"},
                        "pattern6": {"win_rate": 0.62, "type": "news"}
                    }
                }
            },
            {
                "block_type": "trading_strategy",
                "title": "Strategy Adaptation Rules",
                "content": """Strategy Adaptation Based on Market Conditions:

                BULL MARKET:
                - Focus on momentum strategies
                - Use trailing stops more aggressively
                - Allow for larger position sizes
                - Look for continuation patterns

                BEAR MARKET:
                - Focus on defensive strategies
                - Use tighter stops
                - Reduce position sizes by 50%
                - Look for short opportunities and bounces

                SIDEWAYS MARKET:
                - Focus on range-bound strategies
                - Buy support, sell resistance
- Use oscillators for timing
                - Smaller, frequent trades preferred""",
                "value_type": "string",
                "metadata": {
                    "market_phases": ["bull", "bear", "sideways"],
                    "adaptation_rules": True
                }
            }
        ]
        
        for block in memory_blocks:
            self.add_memory_block(agent_id, block)
    
    def _add_market_analysis_memory_blocks(self, agent_id: str):
        """Add memory blocks for market analyst agent"""
        memory_blocks = [
            {
                "block_type": "market_conditions",
                "title": "Bull Market Indicators",
                "content": """Bull Market Indicators:
                - SPY above 50-day moving average
                - VIX below 20 (low volatility)
                - Strong breadth (advance/decline ratio > 2)
                - Rising volume on up days
                - Economic growth indicators positive
                - Credit spreads tightening
                - Dollar strength supporting risk assets""",
                "value_type": "string",
                "metadata": {
                    "market_phase": "bull",
                    "indicators": ["SPY", "VIX", "breadth", "volume", "economic", "credit", "dollar"]
                }
            },
            {
                "block_type": "market_conditions",
                "title": "Bear Market Indicators",
                "content": """Bear Market Indicators:
                - SPY below 50-day moving average
                - VIX above 30 (high volatility)
                - Weak breadth (advance/decline ratio < 1)
                - Declining volume on down days
                - Economic indicators deteriorating
                - Credit spreads widening
                - Flight to quality (bonds, gold)""",
                "value_type": "string",
                "metadata": {
                    "market_phase": "bear",
                    "indicators": ["SPY", "VIX", "breadth", "volume", "economic", "credit", "flight_to_quality"]
                }
            },
            {
                "block_type": "system_context",
                "title": "Current Market Session",
                "content": """Current Market Session Information:
                Session Type: Regular trading hours (9:30 AM - 4:00 PM EST)
                Primary Focus: US equity markets (NYSE, NASDAQ)
                Time Zone: Eastern Time
                Key Monitoring: SPY, QQQ, IWM, major sector ETFs (XLF, XLK, XLE, XLI)
                Economic Calendar: Monitor Fed decisions, employment data, inflation reports
                Earnings Season: Track major earnings announcements and guidance updates""",
                "value_type": "string",
                "metadata": {
                    "session": "regular",
                    "timezone": "EST",
                    "markets": ["US_equities"],
                    "symbols": ["SPY", "QQQ", "IWM"]
                }
            },
            {
                "block_type": "recent",
                "title": "Market Monitoring Checklist",
                "content": """Daily Market Monitoring Checklist:
                1. Pre-market futures movement (ES, NQ, RTY)
                2. Major news events and their market impact
                3. Economic data releases for the day
                4. Key earnings announcements
                5. Fed speeches or central bank communications
                6. Market breadth indicators
                7. Sector rotation analysis
                8. VIX and volatility levels
                9. Currency and commodity movements
                10. International market performance""",
                "value_type": "string",
                "metadata": {
                    "checklist_type": "daily",
                    "monitoring_focus": "comprehensive"
                }
            }
        ]
        
        for block in memory_blocks:
            self.add_memory_block(agent_id, block)
    
    def _add_risk_management_memory_blocks(self, agent_id: str):
        """Add memory blocks for risk manager agent"""
        memory_blocks = [
            {
                "block_type": "risk_parameters",
                "title": "Portfolio Risk Limits",
                "content": """Portfolio Risk Management Limits:
                Maximum position size: 5% of portfolio per trade
                Maximum daily loss: 2% of portfolio
                Maximum weekly loss: 5% of portfolio
                Maximum monthly loss: 10% of portfolio
                Maximum concurrent open positions: 10
                Stop loss minimum: 1.5x ATR (Average True Range)
                Maximum sector concentration: 20%
                Maximum correlation between positions: 0.7
                Maximum leverage: 2:1 on margin accounts""",
                "value_type": "string",
                "metadata": {
                    "limits": {
                        "position_size": 0.05,
                        "daily_loss": 0.02,
                        "weekly_loss": 0.05,
                        "monthly_loss": 0.10,
                        "max_positions": 10,
                        "stop_loss_multiplier": 1.5,
                        "sector_concentration": 0.20,
                        "max_correlation": 0.70,
                        "max_leverage": 2.0
                    }
                }
            },
            {
                "block_type": "risk_parameters",
                "title": "Position Sizing Formula",
                "content": """Kelly Criterion Position Sizing:
                
                Basic Kelly Formula: f = (bp - q) / b
                Where:
                - f = fraction of capital to risk
                - b = odds received (reward/risk ratio)
                - p = probability of winning
                - q = probability of losing (1-p)

                Conservative Implementation:
                - Use 25% of calculated Kelly for safety
                - Cap at maximum position size (5%)
                - Adjust based on recent performance
                - Reduce size during drawdowns

                Alternative: Fixed Risk per Trade
                - Risk 1% of portfolio on standard trades
                - Risk 2% on highest confidence setups
                - Never risk more than account tolerance""",
                "value_type": "string",
                "metadata": {
                    "position_sizing": "kelly_criterion",
                    "conservative_factor": 0.25,
                    "default_risk": 0.01,
                    "high_confidence_risk": 0.02
                }
            },
            {
                "block_type": "risk_parameters",
                "title": "Stop Loss Guidelines",
                "content": """Stop Loss Implementation:
                
                Technical Stops:
                - Support/Resistance levels: 1-2% below entry
                - Moving averages: Below key MA (20, 50, 200)
                - Pattern invalidation: At pattern completion point
                
                Volatility Stops:
                - ATR-based: 1.5x ATR on 15-minute chart
                - Average True Range: Monitor daily and adjust stops
                
                Time-based Stops:
                - Intraday: Close if no movement within 2 hours
                - Swing trades: Review after 5-7 days
                
                Trail Stops:
                - Profit targets: 2:1 risk/reward minimum
                - Trailing stops: Move to breakeven at 1:1
                - Scale out: Take partial profits at key levels""",
                "value_type": "string",
                "metadata": {
                    "stop_types": ["technical", "volatility", "time_based", "trailing"],
                    "min_risk_reward": 2.0,
                    "breakeven_trigger": 1.0
                }
            }
        ]
        
        for block in memory_blocks:
            self.add_memory_block(agent_id, block)

def main():
    """Main function to create all trading agents"""
    creator = LettaAgentCreator()
    
    print("Creating Letta trading agents...")
    
    # Create all three agents
    agents_created = []
    
    # Create trading strategist
    strategist_id = creator.create_trading_strategist_agent()
    if strategist_id:
        agents_created.append(("Trading Strategist", strategist_id))
    
    # Create market analyst
    analyst_id = creator.create_market_analyst_agent()
    if analyst_id:
        agents_created.append(("Market Analyst", analyst_id))
    
    # Create risk manager
    risk_manager_id = creator.create_risk_manager_agent()
    if risk_manager_id:
        agents_created.append(("Risk Manager", risk_manager_id))
    
    # Save agent IDs for later use
    with open("/workspace/code/letta/agent_ids.json", "w") as f:
        json.dump({
            agent_name: agent_id 
            for agent_name, agent_id in agents_created
        }, f, indent=2)
    
    print(f"\nSuccessfully created {len(agents_created)} agents:")
    for name, agent_id in agents_created:
        print(f"- {name}: {agent_id}")
    
    print(f"\nAgent IDs saved to: /workspace/code/letta/agent_ids.json")

if __name__ == "__main__":
    main()