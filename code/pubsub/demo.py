#!/usr/bin/env python3
"""
Demo script for the Agent Communication System.
This script demonstrates the main features and usage patterns.
"""

import asyncio
import json
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import system components
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from communication_system import (
    AgentCommunicationSystem, AgentConfig, create_communication_system
)
from schemas.message_schemas import MessageFactory, Priority, SecurityLevel
from config_example import get_config

# Demo configuration
DEMO_CONFIG = get_config("development")


class TradingAgent:
    """Demo trading agent"""
    
    def __init__(self, agent_id: str, system: AgentCommunicationSystem):
        self.agent_id = agent_id
        self.system = system
        self.running = False
        self.positions = {}
        self.signal_count = 0
    
    async def start(self):
        """Start the trading agent"""
        self.running = True
        print(f"🚀 Starting trading agent {self.agent_id}")
        
        # Register with the system
        agent_config = AgentConfig(
            agent_id=self.agent_id,
            agent_type="trading",
            capabilities=["signal_generation", "risk_management"],
            endpoint=f"tcp://localhost:{8000 + hash(self.agent_id) % 1000}",
            region="us-east-1",
            tags=["crypto", "trading"],
            security_level=SecurityLevel.HIGH
        )
        
        success = await self.system.register_agent(agent_config)
        if success:
            print(f"✅ Agent {self.agent_id} registered successfully")
        else:
            print(f"❌ Failed to register agent {self.agent_id}")
            return
        
        # Start main loop
        await self._trading_loop()
    
    async def _trading_loop(self):
        """Main trading loop"""
        while self.running:
            try:
                # Generate trading signals
                await self._generate_signals()
                
                # Process incoming coordination requests
                await self._process_coordination()
                
                # Send periodic heartbeat
                await self._send_heartbeat()
                
                # Wait before next iteration
                await asyncio.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"❌ Error in trading loop for {self.agent_id}: {e}")
                await asyncio.sleep(5)
    
    async def _generate_signals(self):
        """Generate random trading signals"""
        if random.random() < 0.3:  # 30% chance to generate signal
            symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
            symbol = random.choice(symbols)
            
            signal_type = random.choice(["BUY", "SELL", "HOLD"])
            price = random.uniform(1000, 50000)
            confidence = random.uniform(0.5, 0.95)
            
            # Create trade signal
            signal = MessageFactory.create_trade_signal(
                sender_id=self.agent_id,
                symbol=symbol,
                signal=signal_type,
                price=price,
                confidence=confidence,
                strategy="demo_strategy",
                metadata={
                    "timeframe": "1h",
                    "indicators": ["RSI", "MACD", "SMA"],
                    "volatility": random.uniform(0.01, 0.1)
                }
            )
            
            # Send signal
            success = await self.system.send_message(signal)
            if success:
                self.signal_count += 1
                print(f"📊 {self.agent_id}: Generated {signal_type} signal for {symbol} @ ${price:.2f}")
    
    async def _process_coordination(self):
        """Process coordination requests (simplified)"""
        # In a real implementation, this would handle incoming coordination messages
        if random.random() < 0.1:  # 10% chance to start coordination
            await self.system.start_coordination(
                coordinator_id=self.agent_id,
                task_type="portfolio_review",
                participants=["risk_manager_agent"],
                parameters={
                    "review_scope": "daily",
                    "symbols": ["BTCUSDT", "ETHUSDT"],
                    "analysis_depth": "standard"
                }
            )
    
    async def _send_heartbeat(self):
        """Send heartbeat with health information"""
        heartbeat = MessageFactory.create_heartbeat(
            sender_id=self.agent_id,
            status="active",
            performance_metrics={
                "signals_generated": self.signal_count,
                "uptime": time.time(),
                "cpu_usage": random.uniform(10, 50),
                "memory_usage": random.uniform(20, 80)
            }
        )
        
        await self.system.send_message(heartbeat, secure=False)
    
    async def stop(self):
        """Stop the trading agent"""
        self.running = False
        print(f"🛑 Stopping trading agent {self.agent_id}")


class AnalysisAgent:
    """Demo analysis agent"""
    
    def __init__(self, agent_id: str, system: AgentCommunicationSystem):
        self.agent_id = agent_id
        self.system = system
        self.running = False
        self.analysis_count = 0
    
    async def start(self):
        """Start the analysis agent"""
        self.running = True
        print(f"🔍 Starting analysis agent {self.agent_id}")
        
        # Register with the system
        agent_config = AgentConfig(
            agent_id=self.agent_id,
            agent_type="analysis",
            capabilities=["pattern_recognition", "prediction", "sentiment_analysis"],
            endpoint=f"tcp://localhost:{8000 + hash(self.agent_id) % 1000}",
            region="us-east-1",
            tags=["analysis", "ml"],
            security_level=SecurityLevel.HIGH
        )
        
        success = await self.system.register_agent(agent_config)
        if success:
            print(f"✅ Analysis agent {self.agent_id} registered successfully")
        else:
            print(f"❌ Failed to register analysis agent {self.agent_id}")
            return
        
        # Start main loop
        await self._analysis_loop()
    
    async def _analysis_loop(self):
        """Main analysis loop"""
        while self.running:
            try:
                # Generate analysis results
                await self._generate_analysis()
                
                # Process market updates
                await self._process_market_data()
                
                # Send periodic heartbeat
                await self._send_heartbeat()
                
                # Wait before next iteration
                await asyncio.sleep(random.uniform(3, 7))
                
            except Exception as e:
                print(f"❌ Error in analysis loop for {self.agent_id}: {e}")
                await asyncio.sleep(5)
    
    async def _generate_analysis(self):
        """Generate analysis and predictions"""
        if random.random() < 0.4:  # 40% chance to generate analysis
            symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
            symbol = random.choice(symbols)
            
            analysis_types = ["technical_analysis", "sentiment_analysis", "pattern_recognition"]
            analysis_type = random.choice(analysis_types)
            
            if analysis_type == "technical_analysis":
                # Create technical analysis
                prediction = MessageFactory.create_prediction(
                    sender_id=self.agent_id,
                    model="TechnicalAnalyzer_v2",
                    prediction="bullish_trend",
                    confidence=random.uniform(0.6, 0.9),
                    features=["rsi", "macd", "bollinger_bands", "volume"],
                    analysis_type=analysis_type,
                    symbol=symbol,
                    timeframe="4h"
                )
            
            elif analysis_type == "sentiment_analysis":
                # Create sentiment analysis
                prediction = MessageFactory.create_prediction(
                    sender_id=self.agent_id,
                    model="SentimentAnalyzer_v1",
                    prediction="positive_sentiment",
                    confidence=random.uniform(0.5, 0.8),
                    features=["social_sentiment", "news_sentiment", "fear_greed_index"],
                    analysis_type=analysis_type,
                    symbol=symbol,
                    sources=["twitter", "reddit", "news"]
                )
            
            else:  # pattern_recognition
                # Create pattern recognition
                prediction = MessageFactory.create_prediction(
                    sender_id=self.agent_id,
                    model="PatternRecognition_v3",
                    prediction="bull_flag_pattern",
                    confidence=random.uniform(0.7, 0.95),
                    features=["price_action", "volume_profile", "support_resistance"],
                    analysis_type=analysis_type,
                    symbol=symbol,
                    pattern_confidence=random.uniform(0.6, 0.9)
                )
            
            # Send prediction
            success = await self.system.send_message(prediction)
            if success:
                self.analysis_count += 1
                print(f"📈 {self.agent_id}: Generated {analysis_type} for {symbol}")
    
    async def _process_market_data(self):
        """Process market data updates"""
        if random.random() < 0.2:  # 20% chance to send market update
            symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
            symbol = random.choice(symbols)
            
            # Create market update (using trade signal as proxy for demo)
            market_update = MessageFactory.create_trade_signal(
                sender_id=self.agent_id,
                symbol=symbol,
                signal="MARKET_UPDATE",
                price=random.uniform(1000, 50000),
                volume=random.uniform(100000, 10000000),
                confidence=1.0,
                metadata={
                    "update_type": "price_change",
                    "change_percent": random.uniform(-5, 5),
                    "market_cap": random.uniform(1000000000, 1000000000000),
                    "volume_24h": random.uniform(10000000, 1000000000)
                }
            )
            
            await self.system.send_message(market_update)
    
    async def _send_heartbeat(self):
        """Send heartbeat with analysis metrics"""
        heartbeat = MessageFactory.create_heartbeat(
            sender_id=self.agent_id,
            status="analyzing",
            performance_metrics={
                "analyses_completed": self.analysis_count,
                "uptime": time.time(),
                "cpu_usage": random.uniform(20, 60),
                "memory_usage": random.uniform(30, 70),
                "models_loaded": random.randint(2, 5)
            }
        )
        
        await self.system.send_message(heartbeat, secure=False)
    
    async def stop(self):
        """Stop the analysis agent"""
        self.running = False
        print(f"🛑 Stopping analysis agent {self.agent_id}")


class DemoOrchestrator:
    """Demo orchestrator to manage the entire system"""
    
    def __init__(self):
        self.system = None
        self.agents: List[any] = []
        self.running = False
    
    async def setup(self):
        """Set up the demo system"""
        print("🚀 Setting up Agent Communication System Demo...")
        
        # Create the communication system
        self.system = await create_communication_system("demo_system", DEMO_CONFIG)
        
        # Start the system
        await self.system.start()
        print("✅ System started successfully")
        
        # Create and start agents
        await self._create_agents()
        
        # Start monitoring tasks
        await self._start_monitoring_tasks()
    
    async def _create_agents(self):
        """Create demo agents"""
        # Create trading agents
        trading_agents = [
            TradingAgent(f"trading_agent_{i}", self.system)
            for i in range(1, 4)
        ]
        
        # Create analysis agents
        analysis_agents = [
            AnalysisAgent(f"analysis_agent_{i}", self.system)
            for i in range(1, 3)
        ]
        
        self.agents = trading_agents + analysis_agents
        
        # Start all agents
        for agent in self.agents:
            asyncio.create_task(agent.start())
            await asyncio.sleep(0.1)  # Stagger agent startup
    
    async def _start_monitoring_tasks(self):
        """Start monitoring and reporting tasks"""
        # System status reporter
        asyncio.create_task(self._status_reporter())
        
        # Performance monitor
        asyncio.create_task(self._performance_monitor())
        
        # Alert generator
        asyncio.create_task(self._alert_generator())
    
    async def _status_reporter(self):
        """Report system status periodically"""
        while self.running:
            try:
                status = await self.system.get_system_status()
                
                print(f"\n📊 System Status Report ({datetime.now().strftime('%H:%M:%S')})")
                print(f"State: {status['state']}")
                print(f"Uptime: {status['uptime_seconds']:.1f} seconds")
                print(f"Registered Agents: {status['registered_agents']}")
                print(f"Messages Processed: {status['statistics']['messages_processed']}")
                print(f"Coordination Tasks: {status['statistics']['coordination_tasks']}")
                print(f"Active Alerts: {status.get('alert_stats', {}).get('active_alerts', 0)}")
                
                # Agent-specific stats
                active_agents = [agent for agent in self.agents if agent.running]
                print(f"Active Agent Processes: {len(active_agents)}")
                
                await asyncio.sleep(30)  # Report every 30 seconds
                
            except Exception as e:
                print(f"❌ Error in status reporter: {e}")
                await asyncio.sleep(5)
    
    async def _performance_monitor(self):
        """Monitor system performance"""
        while self.running:
            try:
                # Generate performance alert sometimes
                if random.random() < 0.1:  # 10% chance
                    await self._generate_performance_alert()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"❌ Error in performance monitor: {e}")
                await asyncio.sleep(10)
    
    async def _generate_performance_alert(self):
        """Generate performance-related alert"""
        alert_types = ["HIGH_LATENCY", "THROUGHPUT_WARNING", "RESOURCE_USAGE"]
        alert_type = random.choice(alert_types)
        
        alert = MessageFactory.create_alert(
            sender_id="system_monitor",
            alert_type="WARNING" if alert_type in ["HIGH_LATENCY", "THROUGHPUT_WARNING"] else "INFO",
            message=f"Performance metric: {alert_type}",
            component="demo_system",
            metadata={
                "alert_type": alert_type,
                "metric_value": random.uniform(0.5, 2.0),
                "threshold": 1.0,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        await self.system.send_message(alert)
        print(f"⚠️ Generated performance alert: {alert_type}")
    
    async def _alert_generator(self):
        """Generate random system alerts"""
        alert_scenarios = [
            ("INFO", "System backup completed successfully", "backup_service"),
            ("WARNING", "High memory usage detected in agent process", "agent_manager"),
            ("ERROR", "Database connection timeout", "persistence_service"),
            ("INFO", "New agent version deployed", "deployment_service")
        ]
        
        while self.running:
            try:
                await asyncio.sleep(random.uniform(20, 60))  # Random interval
                
                # Generate alert with some probability
                if random.random() < 0.3:  # 30% chance
                    alert_type, message, component = random.choice(alert_scenarios)
                    
                    alert = MessageFactory.create_alert(
                        sender_id="demo_alert_system",
                        alert_type=alert_type,
                        message=message,
                        component=component,
                        metadata={
                            "source": "demo_generator",
                            "severity_score": random.uniform(1, 10),
                            "auto_resolvable": random.choice([True, False])
                        }
                    )
                    
                    await self.system.send_message(alert)
                    print(f"🚨 Generated {alert_type} alert: {message}")
                
            except Exception as e:
                print(f"❌ Error in alert generator: {e}")
                await asyncio.sleep(5)
    
    async def run_demo(self, duration_seconds: int = 300):
        """Run the demo for specified duration"""
        self.running = True
        print(f"🎬 Starting demo for {duration_seconds} seconds...")
        print("Press Ctrl+C to stop early\n")
        
        try:
            await asyncio.sleep(duration_seconds)
            
        except KeyboardInterrupt:
            print("\n🛑 Demo interrupted by user")
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up the demo"""
        print("\n🧹 Cleaning up demo...")
        self.running = False
        
        # Stop all agents
        for agent in self.agents:
            await agent.stop()
        
        # Stop the system
        if self.system:
            await self.system.stop()
        
        print("✅ Demo cleanup completed")


async def main():
    """Main demo function"""
    print("=" * 60)
    print("🤖 AGENT COMMUNICATION SYSTEM DEMO")
    print("=" * 60)
    print("This demo showcases:")
    print("• Multi-agent registration and discovery")
    print("• Real-time message routing and delivery")
    print("• Agent coordination and workflows")
    print("• Event-driven architecture")
    print("• Security and encryption")
    print("• Monitoring and analytics")
    print("• Message persistence and replay")
    print()
    
    # Create and run orchestrator
    orchestrator = DemoOrchestrator()
    
    try:
        await orchestrator.setup()
        await orchestrator.run_demo(duration_seconds=180)  # 3 minutes
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        
    finally:
        await orchestrator.cleanup()
    
    print("\n🎉 Demo completed successfully!")
    print("Thank you for trying the Agent Communication System!")


if __name__ == "__main__":
    # Run the demo
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo terminated by user")
    except Exception as e:
        print(f"\n💥 Demo crashed: {e}")
        import traceback
        traceback.print_exc()