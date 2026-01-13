#!/usr/bin/env python3
"""
Demo Script for Agent Handoff and Decision-Making Workflow System

This script demonstrates the key features of the workflow system including:
- Creating workflow scenarios
- Executing agent handoffs
- Conflict detection and resolution
- Escalation triggers
- Performance tracking
- System monitoring
"""

import asyncio
import json
from datetime import datetime
import time
import random

# Import the workflow system
import sys
sys.path.append('/workspace/code/workflows')

from base_engine import WorkflowEngine, AgentRecommendation
from management.workflow_manager import WorkflowManager

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")

def print_subsection(title):
    """Print a formatted subsection header"""
    print(f"\n{'-' * 40}")
    print(f" {title}")
    print(f"{'-' * 40}")

async def demo_high_confidence_scenario():
    """Demo high confidence trading scenario"""
    print_section("HIGH CONFIDENCE TRADING SCENARIO")
    
    manager = WorkflowManager("/workspace/code/workflows")
    
    # Create workflow
    print("\n1. Creating high-confidence trading workflow...")
    result = manager.create_workflow_scenario(
        scenario_type="high_confidence_prediction",
        data={
            "symbol": "AAPL",
            "action": "buy",
            "confidence_score": 0.85,
            "position_size": 100000,
            "market_hours": True,
            "volatility": 0.15
        },
        priority=2,
        risk_level="medium"
    )
    
    if result['success']:
        workflow_id = result['workflow_id']
        print(f"   ✓ Workflow created: {workflow_id}")
        
        # Execute technical analysis step
        print("\n2. Technical analysis step...")
        tech_result = manager.execute_workflow_step(
            workflow_id=workflow_id,
            agent_type="technical_analyzer",
            agent_id="tech_analyzer_001",
            decision_data={
                "action": "analyze",
                "confidence": 0.82,
                "reasoning": "Strong RSI divergence and support level",
                "risk_assessment": "medium",
                "supporting_data": {
                    "rsi": 32,
                    "support_level": 175.50,
                    "volume": "increasing"
                },
                "outcome": {"successful": True, "return": 0}
            }
        )
        print(f"   ✓ Technical analysis completed by {tech_result['agent_id']}")
        
        # Risk assessment step
        print("\n3. Risk assessment step...")
        risk_result = manager.execute_workflow_step(
            workflow_id=workflow_id,
            agent_type="risk_analyzer",
            agent_id="risk_analyzer_001",
            decision_data={
                "action": "assess_risk",
                "confidence": 0.78,
                "reasoning": "Position size within acceptable risk parameters",
                "risk_assessment": "low",
                "supporting_data": {
                    "var_1day": 0.02,
                    "max_drawdown": 0.05,
                    "risk_reward_ratio": 2.1
                },
                "outcome": {"successful": True, "return": 0}
            }
        )
        print(f"   ✓ Risk assessment completed by {risk_result['agent_id']}")
        
        # Execution step
        print("\n4. Trade execution step...")
        exec_result = manager.execute_workflow_step(
            workflow_id=workflow_id,
            agent_type="execution_agent",
            agent_id="exec_agent_001",
            decision_data={
                "action": "execute_trade",
                "confidence": 0.88,
                "reasoning": "All conditions met, proceeding with execution",
                "risk_assessment": "low",
                "supporting_data": {
                    "execution_price": 176.25,
                    "slippage": 0.001,
                    "order_filled": True
                },
                "outcome": {"successful": True, "return": 0.015}
            }
        )
        print(f"   ✓ Trade executed successfully by {exec_result['agent_id']}")
        
        # Check conflicts
        print("\n5. Checking for conflicts...")
        conflicts = manager.workflow_engine.check_conflicts(workflow_id)
        if conflicts:
            print(f"   ⚠ {len(conflicts)} conflicts detected")
            for conflict in conflicts:
                print(f"     - Conflict severity: {conflict['severity']}")
        else:
            print("   ✓ No conflicts detected")
        
        # Check escalation
        should_escalate = manager.workflow_engine.should_escalate(workflow_id)
        print(f"\n6. Escalation check:")
        print(f"   {'✓ No escalation required' if not should_escalate else '⚠ Escalation required'}")
        
        # Get dashboard
        print("\n7. Workflow dashboard:")
        dashboard = manager.get_workflow_dashboard(workflow_id)
        if 'workflow_status' in dashboard:
            status = dashboard['workflow_status']
            print(f"   Status: {status.get('scenario_type', 'unknown')}")
            print(f"   Current agent: {status.get('current_agent', 'none')}")
        print(f"   Needs attention: {dashboard['needs_attention']}")
        print(f"   Agent performance: {len(dashboard['agent_performance'])} agents tracked")
        
        return workflow_id
    
    return None

async def demo_conflict_resolution():
    """Demo conflict detection and resolution"""
    print_section("CONFLICT DETECTION AND RESOLUTION")
    
    manager = WorkflowManager("/workspace/code/workflows")
    
    # Create workflow with potential conflicts
    print("\n1. Creating workflow with conflicting recommendations...")
    result = manager.create_workflow_scenario(
        scenario_type="market_volatility",
        data={
            "symbol": "TSLA",
            "action": "hold",
            "confidence_score": 0.65,
            "position_size": 500000,
            "volatility_score": 0.35,
            "market_hours": True
        },
        priority=3,
        risk_level="high"
    )
    
    if result['success']:
        workflow_id = result['workflow_id']
        print(f"   ✓ Workflow created: {workflow_id}")
        
        # Add conflicting recommendations
        print("\n2. Adding conflicting agent recommendations...")
        
        # Technical analyzer says SELL
        manager.execute_workflow_step(
            workflow_id=workflow_id,
            agent_type="technical_analyzer",
            agent_id="tech_analyzer_002",
            decision_data={
                "action": "sell",
                "confidence": 0.75,
                "reasoning": "Breaking support level, bearish divergence",
                "risk_assessment": "high",
                "supporting_data": {"support_broken": True},
                "outcome": {"successful": True}
            }
        )
        print("   - Technical analyzer: SELL (confidence: 0.75)")
        
        # Sentiment analyzer says BUY
        manager.execute_workflow_step(
            workflow_id=workflow_id,
            agent_type="sentiment_analyzer",
            agent_id="sentiment_001",
            decision_data={
                "action": "buy",
                "confidence": 0.72,
                "reasoning": "Positive earnings sentiment, retail interest high",
                "risk_assessment": "medium",
                "supporting_data": {"sentiment_score": 0.8},
                "outcome": {"successful": True}
            }
        )
        print("   - Sentiment analyzer: BUY (confidence: 0.72)")
        
        # Risk analyzer says HOLD
        manager.execute_workflow_step(
            workflow_id=workflow_id,
            agent_type="risk_analyzer",
            agent_id="risk_analyzer_001",
            decision_data={
                "action": "hold",
                "confidence": 0.68,
                "reasoning": "High volatility, maintain current position",
                "risk_assessment": "high",
                "supporting_data": {"volatility_risk": "high"},
                "outcome": {"successful": True}
            }
        )
        print("   - Risk analyzer: HOLD (confidence: 0.68)")
        
        # Detect conflicts
        print("\n3. Detecting conflicts...")
        conflicts = manager.workflow_engine.check_conflicts(workflow_id)
        print(f"   ✓ Detected {len(conflicts)} conflict(s)")
        
        for conflict in conflicts:
            print(f"   - Severity: {conflict['severity']}")
            print(f"   - Requires resolution: {conflict['requires_resolution']}")
        
        # Resolve conflicts
        print("\n4. Resolving conflicts...")
        resolution_result = manager.resolve_conflicts(workflow_id)
        if resolution_result['success']:
            print(f"   ✓ Resolved {resolution_result['conflicts_resolved']} conflict(s)")
            for resolution in resolution_result['resolutions']:
                print(f"   - Strategy: {resolution['strategy']}")
                if 'selected_recommendation' in resolution:
                    print(f"   - Selected action: {resolution['selected_recommendation'].get('action', 'N/A')}")
        
        return workflow_id
    
    return None

async def demo_escalation():
    """Demo escalation triggers and handling"""
    print_section("ESCALATION WORKFLOW")
    
    manager = WorkflowManager("/workspace/code/workflows")
    
    # Create workflow that will trigger escalation
    print("\n1. Creating high-risk workflow...")
    result = manager.create_workflow_scenario(
        scenario_type="risk_event",
        data={
            "symbol": "GME",
            "action": "sell",
            "confidence_score": 0.45,  # Low confidence
            "position_size": 8000000,   # Large position
            "risk_score": 0.9,          # High risk
            "volatility_spike": 0.6,
            "failure_count": 3          # Recent failures
        },
        priority=5,
        risk_level="critical"
    )
    
    if result['success']:
        workflow_id = result['workflow_id']
        print(f"   ✓ Workflow created: {workflow_id}")
        
        # Simulate escalation triggers
        print("\n2. Testing escalation triggers...")
        
        # Low confidence trigger
        escalation_result = manager.trigger_escalation(
            workflow_id=workflow_id,
            trigger_data={
                "trigger_type": "confidence_below_threshold",
                "confidence": 0.45,
                "threshold": 0.5
            }
        )
        print(f"   - Confidence escalation: {escalation_result['success']}")
        if escalation_result['success']:
            print(f"     Escalation ID: {escalation_result['escalation_id']}")
        
        # Large position trigger
        escalation_result = manager.trigger_escalation(
            workflow_id=workflow_id,
            trigger_data={
                "trigger_type": "large_position_threshold",
                "position_value": 8000000,
                "threshold": 5000000
            }
        )
        print(f"   - Large position escalation: {escalation_result['success']}")
        
        # Financial loss trigger
        escalation_result = manager.trigger_escalation(
            workflow_id=workflow_id,
            trigger_data={
                "trigger_type": "financial_loss_threshold",
                "loss_percentage": 0.08,
                "threshold": 0.05
            }
        )
        print(f"   - Financial loss escalation: {escalation_result['success']}")
        
        # Check escalation status
        print("\n3. Checking escalation status...")
        active_escalations = [
            esc for esc in manager.escalation_manager.active_escalations.values()
            if esc.workflow_id == workflow_id
        ]
        print(f"   Active escalations: {len(active_escalations)}")
        
        for esc in active_escalations:
            print(f"   - Level {esc.level.value}: {esc.description}")
            print(f"     Status: {esc.status.value}")
        
        return workflow_id
    
    return None

def demo_performance_tracking():
    """Demo performance tracking and analytics"""
    print_section("PERFORMANCE TRACKING")
    
    manager = WorkflowManager("/workspace/code/workflows")
    
    print("\n1. Getting system overview...")
    overview = manager.get_system_overview()
    
    if 'error' not in overview:
        print(f"   System status: {overview['system_status']}")
        print(f"   Active workflows: {overview['workflows']['active_workflows']}")
        print(f"   Success rate: {overview['system_health']['workflow_success_rate']:.2%}")
        
        print("\n2. Workflow metrics:")
        metrics = overview['workflows']['metrics']
        for key, value in metrics.items():
            print(f"   - {key}: {value}")
        
        print("\n3. Handoff metrics:")
        handoff_metrics = overview['handoffs']
        for key, value in handoff_metrics.items():
            print(f"   - {key}: {value}")
        
        print("\n4. Top performing agents:")
        for agent_type, performers in overview['top_agents'].items():
            print(f"   {agent_type}:")
            for performer in performers[:3]:  # Top 3
                print(f"     - {performer['agent_id']}: {performer['performance_score']:.3f}")
    
    else:
        print(f"   Error: {overview['error']}")

async def demo_versioning():
    """Demo version management and rollback"""
    print_section("VERSION MANAGEMENT")
    
    manager = WorkflowManager("/workspace/code/workflows")
    
    print("\n1. Getting version metrics...")
    version_metrics = manager.version_manager.get_version_metrics()
    print(f"   Total versions: {version_metrics['total_versions']}")
    print(f"   Active versions: {version_metrics['active_versions']}")
    print(f"   Total rollbacks: {version_metrics['total_rollbacks']}")
    
    print("\n2. Getting version history for high_confidence_prediction...")
    history = manager.version_manager.get_version_history("high_confidence_prediction")
    if history:
        for version in history[-3:]:  # Last 3 versions
            print(f"   - {version['version_number']}: {version['description']}")
            print(f"     Status: {version['status']}, Created: {version['created_at'][:10]}")
    
    print("\n3. Comparing versions...")
    if len(history) >= 2:
        comparison = manager.version_manager.compare_versions(
            history[-2]['version_id'],
            history[-1]['version_id']
        )
        if 'error' not in comparison:
            print(f"   Compared {history[-2]['version_number']} vs {history[-1]['version_number']}")
            print(f"   Metadata differences: {len(comparison['differences']['metadata'])}")
    
    print("\n4. Validating latest version...")
    if history:
        validation = manager.version_manager.validate_version(history[-1]['version_id'])
        print(f"   Valid: {validation['valid']}")
        if validation['warnings']:
            print(f"   Warnings: {len(validation['warnings'])}")
        if validation['errors']:
            print(f"   Errors: {len(validation['errors'])}")

def demo_backup_cleanup():
    """Demo backup and cleanup operations"""
    print_section("BACKUP AND MAINTENANCE")
    
    manager = WorkflowManager("/workspace/code/workflows")
    
    print("\n1. Creating system backup...")
    backup_result = manager.backup_workflow_data()
    if backup_result['success']:
        print(f"   ✓ Backup created: {backup_result['backup_path']}")
        print(f"   Size: {backup_result['backup_size_mb']:.2f} MB")
    else:
        print(f"   ✗ Backup failed: {backup_result['error']}")
    
    print("\n2. Cleaning up old data...")
    cleanup_result = manager.cleanup_old_data(days_old=1)  # Clean very old data
    if cleanup_result['success']:
        print(f"   ✓ Cleanup completed")
        print(f"   Removed files: {cleanup_result['removed_files']}")
        print(f"   Cleaned handoffs: {cleanup_result['cleaned_handoffs']}")
    else:
        print(f"   ✗ Cleanup failed: {cleanup_result['error']}")

def simulate_workflow_scenarios():
    """Simulate multiple workflow scenarios"""
    print_section("SIMULATING MULTIPLE WORKFLOW SCENARIOS")
    
    manager = WorkflowManager("/workspace/code/workflows")
    
    scenarios = [
        ("high_confidence_prediction", {"confidence_score": 0.9, "position_size": 50000}),
        ("risk_event", {"risk_level": "high", "emergency": True}),
        ("market_volatility", {"volatility_score": 0.4, "market_hours": True}),
        ("high_confidence_prediction", {"confidence_score": 0.75, "position_size": 200000}),
    ]
    
    created_workflows = []
    
    print(f"\nCreating {len(scenarios)} workflow scenarios...")
    
    for i, (scenario_type, data) in enumerate(scenarios, 1):
        result = manager.create_workflow_scenario(
            scenario_type=scenario_type,
            data=data,
            priority=random.randint(1, 5),
            risk_level=random.choice(["low", "medium", "high"])
        )
        
        if result['success']:
            created_workflows.append(result['workflow_id'])
            print(f"   ✓ Scenario {i}: {scenario_type} -> {result['workflow_id'][:8]}")
        else:
            print(f"   ✗ Scenario {i} failed: {result['error']}")
    
    print(f"\nCreated {len(created_workflows)} workflows successfully")
    return created_workflows

async def main():
    """Main demo function"""
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║  Agent Handoff and Decision-Making Workflow System Demo      ║
║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                  ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Demo individual features
        workflow1 = await demo_high_confidence_scenario()
        workflow2 = await demo_conflict_resolution()
        workflow3 = await demo_escalation()
        
        # Demo analytics and management
        demo_performance_tracking()
        await demo_versioning()
        demo_backup_cleanup()
        
        # Simulate multiple scenarios
        simulate_workflow_scenarios()
        
        # Final system overview
        print_section("FINAL SYSTEM OVERVIEW")
        manager = WorkflowManager("/workspace/code/workflows")
        overview = manager.get_system_overview()
        
        if 'error' not in overview:
            print("\n📊 System Summary:")
            print(f"   • Active Workflows: {overview['workflows']['active_workflows']}")
            print(f"   • Success Rate: {overview['system_health']['workflow_success_rate']:.1%}")
            print(f"   • Conflict Resolution: {overview['system_health']['conflict_resolution_rate']:.1%}")
            print(f"   • Escalation Rate: {overview['system_health']['escalation_rate']:.1%}")
            
            print("\n🎯 Key Features Demonstrated:")
            print("   ✓ Workflow creation and execution")
            print("   ✓ Agent handoff protocols")
            print("   ✓ Conflict detection and resolution")
            print("   ✓ Escalation workflows")
            print("   ✓ Performance tracking")
            print("   ✓ Version management")
            print("   ✓ System monitoring")
            print("   ✓ Backup and maintenance")
        
        print("\n" + "=" * 60)
        print("Demo completed successfully! 🎉")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())