"""
Trading Workflow Nodes
Individual nodes for the LangGraph trading workflow
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import asdict

from ..workflows.state import (
    WorkflowState, MarketData, MLPrediction, MLFeatures, RiskAssessment,
    ExecutionOrder, NodeResult, DecisionOutcome, RiskLevel, MarketCondition
)

logger = logging.getLogger(__name__)

class MarketAnalysisNode:
    """Node for market data analysis and condition assessment"""
    
    def __init__(self, data_source=None):
        self.data_source = data_source
        
    def execute(self, state: WorkflowState) -> NodeResult:
        """
        Analyze current market data and determine market condition
        
        Args:
            state: Current workflow state
            
        Returns:
            NodeResult: Analysis result with market condition
        """
        try:
            # If no market data, simulate or fetch it
            if not state.market_data:
                market_data = self._fetch_market_data(state)
            else:
                market_data = state.market_data
            
            # Analyze market condition
            market_condition = self._analyze_market_condition(market_data)
            
            # Update portfolio context
            portfolio_context = self._analyze_portfolio_context(state, market_data)
            
            # Prepare result data
            result_data = {
                "market_data": asdict(market_data),
                "market_condition": market_condition.value,
                "portfolio_context": portfolio_context,
                "analysis_timestamp": datetime.now().isoformat(),
                "key_metrics": self._calculate_key_metrics(market_data)
            }
            
            # Update state
            state.market_data = market_data
            state.market_condition = market_condition
            state.portfolio_context = portfolio_context
            state.current_node = "market_analysis"
            
            logger.info(f"Market analysis completed for {market_data.symbol}")
            
            return NodeResult(
                node_name="market_analysis",
                success=True,
                data=result_data,
                next_node="ml_prediction"
            )
            
        except Exception as e:
            error_msg = f"Market analysis failed: {str(e)}"
            logger.error(error_msg)
            state.error_log.append(error_msg)
            
            return NodeResult(
                node_name="market_analysis",
                success=False,
                error=error_msg,
                next_node="error_handling"
            )
    
    def _fetch_market_data(self, state: WorkflowState) -> MarketData:
        """Fetch or simulate market data"""
        # In real implementation, this would connect to market data APIs
        # For now, simulate realistic market data
        
        import random
        import time
        
        symbol = state.metadata.get("symbol", "BTCUSDT")
        base_price = 45000.0 if "BTC" in symbol else 2500.0
        
        # Simulate price movement
        price_change = random.uniform(-0.05, 0.05)
        current_price = base_price * (1 + price_change)
        
        return MarketData(
            symbol=symbol,
            price=current_price,
            volume=random.uniform(1000000, 10000000),
            timestamp=datetime.now(),
            high_24h=current_price * random.uniform(1.01, 1.05),
            low_24h=current_price * random.uniform(0.95, 0.99),
            change_24h=price_change * base_price,
            change_percent_24h=price_change * 100
        )
    
    def _analyze_market_condition(self, market_data: MarketData) -> MarketCondition:
        """Analyze market condition based on data"""
        change_percent = market_data.change_percent_24h
        
        if abs(change_percent) > 3:
            return MarketCondition.VOLATILE
        elif change_percent > 2:
            return MarketCondition.BULLISH
        elif change_percent < -2:
            return MarketCondition.BEARISH
        else:
            return MarketCondition.SIDEWAYS
    
    def _analyze_portfolio_context(self, state: WorkflowState, market_data: MarketData) -> Dict[str, Any]:
        """Analyze current portfolio context"""
        # Get existing portfolio from metadata or state
        portfolio = state.metadata.get("portfolio", {})
        
        # Calculate current exposure
        current_exposure = portfolio.get("total_exposure", 0.0)
        available_balance = portfolio.get("available_balance", 10000.0)
        
        return {
            "current_exposure": current_exposure,
            "available_balance": available_balance,
            "position_count": len(portfolio.get("positions", [])),
            "largest_position": max([p.get("size", 0) for p in portfolio.get("positions", [])], default=0),
            "sector_exposure": portfolio.get("sector_exposure", {}),
            "risk_metrics": {
                "var_95": 0.02,  # 2% Value at Risk
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.05
            }
        }
    
    def _calculate_key_metrics(self, market_data: MarketData) -> Dict[str, float]:
        """Calculate key market metrics"""
        change_pct = abs(market_data.change_percent_24h)
        
        return {
            "volatility_index": min(change_pct / 10, 1.0),
            "liquidity_score": min(market_data.volume / 1000000, 1.0),
            "momentum_score": market_data.change_percent_24h / 100,
            "volume_trend": 1.0 if market_data.volume > 5000000 else 0.5
        }


class MLPredictionNode:
    """Node for ML model predictions"""
    
    def __init__(self, model_registry=None):
        self.model_registry = model_registry
        self.default_model = "ensemble_v2"
        
    def execute(self, state: WorkflowState) -> NodeResult:
        """
        Generate ML predictions based on market data and features
        
        Args:
            state: Current workflow state
            
        Returns:
            NodeResult: ML prediction result
        """
        try:
            if not state.market_data:
                raise ValueError("Market data required for ML prediction")
            
            # Generate ML features
            features = self._generate_ml_features(state)
            
            # Get ML prediction
            prediction = self._generate_prediction(state, features)
            
            # Calculate prediction confidence
            confidence = self._calculate_prediction_confidence(prediction, state)
            
            # Prepare result data
            result_data = {
                "prediction": asdict(prediction),
                "confidence": confidence,
                "model_version": self.default_model,
                "features": asdict(features),
                "prediction_timestamp": datetime.now().isoformat(),
                "risk_factors": self._identify_risk_factors(prediction, state)
            }
            
            # Update state
            state.ml_prediction = prediction
            state.prediction_confidence = confidence
            state.model_version = self.default_model
            
            logger.info(f"ML prediction generated: {prediction.decision.value} with confidence {confidence:.2f}")
            
            return NodeResult(
                node_name="ml_prediction",
                success=True,
                data=result_data,
                next_node="risk_management"
            )
            
        except Exception as e:
            error_msg = f"ML prediction failed: {str(e)}"
            logger.error(error_msg)
            state.error_log.append(error_msg)
            
            return NodeResult(
                node_name="ml_prediction",
                success=False,
                error=error_msg,
                next_node="error_handling"
            )
    
    def _generate_ml_features(self, state: WorkflowState) -> MLFeatures:
        """Generate ML features for prediction"""
        market_data = state.market_data
        portfolio_context = state.portfolio_context
        
        # Calculate technical indicators (simplified)
        change_pct = market_data.change_percent_24h
        volatility = abs(change_pct) / 100
        
        return MLFeatures(
            technical_indicators={
                "rsi": 50 + change_pct * 2,  # Simplified RSI
                "macd": change_pct / 10,     # Simplified MACD
                "bollinger_position": change_pct / 5,  # Simplified BB position
                "volume_ratio": min(market_data.volume / 5000000, 2.0)
            },
            sentiment_score=0.6 if change_pct > 0 else 0.4,  # Simplified sentiment
            market_regime=state.market_condition.value if state.market_condition else "unknown",
            momentum_score=change_pct / 100,
            volatility_score=volatility,
            features_vector=[change_pct, volatility, market_data.volume, 0.6, 0.7]
        )
    
    def _generate_prediction(self, state: WorkflowState, features: MLFeatures) -> MLPrediction:
        """Generate ML prediction"""
        import random
        
        # Simulate ensemble model prediction
        change_pct = features.technical_indicators.get("rsi", 50) - 50
        momentum = features.momentum_score
        
        # Decision logic based on simplified model
        if momentum > 0.02 and change_pct > 10:
            decision = DecisionOutcome.BUY
            confidence = 0.75
        elif momentum < -0.02 and change_pct < -10:
            decision = DecisionOutcome.SELL
            confidence = 0.72
        elif abs(momentum) < 0.01:
            decision = DecisionOutcome.HOLD
            confidence = 0.85
        else:
            decision = DecisionOutcome.HOLD
            confidence = 0.60
        
        # Calculate price target
        current_price = state.market_data.price
        price_change = confidence * 0.05  # Max 5% change
        price_target = current_price * (1 + price_change if decision == DecisionOutcome.BUY else 1 - price_change)
        
        # Calculate stop loss and take profit
        stop_loss = current_price * 0.98 if decision in [DecisionOutcome.BUY, DecisionOutcome.SELL] else None
        take_profit = current_price * 1.03 if decision in [DecisionOutcome.BUY, DecisionOutcome.SELL] else None
        
        # Risk score
        risk_score = abs(change_pct) / 100 + features.volatility_score
        
        return MLPrediction(
            prediction_id=str(uuid.uuid4()),
            model_name=self.default_model,
            decision=decision,
            confidence=confidence,
            price_target=price_target,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_score=risk_score,
            features_used=features,
            timestamp=datetime.now()
        )
    
    def _calculate_prediction_confidence(self, prediction: MLPrediction, state: WorkflowState) -> float:
        """Calculate enhanced prediction confidence"""
        base_confidence = prediction.confidence
        
        # Adjust based on market condition
        market_confidence_multiplier = {
            MarketCondition.BULLISH: 1.1,
            MarketCondition.BEARISH: 1.1,
            MarketCondition.SIDEWAYS: 0.9,
            MarketCondition.VOLATILE: 0.8,
            MarketCondition.TRENDING: 1.05
        }
        
        multiplier = market_confidence_multiplier.get(state.market_condition, 1.0)
        adjusted_confidence = min(base_confidence * multiplier, 0.95)
        
        return adjusted_confidence
    
    def _identify_risk_factors(self, prediction: MLPrediction, state: WorkflowState) -> List[str]:
        """Identify risk factors for the prediction"""
        risk_factors = []
        
        # Risk based on confidence level
        if prediction.confidence < 0.6:
            risk_factors.append("Low prediction confidence")
        
        # Risk based on volatility
        if prediction.risk_score > 0.05:
            risk_factors.append("High market volatility")
        
        # Risk based on market condition
        if state.market_condition == MarketCondition.VOLATILE:
            risk_factors.append("Volatile market conditions")
        
        # Risk based on portfolio exposure
        current_exposure = state.portfolio_context.get("current_exposure", 0)
        if current_exposure > 0.7:
            risk_factors.append("High portfolio exposure")
        
        return risk_factors


class RiskManagementNode:
    """Node for risk assessment and management"""
    
    def __init__(self, risk_config=None):
        self.risk_config = risk_config or self._default_risk_config()
        self.max_risk_per_trade = 0.02  # 2% max risk per trade
        
    def execute(self, state: WorkflowState) -> NodeResult:
        """
        Perform risk assessment and risk-adjusted decision making
        
        Args:
            state: Current workflow state
            
        Returns:
            NodeResult: Risk assessment result
        """
        try:
            if not state.ml_prediction:
                raise ValueError("ML prediction required for risk assessment")
            
            # Perform risk assessment
            risk_assessment = self._assess_risk(state)
            
            # Apply risk management logic
            adjusted_action = self._apply_risk_management(state, risk_assessment)
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(state, risk_assessment)
            
            # Prepare result data
            result_data = {
                "risk_assessment": asdict(risk_assessment),
                "adjusted_action": adjusted_action,
                "risk_metrics": risk_metrics,
                "risk_timestamp": datetime.now().isoformat(),
                "compliance_check": self._check_compliance(risk_assessment, state)
            }
            
            # Update state
            state.risk_assessment = risk_assessment
            state.risk_score = risk_assessment.risk_level.value
            state.risk_adjusted_action = adjusted_action
            
            logger.info(f"Risk assessment completed: {risk_assessment.risk_level.value} risk")
            
            # Decide next node based on risk level
            next_node = "execution" if risk_assessment.risk_level != RiskLevel.CRITICAL else "risk_review"
            
            return NodeResult(
                node_name="risk_management",
                success=True,
                data=result_data,
                next_node=next_node
            )
            
        except Exception as e:
            error_msg = f"Risk assessment failed: {str(e)}"
            logger.error(error_msg)
            state.error_log.append(error_msg)
            
            return NodeResult(
                node_name="risk_management",
                success=False,
                error=error_msg,
                next_node="error_handling"
            )
    
    def _default_risk_config(self) -> Dict[str, Any]:
        """Default risk management configuration"""
        return {
            "max_portfolio_risk": 0.10,      # 10% max portfolio risk
            "max_position_size": 0.20,       # 20% max position size
            "stop_loss_threshold": 0.05,     # 5% stop loss threshold
            "risk_free_rate": 0.02,          # 2% risk-free rate
            "correlation_limit": 0.7,        # 70% correlation limit
            "var_limit": 0.05                # 5% Value at Risk limit
        }
    
    def _assess_risk(self, state: WorkflowState) -> RiskAssessment:
        """Perform comprehensive risk assessment"""
        prediction = state.ml_prediction
        portfolio_context = state.portfolio_context
        
        # Calculate current exposure
        current_exposure = portfolio_context.get("current_exposure", 0)
        available_balance = portfolio_context.get("available_balance", 10000)
        
        # Calculate position size based on prediction
        position_size = self._calculate_position_size(prediction, available_balance)
        
        # Assess risk level
        risk_level = self._calculate_risk_level(prediction, position_size, current_exposure)
        
        # Calculate portfolio risk impact
        portfolio_risk = self._calculate_portfolio_risk(position_size, current_exposure)
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(prediction, current_exposure, portfolio_risk)
        
        return RiskAssessment(
            risk_level=risk_level,
            max_position_size=position_size,
            current_exposure=current_exposure,
            portfolio_risk=portfolio_risk,
            risk_factors=risk_factors,
            recommended_action=self._get_recommended_action(risk_level, prediction.decision)
        )
    
    def _calculate_position_size(self, prediction: MLPrediction, available_balance: float) -> float:
        """Calculate safe position size based on risk metrics"""
        base_size = available_balance * 0.1  # Default 10% position
        
        # Adjust based on prediction confidence
        confidence_adj = prediction.confidence
        position_size = base_size * confidence_adj
        
        # Apply maximum limits
        max_position = available_balance * self.risk_config["max_position_size"]
        position_size = min(position_size, max_position)
        
        return round(position_size, 2)
    
    def _calculate_risk_level(
        self, 
        prediction: MLPrediction, 
        position_size: float, 
        current_exposure: float
    ) -> RiskLevel:
        """Calculate overall risk level"""
        risk_score = 0
        
        # Confidence risk
        if prediction.confidence < 0.5:
            risk_score += 2
        elif prediction.confidence < 0.7:
            risk_score += 1
        
        # Volatility risk
        if prediction.risk_score > 0.1:
            risk_score += 2
        elif prediction.risk_score > 0.05:
            risk_score += 1
        
        # Position size risk
        if position_size > 5000:
            risk_score += 1
        
        # Portfolio exposure risk
        if current_exposure > 0.8:
            risk_score += 2
        elif current_exposure > 0.6:
            risk_score += 1
        
        # Map to risk levels
        if risk_score >= 5:
            return RiskLevel.CRITICAL
        elif risk_score >= 3:
            return RiskLevel.HIGH
        elif risk_score >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_portfolio_risk(self, position_size: float, current_exposure: float) -> float:
        """Calculate portfolio risk percentage"""
        base_risk = position_size / 10000  # Assume $10k portfolio
        exposure_risk = current_exposure * 0.1
        
        return base_risk + exposure_risk
    
    def _identify_risk_factors(
        self, 
        prediction: MLPrediction, 
        current_exposure: float, 
        portfolio_risk: float
    ) -> List[str]:
        """Identify specific risk factors"""
        risk_factors = []
        
        if prediction.confidence < 0.6:
            risk_factors.append("Low prediction confidence")
        
        if prediction.risk_score > 0.08:
            risk_factors.append("High volatility risk")
        
        if current_exposure > 0.7:
            risk_factors.append("High portfolio exposure")
        
        if portfolio_risk > 0.08:
            risk_factors.append("High portfolio risk")
        
        if len(risk_factors) >= 3:
            risk_factors.append("Multiple risk factors present")
        
        return risk_factors
    
    def _get_recommended_action(self, risk_level: RiskLevel, prediction_decision: DecisionOutcome) -> str:
        """Get recommended action based on risk assessment"""
        if risk_level == RiskLevel.CRITICAL:
            return "REJECT_TRADE"
        elif risk_level == RiskLevel.HIGH:
            if prediction_decision in [DecisionOutcome.BUY, DecisionOutcome.SELL]:
                return "REDUCE_POSITION"
            else:
                return "HOLD_POSITION"
        elif risk_level == RiskLevel.MEDIUM:
            return "PROCEED_WITH_CAUTION"
        else:
            return "PROCEED"
    
    def _apply_risk_management(self, state: WorkflowState, risk_assessment: RiskAssessment) -> str:
        """Apply risk management rules to trading decision"""
        prediction = state.ml_prediction
        
        recommended_action = risk_assessment.recommended_action
        
        if recommended_action == "REJECT_TRADE":
            return "HOLD"
        elif recommended_action == "REDUCE_POSITION":
            # Reduce confidence for high-risk trades
            adjusted_confidence = prediction.confidence * 0.7
            state.prediction_confidence = adjusted_confidence
            return prediction.decision.value
        elif recommended_action == "PROCEED_WITH_CAUTION":
            # Slight confidence reduction
            adjusted_confidence = prediction.confidence * 0.9
            state.prediction_confidence = adjusted_confidence
            return prediction.decision.value
        else:
            return prediction.decision.value
    
    def _calculate_risk_metrics(self, state: WorkflowState, risk_assessment: RiskAssessment) -> Dict[str, float]:
        """Calculate detailed risk metrics"""
        prediction = state.ml_prediction
        
        return {
            "expected_return": prediction.confidence * 0.05,  # Simplified expected return
            "max_loss": risk_assessment.max_position_size * 0.05,  # Max potential loss
            "risk_reward_ratio": prediction.confidence / 0.05 if risk_assessment.max_position_size > 0 else 0,
            "correlation_risk": 0.3,  # Simplified correlation risk
            "liquidity_risk": 0.1 if state.market_data.volume > 1000000 else 0.3
        }
    
    def _check_compliance(self, risk_assessment: RiskAssessment, state: WorkflowState) -> Dict[str, bool]:
        """Check compliance with risk management rules"""
        portfolio_context = state.portfolio_context
        
        return {
            "max_position_size_ok": risk_assessment.max_position_size <= self.risk_config["max_position_size"],
            "portfolio_risk_ok": risk_assessment.portfolio_risk <= self.risk_config["max_portfolio_risk"],
            "confidence_threshold_ok": state.prediction_confidence >= 0.5,
            "stop_loss_set": state.ml_prediction.stop_loss is not None,
            "take_profit_set": state.ml_prediction.take_profit is not None
        }


class ExecutionNode:
    """Node for trading execution"""
    
    def __init__(self, execution_engine=None):
        self.execution_engine = execution_engine
        self.order_manager = None
        
    def execute(self, state: WorkflowState) -> NodeResult:
        """
        Execute trading orders based on approved decisions
        
        Args:
            state: Current workflow state
            
        Returns:
            NodeResult: Execution result
        """
        try:
            if not state.risk_adjusted_action:
                raise ValueError("Risk-adjusted action required for execution")
            
            if state.risk_adjusted_action == "HOLD":
                return self._handle_hold_action(state)
            
            # Generate execution order
            execution_order = self._generate_execution_order(state)
            
            # Execute order (simulated)
            execution_result = self._execute_order(execution_order)
            
            # Update state
            state.execution_order = execution_order
            state.execution_status = execution_result["status"]
            state.execution_result = execution_result
            
            logger.info(f"Order execution completed: {execution_result['status']}")
            
            return NodeResult(
                node_name="execution",
                success=True,
                data={
                    "execution_order": asdict(execution_order),
                    "execution_result": execution_result,
                    "execution_timestamp": datetime.now().isoformat()
                },
                next_node="completion"
            )
            
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            logger.error(error_msg)
            state.error_log.append(error_msg)
            
            return NodeResult(
                node_name="execution",
                success=False,
                error=error_msg,
                next_node="error_handling"
            )
    
    def _handle_hold_action(self, state: WorkflowState) -> NodeResult:
        """Handle hold action (no execution)"""
        execution_result = {
            "status": "HOLD",
            "message": "Trade not executed due to risk management",
            "reason": state.risk_adjusted_action,
            "timestamp": datetime.now().isoformat()
        }
        
        state.execution_status = "HOLD"
        state.execution_result = execution_result
        
        return NodeResult(
            node_name="execution",
            success=True,
            data=execution_result,
            next_node="completion"
        )
    
    def _generate_execution_order(self, state: WorkflowState) -> ExecutionOrder:
        """Generate execution order based on state"""
        risk_assessment = state.risk_assessment
        prediction = state.ml_prediction
        
        # Calculate quantity based on risk assessment
        quantity = risk_assessment.max_position_size / state.market_data.price if state.market_data.price > 0 else 0
        
        return ExecutionOrder(
            order_id=str(uuid.uuid4()),
            symbol=state.market_data.symbol,
            action=state.risk_adjusted_action,
            quantity=quantity,
            order_type="MARKET" if state.risk_score >= 0.8 else "LIMIT",
            price=state.market_data.price,
            stop_loss=prediction.stop_loss,
            take_profit=prediction.take_profit,
            status="PENDING",
            timestamp=datetime.now()
        )
    
    def _execute_order(self, order: ExecutionOrder) -> Dict[str, Any]:
        """Execute the trading order (simulated)"""
        import random
        import time
        
        # Simulate order execution
        time.sleep(0.1)  # Simulate execution delay
        
        # Simulate execution result
        success_rate = 0.95 if order.order_type == "MARKET" else 0.85
        
        if random.random() < success_rate:
            execution_price = order.price * random.uniform(0.999, 1.001)  # Small price slippage
            
            return {
                "status": "FILLED",
                "order_id": order.order_id,
                "executed_price": execution_price,
                "filled_quantity": order.quantity,
                "commission": order.quantity * execution_price * 0.001,  # 0.1% commission
                "execution_timestamp": datetime.now().isoformat(),
                "slippage": execution_price - order.price
            }
        else:
            return {
                "status": "REJECTED",
                "order_id": order.order_id,
                "rejection_reason": "Market conditions or liquidity issues",
                "execution_timestamp": datetime.now().isoformat()
            }