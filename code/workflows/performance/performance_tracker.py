"""
Agent Performance Tracking and Learning Feedback System
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from collections import defaultdict, deque

class PerformanceMetric(Enum):
    """Types of performance metrics"""
    ACCURACY = "accuracy"
    PROFIT_LOSS = "profit_loss"
    RISK_ADJUSTED_RETURN = "risk_adjusted_return"
    EXECUTION_SPEED = "execution_speed"
    DECISION_QUALITY = "decision_quality"
    CONFLICT_RESOLUTION = "conflict_resolution"
    LEARNING_RATE = "learning_rate"

class LearningFeedback(Enum):
    """Types of learning feedback"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CRITICAL = "critical"

@dataclass
class AgentPerformanceSnapshot:
    """Performance snapshot for an agent at a point in time"""
    agent_id: str
    agent_type: str
    timestamp: datetime
    metrics: Dict[str, float]
    decisions_made: int
    successful_decisions: int
    total_return: float
    risk_score: float
    learning_updates: int
    feedback_received: Dict[str, Any]

@dataclass
class LearningFeedbackRecord:
    """Record of learning feedback received"""
    agent_id: str
    scenario_type: str
    decision_id: str
    feedback_type: LearningFeedback
    context: Dict[str, Any]
    impact_score: float
    applied_at: datetime
    effectiveness_rating: float

class AgentPerformanceTracker:
    """Tracks agent performance and manages learning feedback loops"""
    
    def __init__(self, workflows_dir: str = "code/workflows"):
        self.workflows_dir = workflows_dir
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.learning_feedback: List[LearningFeedbackRecord] = []
        self.agent_rankings: Dict[str, Dict[str, float]] = {}
        self.performance_thresholds: Dict[str, Dict[str, float]] = {}
        self.learning_patterns: Dict[str, Dict[str, Any]] = {}
        self.initialize_thresholds()
    
    def initialize_thresholds(self):
        """Initialize performance thresholds for different agent types"""
        self.performance_thresholds = {
            "technical_analyzer": {
                "accuracy": 0.75,
                "execution_speed": 300.0,
                "risk_adjusted_return": 0.15
            },
            "risk_analyzer": {
                "accuracy": 0.85,
                "risk_avoidance": 0.90,
                "profit_loss": 0.05
            },
            "execution_agent": {
                "execution_speed": 60.0,
                "slippage": 0.001,
                "fill_rate": 0.95
            },
            "sentiment_analyzer": {
                "accuracy": 0.70,
                "timeliness": 180.0,
                "correlation_strength": 0.60
            }
        }
    
    def record_agent_decision(self, agent_id: str, agent_type: str, decision: Dict[str, Any],
                            outcome: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Record agent decision and its outcome for performance tracking"""
        
        # Calculate performance metrics for this decision
        metrics = self.calculate_decision_metrics(decision, outcome, context)
        
        # Create performance snapshot
        snapshot = AgentPerformanceSnapshot(
            agent_id=agent_id,
            agent_type=agent_type,
            timestamp=datetime.utcnow(),
            metrics=metrics,
            decisions_made=1,
            successful_decisions=1 if outcome.get('successful', False) else 0,
            total_return=outcome.get('return', 0.0),
            risk_score=context.get('risk_score', 0.0),
            learning_updates=0,
            feedback_received={}
        )
        
        # Add to history
        self.performance_history[agent_id].append(snapshot)
        
        # Generate learning feedback based on outcome
        self.generate_learning_feedback(agent_id, decision, outcome, context)
        
        # Update agent rankings
        self.update_agent_rankings(agent_id, agent_type)
        
        return True
    
    def calculate_decision_metrics(self, decision: Dict[str, Any], 
                                 outcome: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate metrics for a single decision"""
        metrics = {}
        
        # Accuracy metrics
        if 'predicted_value' in decision and 'actual_value' in outcome:
            predicted = decision['predicted_value']
            actual = outcome['actual_value']
            if predicted is not None and actual is not None:
                error = abs(predicted - actual)
                max_value = max(abs(predicted), abs(actual), 1.0)  # Avoid division by zero
                metrics['accuracy'] = 1.0 - (error / max_value)
        
        # Execution speed
        if 'execution_time' in outcome:
            metrics['execution_speed'] = outcome['execution_time']
        
        # Profit/Loss
        if 'return' in outcome:
            metrics['profit_loss'] = outcome['return']
        
        # Risk-adjusted return
        if 'return' in outcome and 'volatility' in context:
            risk_free_rate = 0.02  # Assume 2% risk-free rate
            excess_return = outcome['return'] - risk_free_rate
            if context['volatility'] > 0:
                metrics['risk_adjusted_return'] = excess_return / context['volatility']
        
        # Decision quality score
        quality_score = self.calculate_decision_quality(decision, outcome, context)
        metrics['decision_quality'] = quality_score
        
        return metrics
    
    def calculate_decision_quality(self, decision: Dict[str, Any], 
                                 outcome: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate overall decision quality score"""
        quality_factors = []
        
        # Confidence alignment
        if 'confidence' in decision and 'success' in outcome:
            confidence = decision['confidence']
            success = outcome['success']
            alignment = 1.0 - abs(confidence - (1.0 if success else 0.0))
            quality_factors.append(alignment)
        
        # Timing
        if 'execution_time' in outcome and 'expected_duration' in context:
            actual_time = outcome['execution_time']
            expected_time = context['expected_duration']
            timing_score = min(1.0, expected_time / max(actual_time, 1.0))
            quality_factors.append(timing_score)
        
        # Risk management
        if 'risk_score' in context and 'max_risk' in context:
            actual_risk = context['risk_score']
            max_risk = context['max_risk']
            risk_score = 1.0 - (actual_risk / max(0.01, max_risk))  # Avoid division by zero
            quality_factors.append(risk_score)
        
        return sum(quality_factors) / len(quality_factors) if quality_factors else 0.5
    
    def generate_learning_feedback(self, agent_id: str, decision: Dict[str, Any],
                                 outcome: Dict[str, Any], context: Dict[str, Any]):
        """Generate learning feedback based on decision outcome"""
        
        # Determine feedback type based on outcome
        feedback_type = self.determine_feedback_type(decision, outcome, context)
        
        # Calculate impact score
        impact_score = self.calculate_feedback_impact(decision, outcome, context)
        
        # Create feedback record
        feedback_record = LearningFeedbackRecord(
            agent_id=agent_id,
            scenario_type=context.get('scenario_type', 'unknown'),
            decision_id=decision.get('decision_id', 'unknown'),
            feedback_type=feedback_type,
            context=context,
            impact_score=impact_score,
            applied_at=datetime.utcnow(),
            effectiveness_rating=0.0  # Will be updated later
        )
        
        self.learning_feedback.append(feedback_record)
        
        # Apply feedback to agent learning patterns
        self.update_learning_patterns(agent_id, feedback_record)
    
    def determine_feedback_type(self, decision: Dict[str, Any], outcome: Dict[str, Any],
                              context: Dict[str, Any]) -> LearningFeedback:
        """Determine the type of learning feedback"""
        
        if not outcome.get('successful', False):
            if outcome.get('critical_failure', False):
                return LearningFeedback.CRITICAL
            elif outcome.get('significant_loss', False):
                return LearningFeedback.NEGATIVE
            else:
                return LearningFeedback.NEUTRAL
        
        # Successful outcome
        if decision.get('high_confidence', False) and outcome.get('excellent_result', False):
            return LearningFeedback.POSITIVE
        elif outcome.get('good_result', False):
            return LearningFeedback.POSITIVE
        else:
            return LearningFeedback.NEUTRAL
    
    def calculate_feedback_impact(self, decision: Dict[str, Any], outcome: Dict[str, Any],
                                context: Dict[str, Any]) -> float:
        """Calculate the impact score of the feedback"""
        impact = 0.0
        
        # Financial impact
        if 'return' in outcome:
            return_impact = abs(outcome['return'])
            impact += return_impact * 10  # Scale factor
        
        # Risk impact
        if 'risk_score' in context:
            risk_impact = context['risk_score']
            impact += risk_impact * 5
        
        # Timing impact
        if 'execution_time' in outcome and 'expected_duration' in context:
            timing_error = abs(outcome['execution_time'] - context['expected_duration'])
            impact += timing_error * 0.1
        
        # Confidence-accuracy alignment
        if 'confidence' in decision:
            confidence = decision['confidence']
            success_prob = 1.0 if outcome.get('successful', False) else 0.0
            alignment_error = abs(confidence - success_prob)
            impact += alignment_error * 20
        
        return min(impact, 100.0)  # Cap at 100
    
    def update_learning_patterns(self, agent_id: str, feedback: LearningFeedbackRecord):
        """Update learning patterns based on feedback"""
        
        if agent_id not in self.learning_patterns:
            self.learning_patterns[agent_id] = {
                'positive_feedback_count': 0,
                'negative_feedback_count': 0,
                'critical_feedback_count': 0,
                'average_impact_score': 0.0,
                'learning_velocity': 0.0,
                'improvement_trend': [],
                'scenario_performance': defaultdict(list),
                'last_learning_update': datetime.utcnow()
            }
        
        patterns = self.learning_patterns[agent_id]
        
        # Update feedback counts
        if feedback.feedback_type == LearningFeedback.POSITIVE:
            patterns['positive_feedback_count'] += 1
        elif feedback.feedback_type == LearningFeedback.NEGATIVE:
            patterns['negative_feedback_count'] += 1
        elif feedback.feedback_type == LearningFeedback.CRITICAL:
            patterns['critical_feedback_count'] += 1
        
        # Update average impact score
        total_feedback = (patterns['positive_feedback_count'] + 
                         patterns['negative_feedback_count'] + 
                         patterns['critical_feedback_count'])
        
        if total_feedback > 0:
            current_avg = patterns['average_impact_score']
            new_avg = ((current_avg * (total_feedback - 1)) + feedback.impact_score) / total_feedback
            patterns['average_impact_score'] = new_avg
        
        # Track scenario-specific performance
        scenario = feedback.scenario_type
        patterns['scenario_performance'][scenario].append({
            'feedback_type': feedback.feedback_type.value,
            'impact_score': feedback.impact_score,
            'timestamp': feedback.applied_at
        })
        
        # Update learning velocity (rate of improvement)
        recent_feedback = [f for f in self.learning_feedback 
                         if f.agent_id == agent_id and 
                         (datetime.utcnow() - f.applied_at).days <= 7]
        
        if len(recent_feedback) >= 2:
            positive_recent = len([f for f in recent_feedback if f.feedback_type == LearningFeedback.POSITIVE])
            learning_velocity = positive_recent / len(recent_feedback)
            patterns['learning_velocity'] = learning_velocity
        
        patterns['last_learning_update'] = datetime.utcnow()
    
    def update_agent_rankings(self, agent_id: str, agent_type: str):
        """Update agent rankings based on recent performance"""
        
        # Get recent performance snapshots
        history = self.performance_history[agent_id]
        if not history:
            return
        
        recent_snapshots = list(history)[-20:]  # Last 20 decisions
        
        # Calculate aggregated metrics
        if recent_snapshots:
            avg_accuracy = statistics.mean([s.metrics.get('accuracy', 0.5) for s in recent_snapshots])
            avg_profit_loss = statistics.mean([s.metrics.get('profit_loss', 0.0) for s in recent_snapshots])
            avg_decision_quality = statistics.mean([s.metrics.get('decision_quality', 0.5) for s in recent_snapshots])
            
            # Calculate overall score
            overall_score = (avg_accuracy * 0.4 + 
                           (avg_profit_loss + 1) * 0.3 +  # Normalize profit/loss
                           avg_decision_quality * 0.3)
            
            # Update rankings
            if agent_type not in self.agent_rankings:
                self.agent_rankings[agent_type] = {}
            
            self.agent_rankings[agent_type][agent_id] = overall_score
    
    def get_agent_performance_report(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive performance report for an agent"""
        
        history = list(self.performance_history[agent_id])
        if not history:
            return {'error': 'No performance data available'}
        
        # Filter by time period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_snapshots = [s for s in history if s.timestamp >= cutoff_date]
        
        if not recent_snapshots:
            return {'error': 'No recent performance data'}
        
        # Calculate metrics
        total_decisions = sum(s.decisions_made for s in recent_snapshots)
        successful_decisions = sum(s.successful_decisions for s in recent_snapshots)
        success_rate = successful_decisions / total_decisions if total_decisions > 0 else 0
        
        avg_metrics = {}
        for metric in PerformanceMetric:
            values = [s.metrics.get(metric.value, 0.0) for s in recent_snapshots if metric.value in s.metrics]
            avg_metrics[metric.value] = statistics.mean(values) if values else 0.0
        
        # Get learning patterns
        learning_patterns = self.learning_patterns.get(agent_id, {})
        
        # Performance trends
        trends = self.calculate_performance_trends(recent_snapshots)
        
        # Recommendations
        recommendations = self.generate_performance_recommendations(agent_id, avg_metrics, success_rate)
        
        return {
            'agent_id': agent_id,
            'report_period_days': days,
            'total_decisions': total_decisions,
            'success_rate': success_rate,
            'average_metrics': avg_metrics,
            'learning_patterns': learning_patterns,
            'performance_trends': trends,
            'recommendations': recommendations,
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def calculate_performance_trends(self, snapshots: List[AgentPerformanceSnapshot]) -> Dict[str, Any]:
        """Calculate performance trends over time"""
        
        if len(snapshots) < 2:
            return {'error': 'Insufficient data for trend analysis'}
        
        # Calculate trend for each metric
        trends = {}
        
        for metric in ['accuracy', 'profit_loss', 'decision_quality']:
            values = [s.metrics.get(metric, 0.0) for s in snapshots if metric in s.metrics]
            if len(values) >= 2:
                # Simple linear trend
                n = len(values)
                x = list(range(n))
                x_mean = sum(x) / n
                y_mean = sum(values) / n
                
                numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
                denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
                
                slope = numerator / denominator if denominator != 0 else 0
                
                trends[metric] = {
                    'slope': slope,
                    'direction': 'improving' if slope > 0.01 else 'declining' if slope < -0.01 else 'stable',
                    'strength': abs(slope)
                }
        
        return trends
    
    def generate_performance_recommendations(self, agent_id: str, metrics: Dict[str, float], 
                                           success_rate: float) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Low accuracy recommendations
        if metrics.get('accuracy', 0) < 0.7:
            recommendations.append("Focus on improving prediction accuracy through enhanced feature engineering")
        
        # Poor profit/loss
        if metrics.get('profit_loss', 0) < 0:
            recommendations.append("Review risk management strategies and position sizing")
        
        # Low decision quality
        if metrics.get('decision_quality', 0) < 0.6:
            recommendations.append("Improve decision-making framework with additional validation steps")
        
        # Low success rate
        if success_rate < 0.6:
            recommendations.append("Consider additional training data or model retuning")
        
        # High execution speed but low quality
        if (metrics.get('execution_speed', 999) < 60 and 
            metrics.get('decision_quality', 0) < 0.7):
            recommendations.append("Balance speed with quality - consider adding validation steps")
        
        # Learning patterns analysis
        patterns = self.learning_patterns.get(agent_id, {})
        if patterns.get('critical_feedback_count', 0) > 5:
            recommendations.append("High number of critical errors detected - review safety mechanisms")
        
        if patterns.get('learning_velocity', 0) < 0.3:
            recommendations.append("Learning rate is low - consider adjusting learning parameters")
        
        return recommendations
    
    def get_top_performing_agents(self, agent_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top performing agents by type"""
        
        if agent_type not in self.agent_rankings:
            return []
        
        # Sort by performance score
        rankings = self.agent_rankings[agent_type]
        sorted_agents = sorted(rankings.items(), key=lambda x: x[1], reverse=True)
        
        # Get top performers
        top_agents = []
        for agent_id, score in sorted_agents[:limit]:
            report = self.get_agent_performance_report(agent_id, days=7)
            if 'error' not in report:
                top_agents.append({
                    'agent_id': agent_id,
                    'performance_score': score,
                    'success_rate': report['success_rate'],
                    'avg_metrics': report['average_metrics']
                })
        
        return top_agents
    
    def identify_improvement_areas(self, agent_type: str) -> Dict[str, Any]:
        """Identify common improvement areas for agent type"""
        
        type_agents = [agent_id for agent_id, data in self.performance_history.items() 
                      if data and data[-1].agent_type == agent_type]
        
        if not type_agents:
            return {'error': 'No agents found for this type'}
        
        # Aggregate metrics across all agents of this type
        all_metrics = defaultdict(list)
        for agent_id in type_agents:
            history = list(self.performance_history[agent_id])
            if history:
                recent = history[-10:]  # Last 10 decisions
                for snapshot in recent:
                    for metric, value in snapshot.metrics.items():
                        all_metrics[metric].append(value)
        
        # Calculate averages and identify weak areas
        avg_metrics = {metric: statistics.mean(values) for metric, values in all_metrics.items() if values}
        
        thresholds = self.performance_thresholds.get(agent_type, {})
        
        improvement_areas = []
        for metric, avg_value in avg_metrics.items():
            if metric in thresholds:
                threshold = thresholds[metric]
                if avg_value < threshold:
                    gap = threshold - avg_value
                    improvement_areas.append({
                        'metric': metric,
                        'current_average': avg_value,
                        'threshold': threshold,
                        'improvement_needed': gap,
                        'priority': 'high' if gap > threshold * 0.2 else 'medium'
                    })
        
        return {
            'agent_type': agent_type,
            'total_agents': len(type_agents),
            'average_metrics': avg_metrics,
            'thresholds': thresholds,
            'improvement_areas': sorted(improvement_areas, key=lambda x: x['improvement_needed'], reverse=True)
        }