#!/usr/bin/env python3
"""
Complete Trading Integration Example

Demonstrates a comprehensive trading system built on the Letta Integration API.
This example shows how to build a complete trading dashboard with all features.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import Letta Integration API components
from letta_integration_api import create_trading_integration
from letta_client import TradeEvent, AgentRole
from agent_communication import AgentCapability, MessagePriority
from backup_restore import BackupType


class TradingDashboard:
    """
    Complete Trading Dashboard using Letta Integration API
    
    This dashboard demonstrates:
    - Real-time memory management
    - Automated trading workflow execution
    - Multi-agent communication
    - Performance monitoring
    - Backup and recovery
    """
    
    def __init__(self):
        self.api = None
        self.agents = {}
        self.dashboard_data = {}
        
    async def initialize(self, letta_config: Dict[str, Any]):
        """Initialize the trading dashboard"""
        
        print("🚀 Initializing Trading Dashboard...")
        
        # Create trading integration
        self.api = create_trading_integration(
            letta_config=letta_config,
            backup_directory="./trading_backups"
        )
        
        # Start the system
        self.api.start()
        print("✅ Trading Dashboard initialized")
        
        # Setup agents
        await self._setup_agents()
        
        # Load initial data
        await self._load_initial_data()
        
        print("🎯 Dashboard ready for trading operations")
    
    async def _setup_agents(self):
        """Setup trading agents in the system"""
        
        print("\n🤖 Setting up Trading Agents...")
        
        # Register Trading Strategist Agent
        strategist_capabilities = [
            AgentCapability("strategy_development", "Develop and optimize trading strategies", 5, ["strategy", "optimization"]),
            AgentCapability("pattern_recognition", "Identify trading patterns and setups", 4, ["patterns", "analysis"]),
            AgentCapability("risk_assessment", "Assess trading risks and manage exposure", 3, ["risk", "assessment"])
        ]
        
        success = self.api.register_agent(
            agent_id="trading_strategist",
            name="Trading Strategist",
            role="strategist",
            capabilities=[{
                "name": cap.name,
                "description": cap.description,
                "level": cap.level,
                "tags": cap.tags
            } for cap in strategist_capabilities]
        )
        
        if success:
            print("   ✅ Trading Strategist registered")
            self.agents["trading_strategist"] = {
                "role": "strategist",
                "capabilities": len(strategist_capabilities),
                "status": "active"
            }
        else:
            print("   ❌ Failed to register Trading Strategist")
        
        # Register Market Analyst Agent
        analyst_capabilities = [
            AgentCapability("market_analysis", "Analyze market conditions and trends", 5, ["market", "analysis"]),
            AgentCapability("data_processing", "Process and analyze trading data", 4, ["data", "processing"]),
            AgentCapability("technical_analysis", "Perform technical analysis", 4, ["technical", "analysis"])
        ]
        
        success = self.api.register_agent(
            agent_id="market_analyst",
            name="Market Analyst",
            role="analyst",
            capabilities=[{
                "name": cap.name,
                "description": cap.description,
                "level": cap.level,
                "tags": cap.tags
            } for cap in analyst_capabilities]
        )
        
        if success:
            print("   ✅ Market Analyst registered")
            self.agents["market_analyst"] = {
                "role": "analyst",
                "capabilities": len(analyst_capabilities),
                "status": "active"
            }
        else:
            print("   ❌ Failed to register Market Analyst")
        
        # Register Risk Manager Agent
        risk_capabilities = [
            AgentCapability("risk_management", "Manage portfolio risk and exposure", 5, ["risk", "management"]),
            AgentCapability("portfolio_monitoring", "Monitor portfolio performance and risk", 4, ["portfolio", "monitoring"]),
            AgentCapability("compliance", "Ensure regulatory compliance", 3, ["compliance", "regulation"])
        ]
        
        success = self.api.register_agent(
            agent_id="risk_manager",
            name="Risk Manager",
            role="risk_manager",
            capabilities=[{
                "name": cap.name,
                "description": cap.description,
                "level": cap.level,
                "tags": cap.tags
            } for cap in risk_capabilities]
        )
        
        if success:
            print("   ✅ Risk Manager registered")
            self.agents["risk_manager"] = {
                "role": "risk_manager",
                "capabilities": len(risk_capabilities),
                "status": "active"
            }
        else:
            print("   ❌ Failed to register Risk Manager")
    
    async def _load_initial_data(self):
        """Load initial trading data and strategies"""
        
        print("\n📊 Loading Initial Trading Data...")
        
        # Create initial trading strategies
        strategies = [
            {
                "block_type": "trading_strategy",
                "title": "Moving Average Crossover",
                "content": "Strategy using moving average crossovers for entry and exit signals. Fast MA (20) crossing above slow MA (50) for long entries.",
                "priority": "high",
                "tags": ["strategy", "moving_average", "trend_following"]
            },
            {
                "block_type": "trading_strategy", 
                "title": "RSI Reversal Strategy",
                "content": "Mean reversion strategy using RSI oversold/overbought levels. Buy when RSI < 30, sell when RSI > 70.",
                "priority": "medium",
                "tags": ["strategy", "rsi", "mean_reversion"]
            },
            {
                "block_type": "risk_parameters",
                "title": "Portfolio Risk Limits",
                "content": "Maximum position size: 5% of portfolio per trade. Maximum daily loss: 2% of portfolio. Maximum sector exposure: 20%.",
                "priority": "critical",
                "tags": ["risk", "position_sizing", "limits"]
            }
        ]
        
        for strategy in strategies:
            block_id = self.api.create_memory_block(
                agent_id="trading_strategist",
                block_type=strategy["block_type"],
                title=strategy["title"],
                content=strategy["content"],
                priority=strategy["priority"],
                tags=strategy["tags"]
            )
            
            if block_id:
                print(f"   ✅ Created: {strategy['title']}")
            else:
                print(f"   ❌ Failed to create: {strategy['title']}")
        
        # Create initial trading patterns
        patterns = [
            {
                "symbol": "AAPL",
                "pattern_type": "bullish_breakout",
                "success_rate": 0.75,
                "confidence": 0.8,
                "conditions": {"volume_spike": True, "rsi_oversold": False},
                "entry_signals": ["price_breaks_resistance", "volume_confirmation"],
                "exit_signals": ["stop_loss", "profit_target"],
                "risk_metrics": {"max_risk": 0.02, "position_size": 0.1}
            },
            {
                "symbol": "TSLA",
                "pattern_type": "reversal_pattern",
                "success_rate": 0.65,
                "confidence": 0.7,
                "conditions": {"oversold": True, "volume_divergence": True},
                "entry_signals": ["reversal_signal"],
                "exit_signals": ["stop_loss"],
                "risk_metrics": {"max_risk": 0.025, "position_size": 0.08}
            }
        ]
        
        for pattern in patterns:
            pattern_id = self.api.create_trading_pattern(
                agent_id="trading_strategist",
                **pattern
            )
            
            if pattern_id:
                print(f"   ✅ Created pattern: {pattern['pattern_type']} for {pattern['symbol']}")
            else:
                print(f"   ❌ Failed to create pattern: {pattern['pattern_type']}")
    
    async def simulate_trading_day(self):
        """Simulate a complete trading day"""
        
        print("\n📈 Simulating Trading Day...")
        
        # Simulate market analysis
        await self._perform_market_analysis()
        
        # Simulate trade opportunities
        opportunities = await self._identify_trading_opportunities()
        
        # Simulate trade executions
        for opportunity in opportunities:
            await self._execute_trade(opportunity)
        
        # Analyze performance
        await self._analyze_daily_performance()
        
        # Generate insights
        await self._generate_trading_insights()
    
    async def _perform_market_analysis(self):
        """Perform market analysis"""
        
        print("\n🔍 Performing Market Analysis...")
        
        # Get market context
        context = self.api.get_market_context("market_analyst")
        print(f"   Market Regime: {context.get('current_regime', {}).get('regime', 'unknown')}")
        
        # Update market conditions
        market_update = {
            "block_type": "market_conditions",
            "title": f"Market Update - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "content": f"Current market conditions: {context.get('current_regime', {}).get('regime', 'unknown')}. Volatility: moderate.",
            "priority": "medium",
            "tags": ["market", "daily_update", datetime.now().strftime('%Y-%m-%d')]
        }
        
        block_id = self.api.create_memory_block(
            agent_id="market_analyst",
            **market_update
        )
        
        if block_id:
            print("   ✅ Market conditions updated")
        
        # Send analysis to strategist
        analysis_message = self.api.send_message(
            sender_agent_id="market_analyst",
            receiver_agent_id="trading_strategist",
            subject="Daily Market Analysis",
            content="Market analysis completed. Current regime suggests trending conditions.",
            priority="normal"
        )
        
        if analysis_message:
            print("   ✅ Market analysis sent to strategist")
    
    async def _identify_trading_opportunities(self) -> List[Dict[str, Any]]:
        """Identify trading opportunities"""
        
        print("\n🎯 Identifying Trading Opportunities...")
        
        # Get trading opportunities
        opportunities = self.api.get_trading_opportunities(
            "trading_strategist",
            confidence_threshold=0.7
        )
        
        print(f"   Found {len(opportunities)} opportunities")
        
        for opp in opportunities[:3]:  # Show first 3
            print(f"   📊 {opp['symbol']}: {opp['pattern_type']} (confidence: {opp['confidence']:.1%})")
        
        return opportunities
    
    async def _execute_trade(self, opportunity: Dict[str, Any]):
        """Execute a trade based on opportunity"""
        
        print(f"\n💼 Executing Trade: {opportunity['symbol']} - {opportunity['pattern_type']}")
        
        # Simulate trade execution
        entry_price = 150.00 + (hash(opportunity['symbol']) % 100) / 100  # Simulated price
        quantity = int(1000 / entry_price)  # Position sizing based on $1000
        exit_price = entry_price * (1 + (hash(opportunity['symbol']) % 20 - 10) / 1000)  # Simulated P&L
        pnl = (exit_price - entry_price) * quantity
        
        trade_outcome = "win" if pnl > 0 else "loss"
        
        # Create trade event
        trade_data = {
            "trade_id": f"trade_{int(time.time())}_{opportunity['symbol']}",
            "symbol": opportunity['symbol'],
            "action": "buy",
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": round(pnl, 2),
            "strategy": opportunity['pattern_type'],
            "confidence": opportunity['confidence'],
            "outcome": trade_outcome,
            "timestamp": datetime.now(),
            "metadata": {
                "opportunity_id": opportunity.get('pattern_id'),
                "execution_type": "automated"
            }
        }
        
        print(f"   📈 Trade: {quantity} shares @ ${entry_price:.2f} -> ${exit_price:.2f} (PnL: ${pnl:.2f})")
        
        # Record trade outcome
        success = self.api.record_trade_outcome("trading_strategist", trade_data)
        if success:
            print("   ✅ Trade outcome recorded")
        
        # Execute trade analysis workflow
        workflow_id = self.api.execute_trade_analysis_workflow("trading_strategist", trade_data)
        if workflow_id:
            print(f"   ✅ Trade analysis workflow started: {workflow_id}")
        
        # Send notification to risk manager
        notification = self.api.send_message(
            sender_agent_id="trading_strategist",
            receiver_agent_id="risk_manager",
            subject=f"Trade Executed: {opportunity['symbol']}",
            content=f"Executed {trade_outcome} trade on {opportunity['symbol']}. PnL: ${pnl:.2f}",
            priority=MessagePriority.HIGH.value
        )
        
        if notification:
            print("   ✅ Trade notification sent to risk manager")
        
        return trade_data
    
    async def _analyze_daily_performance(self):
        """Analyze daily trading performance"""
        
        print("\n📊 Analyzing Daily Performance...")
        
        # Get performance analysis
        performance = self.api.get_performance_analysis("trading_strategist", period_days=1)
        
        if "error" not in performance:
            basic = performance["basic_metrics"]
            print(f"   📈 Total Trades: {basic['total_trades']}")
            print(f"   🎯 Win Rate: {basic['win_rate']:.1%}")
            print(f"   💰 Total P&L: ${basic['total_pnl']:.2f}")
            print(f"   📊 Profit Factor: {basic['profit_factor']:.2f}")
        else:
            print(f"   ❌ Performance analysis failed: {performance['error']}")
    
    async def _generate_trading_insights(self):
        """Generate trading insights and recommendations"""
        
        print("\n💡 Generating Trading Insights...")
        
        # Get trading advice
        advice = self.api.get_trading_advice(
            "trading_strategist",
            "current market conditions and strategy performance"
        )
        
        print(f"   🎯 Confidence Score: {advice.get('confidence_score', 0):.1%}")
        print(f"   📊 Market Regime: {advice.get('market_regime', 'unknown')}")
        
        for recommendation in advice.get('recommendations', [])[:2]:
            print(f"   💡 Recommendation: {recommendation}")
        
        # Memory optimization
        optimization_report = self.api.optimize_memory("trading_strategist")
        if optimization_report["success"]:
            print(f"   🧹 Optimized {optimization_report['blocks_processed']} memory blocks")
        else:
            print(f"   ❌ Memory optimization failed: {optimization_report.get('error', 'Unknown error')}")
    
    async def backup_system(self):
        """Create backup of the trading system"""
        
        print("\n💾 Creating System Backup...")
        
        # Create backup for each agent
        for agent_id in self.agents.keys():
            backup_id = self.api.create_backup(
                agent_id=agent_id,
                backup_type=BackupType.FULL,
                description=f"Daily backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                tags=["daily", "trading_system", "complete"]
            )
            
            if backup_id:
                print(f"   ✅ Backup created for {agent_id}: {backup_id}")
            else:
                print(f"   ❌ Backup failed for {agent_id}")
    
    async def get_system_status(self):
        """Get comprehensive system status"""
        
        print("\n📋 System Status Report")
        print("=" * 50)
        
        # Overall system status
        status = self.api.get_system_status()
        
        print(f"🏥 Overall Health: {status['integration_system']['status']}")
        print(f"🤖 Active Agents: {status['memory_management'].get('active_agents', 0)}")
        print(f"💬 Communication: {'Enabled' if status['communication'].get('enabled', False) else 'Disabled'}")
        print(f"📊 Monitoring: {'Enabled' if status['performance'].get('enabled', False) else 'Disabled'}")
        
        # Agent details
        print(f"\n🤖 Registered Agents: {len(self.agents)}")
        for agent_id, info in self.agents.items():
            print(f"   • {agent_id}: {info['role']} ({info['capabilities']} capabilities)")
        
        # Recent messages
        for agent_id in self.agents.keys():
            recent_messages = self.api.get_recent_messages(agent_id, time_range_hours=24)
            print(f"💬 {agent_id}: {len(recent_messages)} recent messages")
        
        # Memory usage
        for agent_id in self.agents.keys():
            usage = self.api.get_memory_usage(agent_id)
            print(f"🧠 {agent_id}: {usage.total_blocks} blocks ({usage.total_size_bytes / 1024:.1f} KB)")
        
        # Recent backups
        backups = self.api.list_backups()
        print(f"💾 Available Backups: {len(backups)}")
        
        print("=" * 50)
    
    async def run_dashboard(self, duration_minutes: int = 30):
        """Run the trading dashboard for specified duration"""
        
        print(f"\n🚀 Starting Trading Dashboard (Duration: {duration_minutes} minutes)")
        print("=" * 70)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        cycle_count = 0
        
        try:
            while time.time() < end_time:
                cycle_count += 1
                current_time = datetime.now()
                
                print(f"\n🔄 Trading Cycle #{cycle_count} - {current_time.strftime('%H:%M:%S')}")
                
                # Perform trading cycle
                await self.simulate_trading_day()
                
                # Periodic system status
                if cycle_count % 5 == 0:
                    await self.get_system_status()
                
                # Periodic backup
                if cycle_count % 10 == 0:
                    await self.backup_system()
                
                # Wait for next cycle (simulate time passing)
                await asyncio.sleep(2)  # 2 seconds between cycles for demo
                
                # Calculate remaining time
                remaining_time = max(0, end_time - time.time())
                remaining_minutes = remaining_time / 60
                
                if remaining_minutes > 0:
                    print(f"⏰ Remaining time: {remaining_minutes:.1f} minutes")
        
        except KeyboardInterrupt:
            print("\n⚠️  Dashboard interrupted by user")
        
        finally:
            # Final status report
            await self.get_system_status()
            
            # Create final backup
            await self.backup_system()
            
            # Shutdown
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the trading dashboard"""
        
        print("\n🔄 Shutting down Trading Dashboard...")
        
        if self.api:
            self.api.stop()
            print("✅ Integration API stopped")
        
        print("👋 Trading Dashboard shutdown complete")
    
    def get_dashboard_info(self) -> Dict[str, Any]:
        """Get dashboard information and statistics"""
        
        info = {
            "dashboard_type": "trading",
            "agents_registered": len(self.agents),
            "agent_details": self.agents,
            "features_enabled": {
                "memory_management": True,
                "trading_workflows": True,
                "agent_communication": True,
                "backup_restore": True,
                "performance_monitoring": True
            },
            "version": "1.0.0",
            "created_at": datetime.now().isoformat()
        }
        
        return info


async def main():
    """Main function to run the trading dashboard"""
    
    # Configuration
    letta_config = {
        "base_url": "http://localhost:8283",
        "api_key": "your-secret-api-key",
        "enable_caching": True,
        "enable_monitoring": True,
        "cache_ttl": 300,
        "rate_limit": 5.0
    }
    
    print("🎯 Letta Trading Dashboard Demo")
    print("=" * 70)
    print("This demo showcases a complete trading system built on Letta")
    print("It includes:")
    print("• Multi-agent communication and coordination")
    print("• Automated trading workflow execution")
    print("• Real-time memory management and optimization")
    print("• Performance monitoring and analytics")
    print("• Backup and restore functionality")
    print("• Intelligent trading insights and recommendations")
    print("=" * 70)
    
    # Create dashboard
    dashboard = TradingDashboard()
    
    try:
        # Initialize dashboard
        await dashboard.initialize(letta_config)
        
        # Show dashboard info
        info = dashboard.get_dashboard_info()
        print(f"\n📊 Dashboard Info:")
        print(f"   Type: {info['dashboard_type']}")
        print(f"   Version: {info['version']}")
        print(f"   Agents: {info['agents_registered']}")
        print(f"   Features: {list(info['features_enabled'].keys())}")
        
        # Run dashboard for 5 minutes
        await dashboard.run_dashboard(duration_minutes=5)
        
    except ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nPlease ensure:")
        print("1. Letta server is running on http://localhost:8283")
        print("2. API key is correct in the configuration")
        print("3. Network connectivity is available")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        
    finally:
        # Cleanup
        await dashboard.shutdown()


if __name__ == "__main__":
    # Run the demo
    print("Starting Letta Trading Dashboard Demo...")
    asyncio.run(main())