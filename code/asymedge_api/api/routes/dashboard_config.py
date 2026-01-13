"""
ASYMEdge Dashboard API - Dashboard Configuration Routes

Dashboard configuration endpoints providing:
- Dashboard layout and widget configuration
- Theme and appearance settings
- User preferences and filters
- Dashboard sharing and templates
- Real-time data source configuration
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from api.database.models import DashboardConfig, User
from api.database.database import get_db_session
from api.schemas import (
    DashboardConfigResponse, DashboardConfigCreate, DashboardConfigUpdate,
    APIResponse, PaginationParams
)
from api.middleware.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Dashboard Configuration Endpoints

@router.get("/configs", response_model=List[DashboardConfigResponse])
async def get_dashboard_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_public: bool = Query(False, description="Include public dashboards from other users"),
    current_user: get_current_user = Depends(get_current_user)
):
    """Get dashboard configurations for the current user"""
    try:
        with get_db_session() as db:
            query = db.query(DashboardConfig)
            
            # Filter by ownership or public access
            if include_public:
                query = query.filter(
                    (DashboardConfig.owner_id == current_user.id) | 
                    (DashboardConfig.is_public == True)
                )
            else:
                query = query.filter(DashboardConfig.owner_id == current_user.id)
            
            # Apply pagination
            configs = query.offset(skip).limit(limit).order_by(
                DashboardConfig.is_default.desc(), 
                DashboardConfig.updated_at.desc()
            ).all()
            
            return [
                DashboardConfigResponse(
                    id=config.id,
                    name=config.name,
                    owner_id=config.owner_id,
                    is_default=config.is_default,
                    is_public=config.is_public,
                    layout_config=config.layout_config,
                    widget_configs=config.widget_configs,
                    theme_config=config.theme_config,
                    filters_config=config.filters_config,
                    metadata=config.metadata,
                    created_at=config.created_at,
                    updated_at=config.updated_at
                )
                for config in configs
            ]
            
    except Exception as e:
        logger.error(f"Failed to get dashboard configs: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/configs/{config_id}", response_model=DashboardConfigResponse)
async def get_dashboard_config(
    config_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Get a specific dashboard configuration by ID"""
    try:
        with get_db_session() as db:
            config = db.query(DashboardConfig).filter(
                DashboardConfig.id == config_id
            ).first()
            
            if not config:
                raise HTTPException(status_code=404, detail={"error": "Dashboard configuration not found"})
            
            # Check access permissions
            if config.owner_id != current_user.id and not config.is_public:
                raise HTTPException(status_code=403, detail={"error": "Access denied to this dashboard"})
            
            return DashboardConfigResponse(
                id=config.id,
                name=config.name,
                owner_id=config.owner_id,
                is_default=config.is_default,
                is_public=config.is_public,
                layout_config=config.layout_config,
                widget_configs=config.widget_configs,
                theme_config=config.theme_config,
                filters_config=config.filters_config,
                metadata=config.metadata,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard config {config_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/configs", response_model=DashboardConfigResponse)
async def create_dashboard_config(
    config_data: DashboardConfigCreate,
    current_user: get_current_user = Depends(get_current_user)
):
    """Create a new dashboard configuration"""
    try:
        with get_db_session() as db:
            # If setting as default, unset other defaults
            if config_data.is_default:
                db.query(DashboardConfig).filter(
                    DashboardConfig.owner_id == current_user.id,
                    DashboardConfig.is_default == True
                ).update({"is_default": False})
            
            config = DashboardConfig(
                name=config_data.name,
                owner_id=current_user.id,
                is_default=config_data.is_default,
                is_public=config_data.is_public,
                layout_config=config_data.layout_config,
                widget_configs=config_data.widget_configs,
                theme_config=config_data.theme_config,
                filters_config=config_data.filters_config,
                metadata=config_data.metadata
            )
            
            db.add(config)
            db.commit()
            db.refresh(config)
            
            logger.info(f"Dashboard config created: {config.name} by user {current_user.id}")
            
            return DashboardConfigResponse(
                id=config.id,
                name=config.name,
                owner_id=config.owner_id,
                is_default=config.is_default,
                is_public=config.is_public,
                layout_config=config.layout_config,
                widget_configs=config.widget_configs,
                theme_config=config.theme_config,
                filters_config=config.filters_config,
                metadata=config.metadata,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            
    except Exception as e:
        logger.error(f"Failed to create dashboard config: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.put("/configs/{config_id}", response_model=DashboardConfigResponse)
async def update_dashboard_config(
    config_id: int,
    config_data: DashboardConfigUpdate,
    current_user: get_current_user = Depends(get_current_user)
):
    """Update an existing dashboard configuration"""
    try:
        with get_db_session() as db:
            config = db.query(DashboardConfig).filter(
                DashboardConfig.id == config_id,
                DashboardConfig.owner_id == current_user.id
            ).first()
            
            if not config:
                raise HTTPException(status_code=404, detail={"error": "Dashboard configuration not found"})
            
            # Handle default dashboard changes
            update_data = config_data.dict(exclude_unset=True)
            
            if config_data.is_default and not config.is_default:
                # Setting as default, unset other defaults
                db.query(DashboardConfig).filter(
                    DashboardConfig.owner_id == current_user.id,
                    DashboardConfig.is_default == True
                ).update({"is_default": False})
            
            # Update fields
            for field, value in update_data.items():
                setattr(config, field, value)
            
            config.updated_at = datetime.now()
            
            db.commit()
            db.refresh(config)
            
            logger.info(f"Dashboard config updated: {config.name} by user {current_user.id}")
            
            return DashboardConfigResponse(
                id=config.id,
                name=config.name,
                owner_id=config.owner_id,
                is_default=config.is_default,
                is_public=config.is_public,
                layout_config=config.layout_config,
                widget_configs=config.widget_configs,
                theme_config=config.theme_config,
                filters_config=config.filters_config,
                metadata=config.metadata,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update dashboard config {config_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.delete("/configs/{config_id}", response_model=APIResponse)
async def delete_dashboard_config(
    config_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Delete a dashboard configuration"""
    try:
        with get_db_session() as db:
            config = db.query(DashboardConfig).filter(
                DashboardConfig.id == config_id,
                DashboardConfig.owner_id == current_user.id
            ).first()
            
            if not config:
                raise HTTPException(status_code=404, detail={"error": "Dashboard configuration not found"})
            
            # Prevent deletion of default dashboard if it's the only one
            if config.is_default:
                other_configs = db.query(DashboardConfig).filter(
                    DashboardConfig.owner_id == current_user.id,
                    DashboardConfig.id != config_id
                ).count()
                
                if other_configs == 0:
                    raise HTTPException(
                        status_code=400,
                        detail={"error": "Cannot delete the only dashboard configuration"}
                    )
            
            # Delete configuration
            db.delete(config)
            db.commit()
            
            logger.info(f"Dashboard config deleted: {config.name} by user {current_user.id}")
            
            return APIResponse(
                success=True,
                message="Dashboard configuration deleted successfully",
                data={"config_id": config_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dashboard config {config_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/configs/{config_id}/clone", response_model=DashboardConfigResponse)
async def clone_dashboard_config(
    config_id: int,
    new_name: Optional[str] = Query(None, description="Name for the cloned dashboard"),
    current_user: get_current_user = Depends(get_current_user)
):
    """Clone an existing dashboard configuration"""
    try:
        with get_db_session() as db:
            # Get original config
            original_config = db.query(DashboardConfig).filter(
                DashboardConfig.id == config_id
            ).first()
            
            if not original_config:
                raise HTTPException(status_code=404, detail={"error": "Dashboard configuration not found"})
            
            # Check access permissions
            if original_config.owner_id != current_user.id and not original_config.is_public:
                raise HTTPException(status_code=403, detail={"error": "Access denied to this dashboard"})
            
            # Create cloned config
            clone_name = new_name or f"{original_config.name} (Copy)"
            
            clone_config = DashboardConfig(
                name=clone_name,
                owner_id=current_user.id,
                is_default=False,  # Cloned dashboards are never default
                is_public=False,   # Cloned dashboards inherit privacy
                layout_config=original_config.layout_config.copy(),
                widget_configs=original_config.widget_configs.copy(),
                theme_config=original_config.theme_config.copy() if original_config.theme_config else {},
                filters_config=original_config.filters_config.copy() if original_config.filters_config else {},
                metadata=original_config.metadata.copy() if original_config.metadata else {}
            )
            
            db.add(clone_config)
            db.commit()
            db.refresh(clone_config)
            
            logger.info(f"Dashboard config cloned: {original_config.name} -> {clone_config.name} by user {current_user.id}")
            
            return DashboardConfigResponse(
                id=clone_config.id,
                name=clone_config.name,
                owner_id=clone_config.owner_id,
                is_default=clone_config.is_default,
                is_public=clone_config.is_public,
                layout_config=clone_config.layout_config,
                widget_configs=clone_config.widget_configs,
                theme_config=clone_config.theme_config,
                filters_config=clone_config.filters_config,
                metadata=clone_config.metadata,
                created_at=clone_config.created_at,
                updated_at=clone_config.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clone dashboard config {config_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/configs/{config_id}/set-default", response_model=APIResponse)
async def set_default_dashboard(
    config_id: int,
    current_user: get_current_user = Depends(get_current_user)
):
    """Set a dashboard as the default dashboard"""
    try:
        with get_db_session() as db:
            config = db.query(DashboardConfig).filter(
                DashboardConfig.id == config_id,
                DashboardConfig.owner_id == current_user.id
            ).first()
            
            if not config:
                raise HTTPException(status_code=404, detail={"error": "Dashboard configuration not found"})
            
            # Unset other defaults
            db.query(DashboardConfig).filter(
                DashboardConfig.owner_id == current_user.id,
                DashboardConfig.is_default == True
            ).update({"is_default": False})
            
            # Set this as default
            config.is_default = True
            config.updated_at = datetime.now()
            
            db.commit()
            
            logger.info(f"Default dashboard set: {config.name} for user {current_user.id}")
            
            return APIResponse(
                success=True,
                message="Default dashboard set successfully",
                data={"config_id": config_id, "name": config.name}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set default dashboard {config_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/default", response_model=DashboardConfigResponse)
async def get_default_dashboard(
    current_user: get_current_user = Depends(get_current_user)
):
    """Get the default dashboard configuration for the current user"""
    try:
        with get_db_session() as db:
            config = db.query(DashboardConfig).filter(
                DashboardConfig.owner_id == current_user.id,
                DashboardConfig.is_default == True
            ).first()
            
            if not config:
                # Create default dashboard if none exists
                default_config = await create_default_dashboard_config(current_user.id)
                return default_config
            
            return DashboardConfigResponse(
                id=config.id,
                name=config.name,
                owner_id=config.owner_id,
                is_default=config.is_default,
                is_public=config.is_public,
                layout_config=config.layout_config,
                widget_configs=config.widget_configs,
                theme_config=config.theme_config,
                filters_config=config.filters_config,
                metadata=config.metadata,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            
    except Exception as e:
        logger.error(f"Failed to get default dashboard: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Widget and Layout Management

@router.get("/widgets", response_model=List[Dict[str, Any]])
async def get_available_widgets(current_user: get_current_user = Depends(get_current_user)):
    """Get available widget types and their configurations"""
    try:
        widgets = [
            {
                "type": "portfolio_value",
                "name": "Portfolio Value",
                "description": "Display current portfolio total value",
                "icon": "trending_up",
                "category": "portfolio",
                "default_size": {"width": 4, "height": 2},
                "data_source": "trading_metrics",
                "configuration": {
                    "refresh_interval": 30,
                    "show_change": True,
                    "show_percentage": True,
                    "currency": "USD"
                }
            },
            {
                "type": "position_breakdown",
                "name": "Position Breakdown",
                "description": "Show allocation breakdown by symbol",
                "icon": "pie_chart",
                "category": "portfolio",
                "default_size": {"width": 6, "height": 4},
                "data_source": "trading_metrics",
                "configuration": {
                    "chart_type": "pie",
                    "show_percentages": True,
                    "max_positions": 10
                }
            },
            {
                "type": "performance_chart",
                "name": "Performance Chart",
                "description": "Display portfolio performance over time",
                "icon": "timeline",
                "category": "analytics",
                "default_size": {"width": 8, "height": 4},
                "data_source": "trading_metrics",
                "configuration": {
                    "time_period": "1M",
                    "chart_type": "line",
                    "show_comparison": True
                }
            },
            {
                "type": "agent_status",
                "name": "Agent Status",
                "description": "Show status of active agents",
                "icon": "smart_toy",
                "category": "agents",
                "default_size": {"width": 4, "height": 3},
                "data_source": "agents",
                "configuration": {
                    "show_activity": True,
                    "show_performance": True
                }
            },
            {
                "type": "workflow_status",
                "name": "Workflow Status",
                "description": "Display running workflows and their progress",
                "icon": "settings",
                "category": "workflows",
                "default_size": {"width": 6, "height": 4},
                "data_source": "workflows",
                "configuration": {
                    "show_progress": True,
                    "group_by_type": True
                }
            },
            {
                "type": "market_overview",
                "name": "Market Overview",
                "description": "Show major market indices and trends",
                "icon": "show_chart",
                "category": "market",
                "default_size": {"width": 4, "height": 3},
                "data_source": "market_data",
                "configuration": {
                    "indices": ["SPY", "QQQ", "IWM"],
                    "show_change": True
                }
            },
            {
                "type": "risk_metrics",
                "name": "Risk Metrics",
                "description": "Display portfolio risk indicators",
                "icon": "warning",
                "category": "analytics",
                "default_size": {"width": 4, "height": 3},
                "data_source": "trading_metrics",
                "configuration": {
                    "metrics": ["var", "sharpe_ratio", "max_drawdown"],
                    "show_alerts": True
                }
            },
            {
                "type": "recent_queries",
                "name": "Recent Agent Queries",
                "description": "Show recent agent query activity",
                "icon": "chat",
                "category": "agents",
                "default_size": {"width": 6, "height": 4},
                "data_source": "agents",
                "configuration": {
                    "max_queries": 10,
                    "show_responses": False
                }
            }
        ]
        
        return widgets
        
    except Exception as e:
        logger.error(f"Failed to get available widgets: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/themes", response_model=List[Dict[str, Any]])
async def get_available_themes(current_user: get_current_user = Depends(get_current_user)):
    """Get available dashboard themes"""
    try:
        themes = [
            {
                "id": "light",
                "name": "Light Theme",
                "description": "Clean light theme with bright colors",
                "colors": {
                    "background": "#ffffff",
                    "surface": "#f5f5f5",
                    "primary": "#1976d2",
                    "secondary": "#388e3c",
                    "text": "#212121",
                    "text_secondary": "#757575"
                }
            },
            {
                "id": "dark",
                "name": "Dark Theme",
                "description": "Professional dark theme for low-light environments",
                "colors": {
                    "background": "#121212",
                    "surface": "#1e1e1e",
                    "primary": "#2196f3",
                    "secondary": "#4caf50",
                    "text": "#ffffff",
                    "text_secondary": "#b0b0b0"
                }
            },
            {
                "id": "blue",
                "name": "Ocean Blue",
                "description": "Blue-themed professional appearance",
                "colors": {
                    "background": "#f8faff",
                    "surface": "#e3f2fd",
                    "primary": "#1565c0",
                    "secondary": "#2e7d32",
                    "text": "#0d47a1",
                    "text_secondary": "#1976d2"
                }
            },
            {
                "id": "green",
                "name": "Forest Green",
                "description": "Green-themed theme for nature-inspired dashboards",
                "colors": {
                    "background": "#f1f8e9",
                    "surface": "#e8f5e8",
                    "primary": "#2e7d32",
                    "secondary": "#1976d2",
                    "text": "#1b5e20",
                    "text_secondary": "#388e3c"
                }
            },
            {
                "id": "purple",
                "name": "Royal Purple",
                "description": "Elegant purple theme for premium feel",
                "colors": {
                    "background": "#faf8ff",
                    "surface": "#f3e5f5",
                    "primary": "#7b1fa2",
                    "secondary": "#388e3c",
                    "text": "#4a148c",
                    "text_secondary": "#8e24aa"
                }
            }
        ]
        
        return themes
        
    except Exception as e:
        logger.error(f"Failed to get available themes: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/templates", response_model=List[Dict[str, Any]])
async def get_dashboard_templates(current_user: get_current_user = Depends(get_current_user)):
    """Get pre-defined dashboard templates"""
    try:
        templates = [
            {
                "id": "portfolio_overview",
                "name": "Portfolio Overview",
                "description": "Complete portfolio monitoring dashboard",
                "category": "portfolio",
                "widgets": [
                    {"type": "portfolio_value", "position": {"x": 0, "y": 0, "width": 4, "height": 2}},
                    {"type": "position_breakdown", "position": {"x": 4, "y": 0, "width": 6, "height": 4}},
                    {"type": "performance_chart", "position": {"x": 0, "y": 2, "width": 4, "height": 4}},
                    {"type": "risk_metrics", "position": {"x": 10, "y": 0, "width": 2, "height": 6}}
                ],
                "theme": "light"
            },
            {
                "id": "trading_focused",
                "name": "Trading Dashboard",
                "description": "Focused trading and market analysis dashboard",
                "category": "trading",
                "widgets": [
                    {"type": "market_overview", "position": {"x": 0, "y": 0, "width": 4, "height": 3}},
                    {"type": "performance_chart", "position": {"x": 4, "y": 0, "width": 8, "height": 3}},
                    {"type": "position_breakdown", "position": {"x": 0, "y": 3, "width": 6, "height": 3}},
                    {"type": "workflow_status", "position": {"x": 6, "y": 3, "width": 6, "height": 3}}
                ],
                "theme": "dark"
            },
            {
                "id": "agent_monitoring",
                "name": "Agent Monitoring",
                "description": "Dashboard focused on agent activity and performance",
                "category": "agents",
                "widgets": [
                    {"type": "agent_status", "position": {"x": 0, "y": 0, "width": 4, "height": 3}},
                    {"type": "recent_queries", "position": {"x": 4, "y": 0, "width": 6, "height": 4}},
                    {"type": "workflow_status", "position": {"x": 0, "y": 3, "width": 4, "height": 4}}
                ],
                "theme": "blue"
            },
            {
                "id": "analytics_dashboard",
                "name": "Analytics Dashboard",
                "description": "Deep analytics and reporting dashboard",
                "category": "analytics",
                "widgets": [
                    {"type": "performance_chart", "position": {"x": 0, "y": 0, "width": 8, "height": 4}},
                    {"type": "risk_metrics", "position": {"x": 8, "y": 0, "width": 4, "height": 2}},
                    {"type": "portfolio_value", "position": {"x": 8, "y": 2, "width": 4, "height": 2}},
                    {"type": "position_breakdown", "position": {"x": 0, "y": 4, "width": 6, "height": 3}},
                    {"type": "market_overview", "position": {"x": 6, "y": 4, "width": 6, "height": 3}}
                ],
                "theme": "purple"
            }
        ]
        
        return templates
        
    except Exception as e:
        logger.error(f"Failed to get dashboard templates: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/templates/{template_id}/create", response_model=DashboardConfigResponse)
async def create_dashboard_from_template(
    template_id: str,
    config_name: str,
    current_user: get_current_user = Depends(get_current_user)
):
    """Create a new dashboard from a template"""
    try:
        # Get template data
        templates = await get_dashboard_templates(current_user)
        template = next((t for t in templates if t["id"] == template_id), None)
        
        if not template:
            raise HTTPException(status_code=404, detail={"error": "Template not found"})
        
        # Create dashboard configuration from template
        config_data = DashboardConfigCreate(
            name=config_name,
            layout_config={
                "grid": {"columns": 12, "rows": 8},
                "theme": template["theme"]
            },
            widget_configs={
                widget["type"]: {
                    "position": widget["position"],
                    "configuration": {}  # Use default widget configuration
                }
                for widget in template["widgets"]
            },
            theme_config={
                "theme_id": template["theme"],
                "custom_colors": {}
            }
        )
        
        # Create the dashboard
        config_response = await create_dashboard_config(config_data, current_user)
        
        return config_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create dashboard from template {template_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Helper function to create default dashboard
async def create_default_dashboard_config(user_id: int) -> DashboardConfigResponse:
    """Create a default dashboard configuration for a new user"""
    with get_db_session() as db:
        # Create default dashboard
        config = DashboardConfig(
            name="My Dashboard",
            owner_id=user_id,
            is_default=True,
            is_public=False,
            layout_config={
                "grid": {"columns": 12, "rows": 8},
                "theme": "light"
            },
            widget_configs={
                "portfolio_value": {
                    "position": {"x": 0, "y": 0, "width": 4, "height": 2},
                    "configuration": {"refresh_interval": 30, "show_change": True}
                },
                "position_breakdown": {
                    "position": {"x": 4, "y": 0, "width": 8, "height": 4},
                    "configuration": {"chart_type": "pie", "show_percentages": True}
                },
                "market_overview": {
                    "position": {"x": 0, "y": 2, "width": 4, "height": 3},
                    "configuration": {"indices": ["SPY", "QQQ", "IWM"], "show_change": True}
                },
                "agent_status": {
                    "position": {"x": 0, "y": 5, "width": 4, "height": 3},
                    "configuration": {"show_activity": True, "show_performance": True}
                }
            },
            theme_config={
                "theme_id": "light",
                "custom_colors": {}
            },
            filters_config={},
            metadata={"created_from": "default_template"}
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        return DashboardConfigResponse(
            id=config.id,
            name=config.name,
            owner_id=config.owner_id,
            is_default=config.is_default,
            is_public=config.is_public,
            layout_config=config.layout_config,
            widget_configs=config.widget_configs,
            theme_config=config.theme_config,
            filters_config=config.filters_config,
            metadata=config.metadata,
            created_at=config.created_at,
            updated_at=config.updated_at
        )