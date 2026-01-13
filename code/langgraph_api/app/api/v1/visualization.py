"""
Workflow visualization endpoints for dashboard integration
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
import json

from ...auth.auth_handler import auth_handler, get_current_user
from ...auth.auth_models import User, APIResponse
from ...services.visualization_service import VisualizationService

logger = logging.getLogger(__name__)
router = APIRouter()
visualization_service = VisualizationService()

@router.get("/graph/{workflow_id}")
async def get_workflow_graph(
    workflow_id: str,
    format: str = Query("mermaid", description="Graph format (mermaid, json, d3)"),
    include_execution_path: bool = Query(True, description="Include actual execution path"),
    current_user: User = Depends(get_current_user)
):
    """Get workflow graph visualization"""
    try:
        graph_data = await visualization_service.get_workflow_graph(
            workflow_id, format, include_execution_path, current_user.id
        )
        if not graph_data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return graph_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timeline/{workflow_id}")
async def get_workflow_timeline(
    workflow_id: str,
    format: str = Query("mermaid", description="Timeline format"),
    include_duration: bool = Query(True, description="Include execution durations"),
    current_user: User = Depends(get_current_user)
):
    """Get workflow execution timeline"""
    try:
        timeline = await visualization_service.get_workflow_timeline(
            workflow_id, format, include_duration, current_user.id
        )
        if not timeline:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return timeline
    except HTTPException:
        raise
    except Exception as e):
        logger.error(f"Failed to get workflow timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/state-flow/{workflow_id}")
async def get_state_flow_diagram(
    workflow_id: str,
    format: str = Query("mermaid", description="Diagram format"),
    highlight_current: bool = Query(True, description="Highlight current state"),
    current_user: User = Depends(get_current_user)
):
    """Get state flow diagram for workflow"""
    try:
        state_flow = await visualization_service.get_state_flow_diagram(
            workflow_id, format, highlight_current, current_user.id
        )
        if not state_flow:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return state_flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get state flow diagram: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/execution-path/{workflow_id}")
async def get_execution_path(
    workflow_id: str,
    execution_id: Optional[str] = Query(None, description="Specific execution to visualize"),
    format: str = Query("json", description="Output format"),
    current_user: User = Depends(get_current_user)
):
    """Get workflow execution path visualization"""
    try:
        execution_path = await visualization_service.get_execution_path(
            workflow_id, execution_id, format, current_user.id
        )
        if not execution_path:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return execution_path
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution path: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/charts")
async def get_metrics_charts(
    workflow_id: Optional[str] = Query(None, description="Specific workflow or all workflows"),
    chart_type: str = Query("overview", description="Chart type (overview, performance, errors, throughput)"),
    time_range_hours: int = Query(24, ge=1, le=168),
    format: str = Query("json", description="Chart data format"),
    current_user: User = Depends(get_current_user)
):
    """Get metrics charts for visualization"""
    try:
        charts = await visualization_service.get_metrics_charts(
            workflow_id, chart_type, time_range_hours, format, current_user.id
        )
        return charts
    except Exception as e:
        logger.error(f"Failed to get metrics charts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/heatmap")
async def get_execution_heatmap(
    workflow_id: Optional[str] = Query(None, description="Specific workflow or all workflows"),
    time_range_hours: int = Query(168, ge=24, le=720, description="30 days max"),
    granularity: str = Query("hour", description="Time granularity (hour, day, week)"),
    current_user: User = Depends(get_current_user)
):
    """Get execution activity heatmap"""
    try:
        heatmap = await visualization_service.get_execution_heatmap(
            workflow_id, time_range_hours, granularity, current_user.id
        )
        return heatmap
    except Exception as e:
        logger.error(f"Failed to get execution heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/network/{workflow_id}")
async def get_workflow_network(
    workflow_id: str,
    include_weights: bool = Query(True, description="Include edge weights"),
    layout: str = Query("force", description="Layout algorithm"),
    current_user: User = Depends(get_current_user)
):
    """Get network diagram of workflow nodes and connections"""
    try:
        network = await visualization_service.get_workflow_network(
            workflow_id, include_weights, layout, current_user.id
        )
        if not network:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return network
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow network: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard/widgets")
async def get_dashboard_widgets(
    widget_types: Optional[List[str]] = Query(None, description="Specific widget types"),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard widget configurations"""
    try:
        widgets = await visualization_service.get_dashboard_widgets(
            widget_types, current_user.id
        )
        return widgets
    except Exception as e:
        logger.error(f"Failed to get dashboard widgets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard/widgets")
async def save_dashboard_layout(
    layout_data: Dict[str, Any],
    widget_types: Optional[List[str]] = Query(None, description="Widget types in layout"),
    current_user: User = Depends(get_current_user)
):
    """Save custom dashboard layout"""
    try:
        saved_layout = await visualization_service.save_dashboard_layout(
            layout_data, widget_types, current_user.id
        )
        return APIResponse(
            message="Dashboard layout saved successfully",
            data=saved_layout
        )
    except Exception as e:
        logger.error(f"Failed to save dashboard layout: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/anomalies")
async def get_anomaly_visualization(
    time_range_hours: int = Query(24, ge=1, le=168),
    sensitivity: float = Query(0.95, ge=0.8, le=0.99, description="Anomaly detection sensitivity"),
    current_user: User = Depends(get_current_user)
):
    """Get anomaly detection visualizations"""
    try:
        anomalies = await visualization_service.get_anomaly_visualization(
            time_range_hours, sensitivity, current_user.id
        )
        return anomalies
    except Exception as e:
        logger.error(f"Failed to get anomaly visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/comparisons")
async def get_workflow_comparison(
    workflow_ids: List[str] = Query(..., description="Workflow IDs to compare"),
    comparison_type: str = Query("performance", description="Type of comparison"),
    time_range_hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_user)
):
    """Get workflow comparison visualization"""
    try:
        if len(workflow_ids) > 10:
            raise HTTPException(
                status_code=400, 
                detail="Maximum 10 workflows can be compared at once"
            )
        
        comparison = await visualization_service.get_workflow_comparison(
            workflow_ids, comparison_type, time_range_hours, current_user.id
        )
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/{workflow_id}")
async def export_visualization(
    workflow_id: str,
    format: str = Query("png", description="Export format (png, svg, pdf)"),
    include_metrics: bool = Query(True, description="Include metrics in export"),
    current_user: User = Depends(get_current_user)
):
    """Export workflow visualization to file"""
    try:
        export_data = await visualization_service.export_visualization(
            workflow_id, format, include_metrics, current_user.id
        )
        if not export_data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return export_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/themes")
async def get_available_themes(
    current_user: User = Depends(get_current_user)
):
    """Get available visualization themes"""
    try:
        themes = await visualization_service.get_available_themes()
        return {"themes": themes}
    except Exception as e:
        logger.error(f"Failed to get themes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/themes/preview")
async def preview_theme(
    theme_config: Dict[str, Any],
    workflow_id: Optional[str] = Query(None, description="Workflow to use for preview"),
    current_user: User = Depends(get_current_user)
):
    """Preview visualization theme"""
    try:
        preview = await visualization_service.preview_theme(
            theme_config, workflow_id, current_user.id
        )
        return preview
    except Exception as e:
        logger.error(f"Failed to preview theme: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/interactive/{workflow_id}")
async def get_interactive_visualization(
    workflow_id: str,
    include_controls: bool = Query(True, description="Include interactive controls"),
    auto_refresh: bool = Query(True, description="Enable auto-refresh"),
    current_user: User = Depends(get_current_user)
):
    """Get interactive workflow visualization"""
    try:
        interactive_viz = await visualization_service.get_interactive_visualization(
            workflow_id, include_controls, auto_refresh, current_user.id
        )
        if not interactive_viz:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return interactive_viz
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get interactive visualization: {e}")
        raise HTTPException(status_code=500, detail=str(e))