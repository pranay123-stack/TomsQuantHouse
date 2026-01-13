"""
Conflict Resolution System for Conflicting Agent Recommendations
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict

class ConflictSeverity(Enum):
    """Severity levels for conflicts"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ResolutionStrategy(Enum):
    """Resolution strategies for conflicts"""
    MAJORITY_VOTE = "majority_vote"
    EXPERT_PREFERENCE = "expert_preference"
    WEIGHTED_SCORING = "weighted_scoring"
    HIERARCHY_BASED = "hierarchy_based"
    HUMAN_MEDIATION = "human_mediation"
    TIME_BASED = "time_based"

class ConflictType(Enum):
    """Types of conflicts"""
    ACTION_CONFLICT = "action_conflict"
    TIMING_CONFLICT = "timing_conflict"
    RISK_CONFLICT = "risk_conflict"
    PRIORITY_CONFLICT = "priority_conflict"
    RESOURCE_CONFLICT = "resource_conflict"

@dataclass
class AgentCredential:
    """Agent credentials for conflict resolution"""
    agent_id: str
    agent_type: str
    hierarchy_level: int
    expertise_score: float
    historical_accuracy: float
    specializations: List[str]
    trust_score: float

@dataclass
class ConflictInstance:
    """Instance of a conflict between agents"""
    conflict_id: str
    workflow_id: str
    conflict_type: ConflictType
    severity: ConflictSeverity
    agents_involved: List[str]
    recommendations: List[Dict[str, Any]]
    created_at: datetime
    resolution_strategy: Optional[ResolutionStrategy]
    resolved_at: Optional[datetime]
    resolution: Optional[Dict[str, Any]]

@dataclass
class ResolutionRule:
    """Rule for resolving conflicts"""
    rule_id: str
    name: str
    conflict_type: ConflictType
    strategy: ResolutionStrategy
    conditions: Dict[str, Any]
    agent_credentials: List[AgentCredential]
    priority: int

class ConflictResolutionEngine:
    """Engine for resolving conflicts between agent recommendations"""
    
    def __init__(self, workflows_dir: str = "code/workflows"):
        self.workflows_dir = workflows_dir
        self.active_conflicts: Dict[str, ConflictInstance] = {}
        self.resolution_history: List[ConflictInstance] = []
        self.agent_credentials: Dict[str, AgentCredential] = {}
        self.resolution_rules: Dict[str, ResolutionRule] = {}
        self.performance_cache: Dict[str, float] = {}
        self.load_resolution_rules()
        self.load_agent_credentials()
    
    def load_resolution_rules(self):
        """Load resolution rules from configuration"""
        rules_file = f"{self.workflows_dir}/conflict_resolution/rules.json"
        try:
            with open(rules_file, 'r') as f:
                rules_data = json.load(f)
                
                for rule_data in rules_data.get('rules', []):
                    rule = ResolutionRule(
                        rule_id=rule_data['rule_id'],
                        name=rule_data['name'],
                        conflict_type=ConflictType(rule_data['conflict_type']),
                        strategy=ResolutionStrategy(rule_data['strategy']),
                        conditions=rule_data['conditions'],
                        agent_credentials=[],  # Will be populated from credentials
                        priority=rule_data['priority']
                    )
                    self.resolution_rules[rule.rule_id] = rule
        except FileNotFoundError:
            # Create default rules
            self.create_default_rules()
    
    def load_agent_credentials(self):
        """Load agent credentials from performance data"""
        # In a real implementation, this would load from a database
        # For now, create sample credentials
        sample_credentials = [
            AgentCredential("tech_analyzer_001", "technical_analyzer", 2, 0.85, 0.78, ["technical_analysis", "chart_patterns"], 0.8),
            AgentCredential("risk_analyzer_001", "risk_analyzer", 3, 0.90, 0.85, ["risk_management", "portfolio_optimization"], 0.9),
            AgentCredential("sentiment_001", "sentiment_analyzer", 1, 0.75, 0.72, ["sentiment_analysis", "news_analysis"], 0.7),
            AgentCredential("exec_agent_001", "execution_agent", 2, 0.80, 0.82, ["trade_execution", "order_management"], 0.85),
            AgentCredential("risk_monitor_001", "risk_monitor", 4, 0.95, 0.88, ["risk_monitoring", "emergency_protocols"], 0.95)
        ]
        
        for cred in sample_credentials:
            self.agent_credentials[cred.agent_id] = cred
    
    def create_default_rules(self):
        """Create default resolution rules"""
        default_rules = [
            ResolutionRule(
                rule_id="action_conflict_hierarchy",
                name="Action Conflict - Hierarchy Based",
                conflict_type=ConflictType.ACTION_CONFLICT,
                strategy=ResolutionStrategy.HIERARCHY_BASED,
                conditions={"max_agents": 5, "min_confidence_diff": 0.1},
                agent_credentials=[],
                priority=1
            ),
            ResolutionRule(
                rule_id="risk_conflict_expert",
                name="Risk Conflict - Expert Preference",
                conflict_type=ConflictType.RISK_CONFLICT,
                strategy=ResolutionStrategy.EXPERT_PREFERENCE,
                conditions={"risk_agent_required": True},
                agent_credentials=[],
                priority=1
            ),
            ResolutionRule(
                rule_id="timing_conflict_majority",
                name="Timing Conflict - Majority Vote",
                conflict_type=ConflictType.TIMING_CONFLICT,
                strategy=ResolutionStrategy.MAJORITY_VOTE,
                conditions={"require_consensus": True},
                agent_credentials=[],
                priority=2
            )
        ]
        
        for rule in default_rules:
            self.resolution_rules[rule.rule_id] = rule
    
    def detect_conflicts(self, workflow_id: str, recommendations: List[Dict[str, Any]]) -> List[ConflictInstance]:
        """Detect conflicts between agent recommendations"""
        
        conflicts = []
        
        # Check for different actions
        actions = [rec.get('action') for rec in recommendations]
        if len(set(actions)) > 1:
            action_conflict = self.create_conflict(
                workflow_id=workflow_id,
                conflict_type=ConflictType.ACTION_CONFLICT,
                recommendations=recommendations,
                agents_involved=[rec.get('agent_id') for rec in recommendations]
            )
            conflicts.append(action_conflict)
        
        # Check for timing conflicts
        timing_conflict = self.detect_timing_conflicts(recommendations)
        if timing_conflict:
            conflicts.append(timing_conflict)
        
        # Check for risk conflicts
        risk_levels = [rec.get('risk_assessment') for rec in recommendations]
        if len(set(risk_levels)) > 2:  # More than 2 different risk levels
            risk_conflict = self.create_conflict(
                workflow_id=workflow_id,
                conflict_type=ConflictType.RISK_CONFLICT,
                recommendations=recommendations,
                agents_involved=[rec.get('agent_id') for rec in recommendations]
            )
            conflicts.append(risk_conflict)
        
        # Check for confidence conflicts
        confidence_diff = self.assess_confidence_conflicts(recommendations)
        if confidence_diff > 0.3:
            priority_conflict = self.create_conflict(
                workflow_id=workflow_id,
                conflict_type=ConflictType.PRIORITY_CONFLICT,
                recommendations=recommendations,
                agents_involved=[rec.get('agent_id') for rec in recommendations]
            )
            conflicts.append(priority_conflict)
        
        return conflicts
    
    def detect_timing_conflicts(self, recommendations: List[Dict[str, Any]]) -> Optional[ConflictInstance]:
        """Detect timing-related conflicts"""
        timing_fields = ['execution_time', 'timeout_seconds', 'urgency_level']
        
        for field in timing_fields:
            values = [rec.get(field) for rec in recommendations if field in rec]
            if len(set(values)) > 1:
                # Significant timing difference detected
                return ConflictInstance(
                    conflict_id=f"timing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    workflow_id=recommendations[0].get('workflow_id', 'unknown'),
                    conflict_type=ConflictType.TIMING_CONFLICT,
                    severity=ConflictSeverity.MEDIUM,
                    agents_involved=[rec.get('agent_id') for rec in recommendations],
                    recommendations=recommendations,
                    created_at=datetime.utcnow(),
                    resolution_strategy=None,
                    resolved_at=None,
                    resolution=None
                )
        
        return None
    
    def assess_confidence_conflicts(self, recommendations: List[Dict[str, Any]]) -> float:
        """Assess confidence conflicts between recommendations"""
        confidences = [rec.get('confidence', 0.5) for rec in recommendations]
        
        if len(confidences) < 2:
            return 0.0
        
        # Calculate standard deviation of confidence scores
        mean_confidence = sum(confidences) / len(confidences)
        variance = sum((c - mean_confidence) ** 2 for c in confidences) / len(confidences)
        std_dev = variance ** 0.5
        
        return std_dev
    
    def create_conflict(self, workflow_id: str, conflict_type: ConflictType,
                       recommendations: List[Dict[str, Any]], agents_involved: List[str]) -> ConflictInstance:
        """Create a conflict instance"""
        
        conflict_id = f"conflict_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(self.active_conflicts)}"
        
        # Assess severity
        severity = self.assess_conflict_severity(conflict_type, recommendations)
        
        conflict = ConflictInstance(
            conflict_id=conflict_id,
            workflow_id=workflow_id,
            conflict_type=conflict_type,
            severity=severity,
            agents_involved=agents_involved,
            recommendations=recommendations,
            created_at=datetime.utcnow(),
            resolution_strategy=None,
            resolved_at=None,
            resolution=None
        )
        
        self.active_conflicts[conflict_id] = conflict
        return conflict
    
    def assess_conflict_severity(self, conflict_type: ConflictType, 
                               recommendations: List[Dict[str, Any]]) -> ConflictSeverity:
        """Assess the severity of a conflict"""
        
        # High severity factors
        high_severity_factors = [
            any(rec.get('risk_assessment') == 'high' for rec in recommendations),
            any(rec.get('confidence', 0) < 0.3 for rec in recommendations),
            len(recommendations) > 3,
            any(rec.get('position_size', 0) > 1000000 for rec in recommendations)
        ]
        
        # Critical severity factors
        critical_factors = [
            any(rec.get('risk_assessment') == 'critical' for rec in recommendations),
            any(rec.get('emergency', False) for rec in recommendations)
        ]
        
        if any(critical_factors):
            return ConflictSeverity.CRITICAL
        elif sum(high_severity_factors) >= 2:
            return ConflictSeverity.HIGH
        elif sum(high_severity_factors) >= 1:
            return ConflictSeverity.MEDIUM
        else:
            return ConflictSeverity.LOW
    
    async def resolve_conflict(self, conflict_id: str) -> Dict[str, Any]:
        """Resolve a conflict using appropriate strategy"""
        
        if conflict_id not in self.active_conflicts:
            return {'error': 'Conflict not found'}
        
        conflict = self.active_conflicts[conflict_id]
        
        # Select resolution strategy
        strategy = self.select_resolution_strategy(conflict)
        conflict.resolution_strategy = strategy
        
        # Execute resolution
        resolution_result = await self.execute_resolution(conflict, strategy)
        
        # Update conflict
        conflict.resolved_at = datetime.utcnow()
        conflict.resolution = resolution_result
        
        # Move to history
        self.resolution_history.append(conflict)
        del self.active_conflicts[conflict_id]
        
        return resolution_result
    
    def select_resolution_strategy(self, conflict: ConflictInstance) -> ResolutionStrategy:
        """Select the best resolution strategy for a conflict"""
        
        # Find applicable rules
        applicable_rules = [rule for rule in self.resolution_rules.values() 
                          if rule.conflict_type == conflict.conflict_type]
        
        if not applicable_rules:
            # Default strategies based on conflict type
            default_strategies = {
                ConflictType.ACTION_CONFLICT: ResolutionStrategy.WEIGHTED_SCORING,
                ConflictType.RISK_CONFLICT: ResolutionStrategy.EXPERT_PREFERENCE,
                ConflictType.TIMING_CONFLICT: ResolutionStrategy.MAJORITY_VOTE,
                ConflictType.PRIORITY_CONFLICT: ResolutionStrategy.HIERARCHY_BASED,
                ConflictType.RESOURCE_CONFLICT: ResolutionStrategy.HUMAN_MEDIATION
            }
            return default_strategies.get(conflict.conflict_type, ResolutionStrategy.WEIGHTED_SCORING)
        
        # Select highest priority rule
        best_rule = max(applicable_rules, key=lambda x: x.priority)
        return best_rule.strategy
    
    async def execute_resolution(self, conflict: ConflictInstance, 
                               strategy: ResolutionStrategy) -> Dict[str, Any]:
        """Execute the resolution strategy"""
        
        if strategy == ResolutionStrategy.MAJORITY_VOTE:
            return await self.resolve_by_majority_vote(conflict)
        elif strategy == ResolutionStrategy.EXPERT_PREFERENCE:
            return await self.resolve_by_expert_preference(conflict)
        elif strategy == ResolutionStrategy.WEIGHTED_SCORING:
            return await self.resolve_by_weighted_scoring(conflict)
        elif strategy == ResolutionStrategy.HIERARCHY_BASED:
            return await self.resolve_by_hierarchy(conflict)
        elif strategy == ResolutionStrategy.HUMAN_MEDIATION:
            return await self.resolve_by_human_mediation(conflict)
        else:  # TIME_BASED
            return await self.resolve_by_time_based(conflict)
    
    async def resolve_by_majority_vote(self, conflict: ConflictInstance) -> Dict[str, Any]:
        """Resolve conflict by majority vote"""
        
        # Count votes for each action
        action_votes = defaultdict(int)
        for rec in conflict.recommendations:
            action = rec.get('action', 'unknown')
            confidence = rec.get('confidence', 0.5)
            # Weight vote by confidence
            action_votes[action] += confidence
        
        # Select winning action
        winning_action = max(action_votes.items(), key=lambda x: x[1])
        
        return {
            'strategy': strategy.value,
            'winning_action': winning_action[0],
            'vote_count': dict(action_votes),
            'margin': winning_action[1] - max(v for k, v in action_votes.items() if k != winning_action[0]),
            'confidence_in_resolution': winning_action[1] / sum(action_votes.values()) if sum(action_votes.values()) > 0 else 0
        }
    
    async def resolve_by_expert_preference(self, conflict: ConflictInstance) -> Dict[str, Any]:
        """Resolve conflict by giving preference to expert agents"""
        
        # Find risk analyzer or highest hierarchy agent
        best_agent = None
        best_score = 0
        
        for rec in conflict.recommendations:
            agent_id = rec.get('agent_id')
            if agent_id in self.agent_credentials:
                cred = self.agent_credentials[agent_id]
                # Score based on hierarchy level, expertise, and trust
                score = (cred.hierarchy_level * 0.4 + 
                        cred.expertise_score * 0.3 + 
                        cred.trust_score * 0.3)
                
                if score > best_score:
                    best_score = score
                    best_agent = agent_id
        
        # Find recommendation from best agent
        best_recommendation = None
        if best_agent:
            for rec in conflict.recommendations:
                if rec.get('agent_id') == best_agent:
                    best_recommendation = rec
                    break
        
        return {
            'strategy': ResolutionStrategy.EXPERT_PREFERENCE.value,
            'selected_agent': best_agent,
            'selected_recommendation': best_recommendation,
            'expert_score': best_score,
            'reasoning': f"Selected based on agent hierarchy and expertise"
        }
    
    async def resolve_by_weighted_scoring(self, conflict: ConflictInstance) -> Dict[str, Any]:
        """Resolve conflict by weighted scoring of recommendations"""
        
        scored_recommendations = []
        
        for rec in conflict.recommendations:
            agent_id = rec.get('agent_id')
            confidence = rec.get('confidence', 0.5)
            action = rec.get('action', 'unknown')
            
            # Calculate weighted score
            score_components = {
                'confidence': confidence,
                'agent_expertise': self.get_agent_expertise_score(agent_id),
                'historical_accuracy': self.get_agent_accuracy_score(agent_id),
                'risk_appropriateness': self.calculate_risk_score(rec)
            }
            
            # Weights for different components
            weights = {'confidence': 0.3, 'agent_expertise': 0.25, 
                      'historical_accuracy': 0.25, 'risk_appropriateness': 0.2}
            
            weighted_score = sum(score_components[key] * weights[key] for key in weights)
            
            scored_recommendations.append({
                'recommendation': rec,
                'weighted_score': weighted_score,
                'score_components': score_components
            })
        
        # Select best scoring recommendation
        best = max(scored_recommendations, key=lambda x: x['weighted_score'])
        
        return {
            'strategy': ResolutionStrategy.WEIGHTED_SCORING.value,
            'selected_recommendation': best['recommendation'],
            'score': best['weighted_score'],
            'all_scores': [(r['recommendation']['action'], r['weighted_score']) 
                          for r in scored_recommendations],
            'score_breakdown': best['score_components']
        }
    
    async def resolve_by_hierarchy(self, conflict: ConflictInstance) -> Dict[str, Any]:
        """Resolve conflict based on agent hierarchy"""
        
        # Sort agents by hierarchy level (higher is better)
        agent_scores = []
        
        for rec in conflict.recommendations:
            agent_id = rec.get('agent_id')
            if agent_id in self.agent_credentials:
                cred = self.agent_credentials[agent_id]
                # Hierarchy score (inverted - lower level number is higher priority)
                hierarchy_score = 10 - cred.hierarchy_level
                agent_scores.append((rec, hierarchy_score, agent_id))
        
        # Select highest hierarchy agent
        if agent_scores:
            best = max(agent_scores, key=lambda x: x[1])
            return {
                'strategy': ResolutionStrategy.HIERARCHY_BASED.value,
                'selected_recommendation': best[0],
                'selected_agent': best[2],
                'hierarchy_level': 10 - best[1],
                'reasoning': "Selected based on organizational hierarchy"
            }
        
        # Fallback to weighted scoring
        return await self.resolve_by_weighted_scoring(conflict)
    
    async def resolve_by_human_mediation(self, conflict: ConflictInstance) -> Dict[str, Any]:
        """Resolve conflict through human mediation (simulated)"""
        
        # In a real implementation, this would trigger human intervention
        # For simulation, we'll create a structured mediation process
        
        mediation_request = {
            'conflict_id': conflict.conflict_id,
            'conflict_type': conflict.conflict_type.value,
            'recommendations': conflict.recommendations,
            'agents_involved': conflict.agents_involved,
            'created_at': conflict.created_at.isoformat(),
            'mediation_required': True
        }
        
        # Simulate human decision (in reality, this would be a human input)
        # For now, select the recommendation with highest confidence
        best_rec = max(conflict.recommendations, key=lambda x: x.get('confidence', 0))
        
        return {
            'strategy': ResolutionStrategy.HUMAN_MEDIATION.value,
            'selected_recommendation': best_rec,
            'mediation_request': mediation_request,
            'human_decision': True,
            'decision_rationale': "Human-mediated resolution based on comprehensive analysis"
        }
    
    async def resolve_by_time_based(self, conflict: ConflictInstance) -> Dict[str, Any]:
        """Resolve conflict based on timing considerations"""
        
        # For time-based resolution, prioritize newer recommendations
        # or recommendations with specific timing requirements
        
        timed_recommendations = []
        for rec in conflict.recommendations:
            urgency = rec.get('urgency_level', 1)
            execution_time = rec.get('execution_time', 3600)
            
            # Score based on urgency and time sensitivity
            time_score = urgency * 10 + (1 / max(execution_time, 1))
            timed_recommendations.append((rec, time_score))
        
        best = max(timed_recommendations, key=lambda x: x[1])
        
        return {
            'strategy': ResolutionStrategy.TIME_BASED.value,
            'selected_recommendation': best[0],
            'time_score': best[1],
            'reasoning': "Selected based on timing urgency and sensitivity"
        }
    
    def get_agent_expertise_score(self, agent_id: str) -> float:
        """Get agent expertise score"""
        if agent_id in self.agent_credentials:
            return self.agent_credentials[agent_id].expertise_score
        return 0.5  # Default score
    
    def get_agent_accuracy_score(self, agent_id: str) -> float:
        """Get agent historical accuracy score"""
        if agent_id in self.agent_credentials:
            return self.agent_credentials[agent_id].historical_accuracy
        return 0.5  # Default score
    
    def calculate_risk_score(self, recommendation: Dict[str, Any]) -> float:
        """Calculate risk appropriateness score for recommendation"""
        risk_assessment = recommendation.get('risk_assessment', 'medium')
        confidence = recommendation.get('confidence', 0.5)
        
        # Risk-appropriate if confidence is high for risk level
        risk_mapping = {'low': 0.2, 'medium': 0.5, 'high': 0.7, 'critical': 0.9}
        expected_confidence = risk_mapping.get(risk_assessment, 0.5)
        
        # Score based on confidence alignment with risk level
        alignment = 1.0 - abs(confidence - expected_confidence)
        return alignment
    
    def get_conflict_metrics(self) -> Dict[str, Any]:
        """Get conflict resolution metrics"""
        total_conflicts = len(self.resolution_history)
        
        if total_conflicts == 0:
            return {'error': 'No conflicts resolved yet'}
        
        # Success rate by strategy
        strategy_success = defaultdict(lambda: {'total': 0, 'successful': 0})
        conflict_types = defaultdict(int)
        severities = defaultdict(int)
        avg_resolution_time = 0
        
        for conflict in self.resolution_history:
            strategy = conflict.resolution_strategy.value if conflict.resolution_strategy else 'unknown'
            strategy_success[strategy]['total'] += 1
            conflict_types[conflict.conflict_type.value] += 1
            severities[conflict.severity.value] += 1
            
            # Calculate resolution time
            if conflict.resolved_at:
                resolution_time = (conflict.resolved_at - conflict.created_at).total_seconds()
                avg_resolution_time += resolution_time
        
        avg_resolution_time /= total_conflicts
        
        # Calculate success rates
        for strategy, stats in strategy_success.items():
            if stats['total'] > 0:
                # In a real implementation, we'd track actual success/failure
                stats['success_rate'] = 0.85  # Simulated success rate
        
        return {
            'total_conflicts': total_conflicts,
            'conflict_types': dict(conflict_types),
            'severity_distribution': dict(severities),
            'strategy_distribution': {k: v['total'] for k, v in strategy_success.items()},
            'average_resolution_time_seconds': avg_resolution_time,
            'strategy_success_rates': {k: v.get('success_rate', 0) for k, v in strategy_success.items()}
        }