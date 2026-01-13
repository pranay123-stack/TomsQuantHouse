"""
Crew Orchestration API
FastAPI interface for external integration with the trading agent crew
"""
from typing import Dict, List, Optional, Any, Union
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio
import logging
import uuid

from orchestration.crew_orchestrator import create_crew_orchestrator, CrewOrchestrator
from orchestration.approval_workflow import ApprovalType, PriorityLevel, ApprovalStatus
from config.settings import settings

# Initialize FastAPI app
app = FastAPI(
    title="CrewAI Trading Agent API",
    description="API for managing and integrating with the trading agent crew",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator: Optional[CrewOrchestrator] = None

# Pydantic models for API
class TradeRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    side: str = Field(..., description="Trade side: buy or sell")
    quantity: int = Field(..., gt=0, description="Number of shares")
    order_type: str = Field(default="market", description="Order type")
    execution_strategy: str = Field(default="immediate", description="Execution strategy")
    urgency: str = Field(default="normal", description="Urgency: low, normal, high")
    max_price: Optional[float] = Field(None, description="Maximum price for limit orders")
    
class PortfolioRequest(BaseModel):
    positions: Dict[str, Dict[str, Any]] = Field(..., description="Portfolio positions")
    cash: float = Field(..., description="Available cash")
    total_value: float = Field(..., description="Total portfolio value")

class AnalysisRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols to analyze")
    analysis_type: str = Field(default="complete", description="Type of analysis")
    include_predictions: bool = Field(default=True, description="Include ML predictions")
    include_risk_analysis: bool = Field(default=True, description="Include risk analysis")

class ApprovalResponse(BaseModel):
    approval_id: str
    status: str
    message: str
    timestamp: str

class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str

class MetricsResponse(BaseModel):
    metrics: Dict[str, Any]
    timestamp: str

# Dependency to get orchestrator
async def get_orchestrator() -> CrewOrchestrator:
    global orchestrator
    if orchestrator is None:
        orchestrator = await create_crew_orchestrator("api_crew", async_mode=True)
        await orchestrator.initialize()
    return orchestrator

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Crew management endpoints
@app.post("/crew/initialize")
async def initialize_crew(crew_id: str = "default"):
    """Initialize the trading agent crew"""
    try:
        global orchestrator
        orchestrator = await create_crew_orchestrator(crew_id, async_mode=True)
        await orchestrator.initialize()
        
        return {
            "status": "initialized",
            "crew_id": crew_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Error initializing crew: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crew/shutdown")
async def shutdown_crew(orchestrator: CrewOrchestrator = Depends(get_orchestrator)):
    """Shutdown the trading agent crew"""
    try:
        await orchestrator.shutdown()
        return {
            "status": "shutdown",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logging.error(f"Error shutting down crew: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Market analysis endpoints
@app.post("/analysis/complete")
async def run_complete_analysis(
    request: AnalysisRequest,
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Run complete trading analysis for symbols"""
    try:
        results = {}
        
        if request.analysis_type == "complete":
            # Run analysis for each symbol
            tasks = []
            for symbol in request.symbols:
                task = orchestrator.run_complete_analysis(symbol)
                tasks.append(task)
            
            # Execute in parallel
            analysis_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(analysis_results):
                symbol = request.symbols[i]
                if isinstance(result, Exception):
                    results[symbol] = {"error": str(result)}
                else:
                    results[symbol] = result
        
        return {
            "status": "completed",
            "analysis_type": request.analysis_type,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error in complete analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analysis/market")
async def analyze_market_conditions(
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Analyze current market conditions"""
    try:
        result = await orchestrator.market_research_analyst.analyze_market_conditions()
        
        return {
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error analyzing market: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analysis/sector")
async def analyze_sector_trends(
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Analyze sector rotation and trends"""
    try:
        result = await orchestrator.market_research_analyst.analyze_sector_performance()
        
        return {
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error analyzing sectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Trading endpoints
@app.post("/trade/submit")
async def submit_trade(
    request: TradeRequest,
    background_tasks: BackgroundTasks,
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Submit a trade for execution"""
    try:
        # Convert API model to internal format
        trade_request = {
            "symbol": request.symbol,
            "side": request.side,
            "quantity": request.quantity,
            "order_type": request.order_type,
            "execution_strategy": request.execution_strategy,
            "urgency": request.urgency,
            "max_price": request.max_price
        }
        
        # Submit trade workflow
        result = await orchestrator.execute_trade_workflow(trade_request)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return WorkflowResponse(
            workflow_id=result.get("workflow_id", ""),
            status=result.get("status", "submitted"),
            message=result.get("message", "Trade submitted successfully"),
            data=result,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logging.error(f"Error submitting trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trade/optimize-strategy")
async def optimize_execution_strategy(
    request: TradeRequest,
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Get optimal execution strategy for a trade"""
    try:
        trade_request = {
            "symbol": request.symbol,
            "quantity": request.quantity,
            "urgency": request.urgency
        }
        
        result = await orchestrator.execution_trader.get_optimal_execution_strategy(trade_request)
        
        return {
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error optimizing execution strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Portfolio management endpoints
@app.post("/portfolio/review")
async def review_portfolio(
    request: PortfolioRequest,
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Run comprehensive portfolio review"""
    try:
        portfolio_data = {
            "positions": request.positions,
            "cash": request.cash,
            "total_value": request.total_value
        }
        
        result = await orchestrator.run_portfolio_review(portfolio_data)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error reviewing portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portfolio/risk-assessment")
async def assess_portfolio_risk(
    request: PortfolioRequest,
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Assess portfolio risk"""
    try:
        portfolio_data = {
            "positions": request.positions,
            "cash": request.cash,
            "total_value": request.total_value
        }
        
        result = await orchestrator.chief_risk_officer.assess_portfolio_risk(portfolio_data)
        
        return {
            "status": "completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error assessing portfolio risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ML and prediction endpoints
@app.post("/ml/build-model")
async def build_prediction_model(
    symbol: str,
    model_type: str = "random_forest",
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Build ML prediction model for symbol"""
    try:
        result = await orchestrator.ml_prediction_engineer.build_prediction_model(symbol, model_type)
        
        return {
            "status": "completed",
            "symbol": symbol,
            "model_type": model_type,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error building model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ml/predict")
async def generate_predictions(
    symbol: str,
    model_type: str = "random_forest",
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Generate price predictions"""
    try:
        result = await orchestrator.ml_prediction_engineer.make_prediction(symbol, model_type)
        
        return {
            "status": "completed",
            "symbol": symbol,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error generating predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ml/backtest")
async def backtest_strategy(
    symbol: str,
    strategy: str = "momentum",
    model_type: str = "random_forest",
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Backtest trading strategy"""
    try:
        result = await orchestrator.ml_prediction_engineer.backtest_strategy(symbol, model_type)
        
        return {
            "status": "completed",
            "symbol": symbol,
            "strategy": strategy,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error backtesting strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Approval workflow endpoints
@app.get("/approvals/pending")
async def list_pending_approvals(
    approver: Optional[str] = None,
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """List pending approval requests"""
    try:
        approvals = await orchestrator.approval_workflow.list_pending_approvals(approver)
        
        return {
            "status": "completed",
            "approvals": approvals,
            "count": len(approvals),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error listing approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approvals/{approval_id}/decision")
async def process_approval_decision(
    approval_id: str,
    decision: str,
    notes: str = "",
    approver: str = "api_user",
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Process approval decision"""
    try:
        if decision not in ["approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")
        
        approval_status = ApprovalStatus.APPROVED if decision == "approved" else ApprovalStatus.REJECTED
        
        success = await orchestrator.approval_workflow.process_approval(
            approval_id,
            approver,
            approval_status,
            notes
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Approval request not found or invalid")
        
        return ApprovalResponse(
            approval_id=approval_id,
            status=decision,
            message=f"Approval {decision} successfully",
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing approval: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/approvals/{approval_id}/status")
async def get_approval_status(
    approval_id: str,
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Get approval request status"""
    try:
        status = await orchestrator.approval_workflow.get_approval_status(approval_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Approval request not found")
        
        return {
            "status": "completed",
            "approval_id": approval_id,
            "status_data": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting approval status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Monitoring and metrics endpoints
@app.get("/monitoring/active")
async def get_active_workflows(
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Get list of active workflows"""
    try:
        workflows = await orchestrator.list_workflows("running")
        
        return {
            "status": "completed",
            "workflows": workflows,
            "count": len(workflows),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error getting active workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitoring/alerts")
async def get_recent_alerts(
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Get recent alerts and notifications"""
    try:
        # This would typically fetch from a alerts storage
        # For now, return mock data
        alerts = []
        
        return {
            "status": "completed",
            "alerts": alerts,
            "count": len(alerts),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/crew")
async def get_crew_metrics(
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Get crew performance metrics"""
    try:
        metrics = await orchestrator.get_crew_metrics()
        
        return MetricsResponse(
            metrics=metrics,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logging.error(f"Error getting crew metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Execution and trading endpoints
@app.get("/execution/history")
async def get_execution_history(
    limit: int = 10,
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Get trading execution history"""
    try:
        result = await orchestrator.execution_trader.get_execution_history(limit)
        
        return {
            "status": "completed",
            "history": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error getting execution history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execution/monitor")
async def monitor_market_conditions(
    symbols: List[str],
    orchestrator: CrewOrchestrator = Depends(get_orchestrator)
):
    """Monitor market conditions for execution timing"""
    try:
        result = await orchestrator.execution_trader.monitor_market_conditions(symbols)
        
        return {
            "status": "completed",
            "symbols": symbols,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error monitoring market: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoints for real-time updates
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            # Process based on message type
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            elif data.get("type") == "subscribe_alerts":
                # Subscribe to alerts (implement as needed)
                await websocket.send_json({"type": "subscription_confirmed", "channel": "alerts"})
            
    except WebSocketDisconnect:
        logging.info(f"WebSocket client {client_id} disconnected")

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logging.error(f"Global exception: {exc}")
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "timestamp": datetime.now().isoformat()
    }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logging.info("CrewAI Trading API starting up...")
    
    # Initialize default orchestrator
    global orchestrator
    if orchestrator is None:
        try:
            orchestrator = await create_crew_orchestrator("default", async_mode=True)
            await orchestrator.initialize()
            logging.info("Default crew initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize default crew: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logging.info("CrewAI Trading API shutting down...")
    
    # Shutdown orchestrator
    global orchestrator
    if orchestrator:
        await orchestrator.shutdown()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )