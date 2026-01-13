# Agent Handoff and Decision-Making Workflow System

A comprehensive workflow system for coordinating trading agents, managing decision-making processes, and handling conflicts and escalations in automated trading environments.

## Overview

This system provides a complete framework for managing complex trading workflows with multiple agents, including:

- **Workflow Templates**: Pre-built templates for common trading scenarios
- **Agent Handoff Protocols**: Context-preserving agent transitions
- **Decision Trees**: Automated vs. human decision routing
- **Performance Tracking**: Agent performance monitoring and learning
- **Conflict Resolution**: Intelligent resolution of conflicting recommendations
- **Escalation Workflows**: Automated escalation for critical decisions
- **Version Management**: Workflow versioning with rollback capabilities

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Manager                         │
│                    (Main Interface)                         │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐   ┌──────────▼─────────┐   ┌──────▼──────┐
│  Workflow    │   │   Agent Handoff    │   │ Performance │
│   Engine     │   │    Manager         │   │  Tracker    │
└──────────────┘   └────────────────────┘   └─────────────┘
        │                     │                     │
        │                     │                     │
┌───────▼──────┐   ┌──────────▼─────────┐   ┌──────▼──────┐
│   Conflict   │   │    Escalation      │   │   Version   │
│  Resolver    │   │    Manager         │   │  Manager    │
└──────────────┘   └────────────────────┘   └─────────────┘
```

## Directory Structure

```
code/workflows/
├── templates/                    # Workflow scenario templates
│   ├── high_confidence_prediction.json
│   ├── risk_event.json
│   └── market_volatility.json
├── protocols/                    # Agent handoff protocols
│   └── handoff_manager.py
├── decision_trees/              # Decision routing trees
│   ├── decision_routing.json
│   └── trade_execution.json
├── performance/                 # Performance tracking
│   └── performance_tracker.py
├── conflict_resolution/         # Conflict resolution
│   ├── conflict_engine.py
│   └── rules.json
├── escalation/                  # Escalation workflows
│   ├── escalation_manager.py
│   └── rules.json
├── versioning/                  # Version management
│   └── version_manager.py
├── management/                  # Management tools
│   └── workflow_manager.py
├── archive/                     # Completed workflows
├── backups/                     # System backups
├── base_engine.py              # Core workflow engine
├── system_config.json          # System configuration
└── README.md                   # This file
```

## Quick Start

### 1. Basic Usage

```python
from workflows.management.workflow_manager import WorkflowManager

# Initialize the workflow system
manager = WorkflowManager("code/workflows")

# Create a high-confidence trading workflow
result = manager.create_workflow_scenario(
    scenario_type="high_confidence_prediction",
    data={
        "symbol": "AAPL",
        "action": "buy",
        "confidence_score": 0.85,
        "position_size": 100000
    },
    priority=2,
    risk_level="medium"
)

print(f"Created workflow: {result['workflow_id']}")
```

### 2. Execute Workflow Steps

```python
# Execute a step with an agent
result = manager.execute_workflow_step(
    workflow_id="workflow_123",
    agent_type="technical_analyzer",
    agent_id="tech_analyzer_001",
    decision_data={
        "action": "analyze",
        "confidence": 0.8,
        "reasoning": "Strong technical indicators",
        "risk_assessment": "medium",
        "outcome": {"successful": True, "return": 0.02}
    }
)
```

### 3. Monitor Workflow Progress

```python
# Get workflow dashboard
dashboard = manager.get_workflow_dashboard("workflow_123")
print(f"Status: {dashboard['workflow_status']['state']}")
print(f"Needs attention: {dashboard['needs_attention']}")
```

## Workflow Templates

### High Confidence Prediction
For trades with high confidence scores (>0.8):
- Automated execution with minimal human intervention
- Fast handoffs between technical and execution agents
- Continuous monitoring and performance tracking

### Risk Event
For critical market risk events:
- Immediate escalation to senior management
- Emergency protocols and protective measures
- Human oversight at key decision points

### Market Volatility
For high volatility periods:
- Adaptive position sizing
- Enhanced monitoring
- Dynamic strategy adjustment

## Agent Types

| Agent Type | Purpose | Typical Actions |
|------------|---------|-----------------|
| `technical_analyzer` | Technical market analysis | Chart patterns, indicators, signals |
| `risk_analyzer` | Risk assessment and management | Position sizing, risk metrics |
| `execution_agent` | Trade execution | Order placement, execution timing |
| `sentiment_analyzer` | Market sentiment analysis | News sentiment, social media |
| `monitor_agent` | Continuous monitoring | Performance tracking, alerts |

## Decision Trees

The system uses decision trees to automatically route decisions:

1. **Risk-based Routing**: Critical risks require human approval
2. **Confidence-based**: High confidence allows automation
3. **Position Size**: Large positions trigger escalations
4. **Market Conditions**: Volatility affects routing decisions

### Example Decision Flow

```
Start → Check Risk Level
       ↓
    Critical? → Human Required
       ↓
    No → Check Confidence Score
       ↓
    High (>0.9)? → Automated
       ↓
    Medium (0.7-0.9)? → Standard Process
       ↓
    Low (<0.7)? → Human Review
```

## Conflict Resolution

The system automatically detects and resolves conflicts:

### Conflict Types
- **Action Conflicts**: Agents recommend different actions
- **Timing Conflicts**: Disagreement on execution timing
- **Risk Conflicts**: Different risk assessments
- **Priority Conflicts**: Conflicting priority levels

### Resolution Strategies
1. **Majority Vote**: Most agents agree on action
2. **Expert Preference**: Defer to specialized agents
3. **Weighted Scoring**: Score based on confidence and expertise
4. **Hierarchy-based**: Follow organizational hierarchy
5. **Human Mediation**: Manual intervention when needed

## Escalation System

### Escalation Levels
1. **Level 1**: Supervisor Review (15 min timeout)
2. **Level 2**: Manager Approval (10 min timeout)
3. **Level 3**: Senior Management (5 min timeout)
4. **Level 4**: Executive Escalation (3 min timeout)

### Triggers
- Financial loss > 5%
- Critical risk levels
- Large positions > $5M
- Consecutive failures
- Volatility spikes

### Notifications
- Email, SMS, dashboard alerts
- Phone calls for critical issues
- Emergency broadcasts for Level 4

## Performance Tracking

### Metrics Tracked
- **Accuracy**: Prediction accuracy rates
- **Execution Speed**: Time to complete actions
- **Risk-Adjusted Returns**: Return vs. risk metrics
- **Decision Quality**: Overall decision effectiveness
- **Learning Rate**: Improvement over time

### Performance Reports
```python
# Get agent performance report
report = manager.performance_tracker.get_agent_performance_report(
    agent_id="tech_analyzer_001", 
    days=30
)

print(f"Success Rate: {report['success_rate']:.2%}")
print(f"Average Metrics: {report['average_metrics']}")
```

## Version Management

### Version Control
- Automatic versioning of workflow templates
- Detailed change tracking
- Checksum validation for integrity
- Rollback capabilities with checkpoints

### Creating New Versions
```python
# Create new version
version_id = manager.version_manager.create_new_version(
    template_file="templates/high_confidence_prediction.json",
    version_description="Added new risk controls",
    changes=["Added stop-loss validation", "Enhanced monitoring"],
    created_by="john_doe"
)

# Activate version
manager.version_manager.activate_version(version_id)
```

### Rollback
```python
# Rollback to previous version
rollback_id = manager.version_manager.rollback_to_version(
    version_id="high_confidence_prediction_v1.0",
    reason=RollbackReason.CRITICAL_BUG,
    initiated_by="john_doe",
    description="Critical bug in risk calculation"
)
```

## CLI Management Tools

### Command Line Interface

```bash
# Create workflow
python -m workflows.management.workflow_manager create high_confidence_prediction \
  --data '{"symbol": "AAPL", "action": "buy"}' --priority 2

# Execute workflow step
python -m workflows.management.workflow_manager execute workflow_123 \
  technical_analyzer tech_analyzer_001 \
  --decision-data '{"action": "analyze", "confidence": 0.8}'

# Get dashboard
python -m workflows.management.workflow_manager dashboard workflow_123

# System overview
python -m workflows.management.workflow_manager overview

# Backup data
python -m workflows.management.workflow_manager backup --path backup.json

# Cleanup old data
python -m workflows.management.workflow_manager cleanup --days 30
```

## Configuration

The system is configured via `system_config.json`:

### Key Settings
- **Agent Configuration**: Timeout, retry limits, confidence thresholds
- **Escalation Rules**: Triggers, timeouts, notification channels
- **Performance Thresholds**: Minimum acceptable performance levels
- **Security Settings**: Authentication, encryption, audit logging

### Customization
```json
{
  "performance_thresholds": {
    "technical_analyzer": {
      "accuracy": 0.80,        // Minimum 80% accuracy
      "execution_speed": 200.0 // Max 200 seconds
    }
  },
  "escalation_config": {
    "max_escalation_level": 4,
    "notification_channels": ["email", "sms", "dashboard"]
  }
}
```

## Monitoring and Alerts

### Real-time Monitoring
- Workflow execution status
- Agent performance metrics
- Conflict and escalation tracking
- System health indicators

### Alerting
- Critical errors: Immediate phone/SMS
- Performance degradation: Email alerts
- Security events: Audit logging
- Capacity thresholds: Dashboard notifications

## Best Practices

### Workflow Design
1. **Keep workflows focused**: Each template should handle one scenario
2. **Use appropriate timeouts**: Balance speed vs. safety
3. **Define clear success criteria**: What constitutes completion
4. **Plan for failures**: Include retry and rollback logic

### Agent Development
1. **Consistent interfaces**: All agents should follow same API
2. **Meaningful confidence scores**: Reflect actual certainty
3. **Rich context data**: Provide supporting information
4. **Proper error handling**: Return detailed error messages

### Conflict Resolution
1. **Use appropriate strategies**: Match strategy to conflict type
2. **Monitor resolution quality**: Track success rates
3. **Tune thresholds**: Adjust based on false positive/negative rates
4. **Human oversight**: Define when manual intervention is needed

### Escalation Management
1. **Clear trigger conditions**: Well-defined escalation triggers
2. **Appropriate timeouts**: Balance urgency vs. thoroughness
3. **Contact hierarchy**: Define escalation paths clearly
4. **Notification redundancy**: Multiple channels for critical alerts

## Troubleshooting

### Common Issues

#### Workflow Stuck in Pending
```python
# Check workflow status
status = manager.workflow_engine.get_workflow_status(workflow_id)
print(status)

# Check for escalation triggers
if status['should_escalate']:
    print("Workflow requires escalation")
```

#### High Conflict Rate
```python
# Analyze conflict patterns
metrics = manager.conflict_engine.get_conflict_metrics()
print(f"Conflict rate: {metrics['conflict_rate']:.2%}")

# Review conflict types
print("Conflict distribution:", metrics['conflict_types'])
```

#### Performance Degradation
```python
# Get performance trends
report = manager.performance_tracker.get_agent_performance_report(agent_id)
trends = report['performance_trends']
for metric, trend in trends.items():
    if trend['direction'] == 'declining':
        print(f"Declining metric: {metric}")
```

### Debug Mode
Enable debug logging:
```python
import logging
logging.getLogger('workflow_engine').setLevel(logging.DEBUG)
```

### Testing Mode
Use simulation mode for testing:
```json
{
  "testing": {
    "enable_simulation_mode": true,
    "simulation_probabilities": {
      "agent_success": 0.95,
      "conflict_occurrence": 0.05
    }
  }
}
```

## API Reference

### WorkflowManager Methods

#### `create_workflow_scenario()`
Create a new workflow from template.

**Parameters:**
- `scenario_type` (str): Template ID
- `data` (dict): Initial workflow data
- `priority` (int): Priority level (1-5)
- `risk_level` (str): Risk level (low, medium, high, critical)

**Returns:** Workflow creation result

#### `execute_workflow_step()`
Execute a step in a workflow.

**Parameters:**
- `workflow_id` (str): Workflow identifier
- `agent_type` (str): Type of agent executing
- `agent_id` (str): Agent identifier
- `decision_data` (dict): Decision information

**Returns:** Execution result

#### `get_workflow_dashboard()`
Get comprehensive workflow status.

**Parameters:**
- `workflow_id` (str): Workflow identifier

**Returns:** Dashboard data

#### `resolve_conflicts()`
Resolve conflicts in a workflow.

**Parameters:**
- `workflow_id` (str): Workflow identifier

**Returns:** Resolution results

#### `trigger_escalation()`
Trigger escalation for a workflow.

**Parameters:**
- `workflow_id` (str): Workflow identifier
- `trigger_data` (dict): Escalation trigger information

**Returns:** Escalation result

### Event Handlers

Implement custom event handlers:

```python
def custom_escalation_handler(event_data):
    # Custom escalation logic
    if event_data['severity'] == 'critical':
        send_emergency_alert(event_data)

# Register handler
manager.escalation_manager.add_event_handler('escalation', custom_escalation_handler)
```

## Security Considerations

### Authentication
- All agents must authenticate before execution
- API keys for external integrations
- Role-based access control

### Audit Logging
- All workflow actions logged
- Immutable audit trail
- Compliance reporting

### Data Protection
- Sensitive data encryption at rest
- Secure communication channels
- Data retention policies

## Contributing

### Adding New Templates
1. Create JSON template in `templates/`
2. Define steps, conditions, and actions
3. Add to system configuration
4. Test with CLI tools

### Adding New Agents
1. Implement agent interface
2. Register in agent configuration
3. Add performance metrics
4. Test handoff protocols

### Extending Decision Trees
1. Add tree definition to `decision_trees/`
2. Define conditions and routing logic
3. Update decision evaluation
4. Test edge cases

## License

This system is provided for educational and research purposes. See LICENSE file for details.

## Support

For questions and support:
- Review this README and API documentation
- Check the troubleshooting section
- Examine example workflows in templates/
- Use CLI tools for debugging and monitoring

---

*System created on 2025-11-02 for comprehensive agent handoff and decision-making workflows*