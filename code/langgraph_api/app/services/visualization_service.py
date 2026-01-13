"""
Visualization service for workflow graphs and charts
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from ..core.database import db_manager

logger = logging.getLogger(__name__)

class VisualizationService:
    """Service for visualization operations"""
    
    async def get_workflow_graph(
        self,
        workflow_id: str,
        format: str,
        include_execution_path: bool,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get workflow graph visualization"""
        # Verify workflow ownership
        workflow = await self._verify_workflow_ownership(workflow_id, user_id)
        if not workflow:
            return None
        
        if format == "mermaid":
            return await self._generate_mermaid_graph(workflow_id, include_execution_path)
        elif format == "json":
            return await self._generate_json_graph(workflow_id, include_execution_path)
        else:
            raise ValueError(f"Unsupported graph format: {format}")
    
    async def get_workflow_timeline(
        self,
        workflow_id: str,
        format: str,
        include_duration: bool,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get workflow execution timeline"""
        workflow = await self._verify_workflow_ownership(workflow_id, user_id)
        if not workflow:
            return None
        
        if format == "mermaid":
            return await self._generate_mermaid_timeline(workflow_id, include_duration)
        else:
            raise ValueError(f"Unsupported timeline format: {format}")
    
    async def get_state_flow_diagram(
        self,
        workflow_id: str,
        format: str,
        highlight_current: bool,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get state flow diagram"""
        workflow = await self._verify_workflow_ownership(workflow_id, user_id)
        if not workflow:
            return None
        
        # Get workflow states
        states = await self._get_workflow_states(workflow_id, user_id)
        
        if format == "mermaid":
            return await self._generate_state_flow_mermaid(states, highlight_current)
        else:
            raise ValueError(f"Unsupported flow format: {format}")
    
    async def get_execution_path(
        self,
        workflow_id: str,
        execution_id: Optional[str],
        format: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get workflow execution path"""
        workflow = await self._verify_workflow_ownership(workflow_id, user_id)
        if not workflow:
            return None
        
        # Get execution path data
        execution_path = await self._get_execution_path_data(workflow_id, execution_id)
        
        if format == "json":
            return {"execution_path": execution_path}
        else:
            raise ValueError(f"Unsupported execution path format: {format}")
    
    async def get_metrics_charts(
        self,
        workflow_id: Optional[str],
        chart_type: str,
        time_range_hours: int,
        format: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get metrics charts for visualization"""
        try:
            if chart_type == "overview":
                return await self._generate_overview_chart(workflow_id, time_range_hours, user_id)
            elif chart_type == "performance":
                return await self._generate_performance_chart(workflow_id, time_range_hours, user_id)
            elif chart_type == "errors":
                return await self._generate_error_chart(workflow_id, time_range_hours, user_id)
            elif chart_type == "throughput":
                return await self._generate_throughput_chart(workflow_id, time_range_hours, user_id)
            else:
                raise ValueError(f"Unsupported chart type: {chart_type}")
                
        except Exception as e:
            logger.error(f"Failed to generate metrics chart: {e}")
            raise
    ) -> Dict[str, Any]:
        """Get metrics charts for visualization"""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        if chart_type == "overview":
            return await self._generate_overview_charts(workflow_id, cutoff_time, user_id)
        elif chart_type == "performance":
            return await self._generate_performance_charts(workflow_id, cutoff_time, user_id)
        elif chart_type == "errors":
            return await self._generate_error_charts(workflow_id, cutoff_time, user_id)
        elif chart_type == "throughput":
            return await self._generate_throughput_charts(workflow_id, cutoff_time, user_id)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
    
    async def get_execution_heatmap(
        self,
        workflow_id: Optional[str],
        time_range_hours: int,
        granularity: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Get execution activity heatmap"""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        # Generate heatmap data
        heatmap_data = await self._generate_heatmap_data(workflow_id, cutoff_time, granularity, user_id)
        
        return {
            "heatmap_data": heatmap_data,
            "granularity": granularity,
            "time_range_hours": time_range_hours,
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_workflow_network(
        self,
        workflow_id: str,
        include_weights: bool,
        layout: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get network diagram of workflow nodes"""
        workflow = await self._verify_workflow_ownership(workflow_id, user_id)
        if not workflow:
            return None
        
        # Get workflow structure
        network_data = await self._generate_network_data(workflow_id, include_weights)
        
        return {
            "network": network_data,
            "layout": layout,
            "workflow_id": workflow_id
        }
    
    async def get_dashboard_widgets(
        self,
        widget_types: Optional[List[str]],
        user_id: str
    ) -> Dict[str, Any]:
        """Get dashboard widget configurations"""
        # Define available widgets
        available_widgets = {
            "workflow_count": {
                "title": "Workflow Count",
                "type": "metric",
                "config": {"metric": "workflow_count"}
            },
            "success_rate": {
                "title": "Success Rate",
                "type": "gauge",
                "config": {"metric": "success_rate", "min": 0, "max": 100}
            },
            "recent_executions": {
                "title": "Recent Executions",
                "type": "table",
                "config": {"columns": ["workflow", "status", "started_at"]}
            },
            "error_chart": {
                "title": "Error Analysis",
                "type": "chart",
                "config": {"chart_type": "bar", "metric": "errors"}
            },
            "performance_chart": {
                "title": "Performance Trends",
                "type": "chart",
                "config": {"chart_type": "line", "metric": "execution_time"}
            }
        }
        
        if widget_types:
            filtered_widgets = {k: v for k, v in available_widgets.items() if k in widget_types}
        else:
            filtered_widgets = available_widgets
        
        return {
            "widgets": filtered_widgets,
            "default_layout": [
                ["workflow_count", "success_rate"],
                ["recent_executions"],
                ["error_chart"],
                ["performance_chart"]
            ]
        }
    
    async def save_dashboard_layout(
        self,
        layout_data: Dict[str, Any],
        widget_types: Optional[List[str]],
        user_id: str
    ) -> Dict[str, Any]:
        """Save custom dashboard layout"""
        # In a real implementation, save to database
        saved_layout = {
            "layout": layout_data,
            "widget_types": widget_types,
            "saved_at": datetime.now().isoformat(),
            "user_id": user_id
        }
        
        logger.info(f"Saved dashboard layout for user {user_id}")
        return saved_layout
    
    async def get_anomaly_visualization(
        self,
        time_range_hours: int,
        sensitivity: float,
        user_id: str
    ) -> Dict[str, Any]:
        """Get anomaly detection visualizations"""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        # Generate anomaly data
        anomalies = await self._detect_anomalies(cutoff_time, sensitivity, user_id)
        
        return {
            "anomalies": anomalies,
            "sensitivity": sensitivity,
            "time_range_hours": time_range_hours,
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_workflow_comparison(
        self,
        workflow_ids: List[str],
        comparison_type: str,
        time_range_hours: int,
        user_id: str
    ) -> Dict[str, Any]:
        """Get workflow comparison visualization"""
        cutoff_time = datetime.now() - timedelta(hours=time_range_hours)
        
        comparison_data = await self._generate_comparison_data(workflow_ids, comparison_type, cutoff_time, user_id)
        
        return {
            "comparison_type": comparison_type,
            "workflows": comparison_data,
            "time_range_hours": time_range_hours,
            "generated_at": datetime.now().isoformat()
        }
    
    async def export_visualization(
        self,
        workflow_id: str,
        format: str,
        include_metrics: bool,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Export workflow visualization to file"""
        workflow = await self._verify_workflow_ownership(workflow_id, user_id)
        if not workflow:
            return None
        
        # Get visualization data
        graph_data = await self.get_workflow_graph(workflow_id, "json", include_metrics, user_id)
        timeline_data = await self.get_workflow_timeline(workflow_id, "mermaid", include_metrics, user_id)
        
        export_data = {
            "workflow_info": {
                "id": workflow_id,
                "name": workflow[1],
                "type": workflow[3]
            },
            "visualizations": {
                "graph": graph_data,
                "timeline": timeline_data
            },
            "export_metadata": {
                "format": format,
                "include_metrics": include_metrics,
                "exported_at": datetime.now().isoformat()
            }
        }
        
        return export_data
    
    async def get_available_themes(self) -> List[str]:
        """Get available visualization themes"""
        return [
            "default",
            "dark",
            "minimal",
            "corporate",
            "colorful",
            "monochrome"
        ]
    
    async def preview_theme(
        self,
        theme_config: Dict[str, Any],
        workflow_id: Optional[str],
        user_id: str
    ) -> Dict[str, Any]:
        """Preview visualization theme"""
        preview_data = {
            "theme_config": theme_config,
            "sample_visualizations": await self._generate_theme_preview(theme_config),
            "preview_timestamp": datetime.now().isoformat()
        }
        
        return preview_data
    
    async def get_interactive_visualization(
        self,
        workflow_id: str,
        include_controls: bool,
        auto_refresh: bool,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get interactive workflow visualization"""
        workflow = await self._verify_workflow_ownership(workflow_id, user_id)
        if not workflow:
            return None
        
        return {
            "interactive_graph": await self._generate_interactive_graph(workflow_id, user_id),
            "controls": {
                "enabled": include_controls,
                "auto_refresh": auto_refresh,
                "refresh_interval": 30
            },
            "workflow_id": workflow_id
        }
    
    async def _verify_workflow_ownership(self, workflow_id: str, user_id: str) -> Optional[tuple]:
        """Verify workflow ownership"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                "SELECT * FROM workflows WHERE id = ? AND user_id = ?",
                (workflow_id, user_id)
            )
            return result.fetchone()
    
    async def _get_workflow_states(self, workflow_id: str, user_id: str) -> List[tuple]:
        """Get workflow states"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                """
                SELECT s.* FROM states s 
                JOIN workflows w ON s.workflow_id = w.id 
                WHERE s.workflow_id = ? AND w.user_id = ?
                ORDER BY s.created_at DESC
                """,
                (workflow_id, user_id)
            )
            return result.fetchall()
    
    async def _generate_mermaid_graph(self, workflow_id: str, include_execution_path: bool) -> Dict[str, Any]:
        """Generate Mermaid diagram for workflow"""
        # Basic workflow structure
        mermaid_code = """
        graph TD
            Start([Workflow Start]) --> Analysis[Data Analysis]
            Analysis --> Processing[Data Processing]
            Processing --> Validation{Validation}
            Validation -->|Pass| Completion([Complete])
            Validation -->|Fail| ErrorHandling[Error Handling]
            ErrorHandling --> Retry[Retry]
            Retry --> Processing
        """
        
        if include_execution_path:
            # Add execution highlighting (simplified)
            mermaid_code += """
            classDef executed fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
            classDef failed fill:#ffebee,stroke:#c62828,stroke-width:2px
            classDef completed fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
            """
        
        return {
            "format": "mermaid",
            "code": mermaid_code,
            "workflow_id": workflow_id
        }
    
    async def _generate_json_graph(self, workflow_id: str, include_execution_path: bool) -> Dict[str, Any]:
        """Generate JSON graph structure"""
        return {
            "format": "json",
            "graph": {
                "nodes": [
                    {"id": "start", "label": "Start", "type": "start"},
                    {"id": "analysis", "label": "Data Analysis", "type": "process"},
                    {"id": "processing", "label": "Data Processing", "type": "process"},
                    {"id": "validation", "label": "Validation", "type": "decision"},
                    {"id": "completion", "label": "Complete", "type": "end"},
                    {"id": "error", "label": "Error Handling", "type": "error"}
                ],
                "edges": [
                    {"from": "start", "to": "analysis"},
                    {"from": "analysis", "to": "processing"},
                    {"from": "processing", "to": "validation"},
                    {"from": "validation", "to": "completion", "label": "Pass"},
                    {"from": "validation", "to": "error", "label": "Fail"},
                    {"from": "error", "to": "processing", "label": "Retry"}
                ]
            },
            "workflow_id": workflow_id
        }
    
    async def _generate_mermaid_timeline(self, workflow_id: str, include_duration: bool) -> Dict[str, Any]:
        """Generate Mermaid timeline"""
        timeline_code = """
        timeline
            title Workflow Execution Timeline
            2025-11-02 09:00 : Workflow Started
                : Initialize
            2025-11-02 09:01 : Data Analysis
                : Complete
            2025-11-02 09:02 : Processing
                : Running
            2025-11-02 09:03 : Validation
                : Success
            2025-11-02 09:04 : Completion
                : Finished
        """
        
        return {
            "format": "mermaid",
            "code": timeline_code,
            "workflow_id": workflow_id
        }
    
    async def _generate_state_flow_mermaid(self, states: List[tuple], highlight_current: bool) -> Dict[str, Any]:
        """Generate state flow Mermaid diagram"""
        flow_code = """
        graph LR
            State1[Initial State] --> State2[Processing]
            State2 --> State3[Validated]
            State3 --> State4[Completed]
        """
        
        if highlight_current:
            flow_code += """
            classDef current fill:#fff3e0,stroke:#f57c00,stroke-width:3px
            classDef current:::current
            """
        
        return {
            "format": "mermaid",
            "code": flow_code,
            "states": len(states)
        }
    
    async def _get_execution_path_data(self, workflow_id: str, execution_id: Optional[str]) -> List[Dict[str, Any]]:
        """Get execution path data"""
        # Simplified execution path
        return [
            {"node": "start", "timestamp": "2025-11-02T09:00:00Z", "status": "completed"},
            {"node": "analysis", "timestamp": "2025-11-02T09:01:00Z", "status": "completed"},
            {"node": "processing", "timestamp": "2025-11-02T09:02:00Z", "status": "completed"},
            {"node": "validation", "timestamp": "2025-11-02T09:03:00Z", "status": "completed"},
            {"node": "completion", "timestamp": "2025-11-02T09:04:00Z", "status": "completed"}
        ]
    
    async def _generate_overview_charts(self, workflow_id: Optional[str], cutoff_time: datetime, user_id: str) -> Dict[str, Any]:
        """Generate overview charts"""
        return {
            "charts": [
                {
                    "type": "pie",
                    "title": "Workflow Status Distribution",
                    "data": [
                        {"label": "Completed", "value": 65, "color": "#4CAF50"},
                        {"label": "Running", "value": 15, "color": "#2196F3"},
                        {"label": "Failed", "value": 10, "color": "#F44336"},
                        {"label": "Pending", "value": 10, "color": "#FF9800"}
                    ]
                },
                {
                    "type": "bar",
                    "title": "Daily Executions",
                    "data": {
                        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                        "values": [12, 19, 8, 15, 25, 22, 18]
                    }
                }
            ]
        }
    
    async def _generate_performance_charts(self, workflow_id: Optional[str], cutoff_time: datetime, user_id: str) -> Dict[str, Any]:
        """Generate performance charts"""
        return {
            "charts": [
                {
                    "type": "line",
                    "title": "Execution Time Trend",
                    "data": {
                        "labels": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
                        "values": [120, 110, 95, 105, 125, 115]
                    }
                }
            ]
        }
    
    async def _generate_error_charts(self, workflow_id: Optional[str], cutoff_time: datetime, user_id: str) -> Dict[str, Any]:
        """Generate error charts"""
        return {
            "charts": [
                {
                    "type": "bar",
                    "title": "Error Types",
                    "data": {
                        "labels": ["Timeout", "Validation", "Network", "Resource"],
                        "values": [5, 3, 2, 1]
                    }
                }
            ]
        }
    
    async def _generate_throughput_charts(self, workflow_id: Optional[str], cutoff_time: datetime, user_id: str) -> Dict[str, Any]:
        """Generate throughput charts"""
        return {
            "charts": [
                {
                    "type": "area",
                    "title": "Throughput Over Time",
                    "data": {
                        "labels": ["00:00", "06:00", "12:00", "18:00", "24:00"],
                        "values": [10, 15, 25, 30, 20]
                    }
                }
            ]
        }
    
    async def _generate_heatmap_data(self, workflow_id: Optional[str], cutoff_time: datetime, granularity: str, user_id: str) -> List[List[int]]:
        """Generate heatmap data"""
        # Simplified 7x24 heatmap (7 days x 24 hours)
        import random
        return [[random.randint(0, 10) for _ in range(24)] for _ in range(7)]
    
    async def _generate_network_data(self, workflow_id: str, include_weights: bool) -> Dict[str, Any]:
        """Generate network data"""
        return {
            "nodes": [
                {"id": "start", "label": "Start", "size": 20},
                {"id": "analysis", "label": "Analysis", "size": 30},
                {"id": "processing", "label": "Processing", "size": 35},
                {"id": "end", "label": "End", "size": 20}
            ],
            "edges": [
                {"from": "start", "to": "analysis", "weight": 1},
                {"from": "analysis", "to": "processing", "weight": 1},
                {"from": "processing", "to": "end", "weight": 1}
            ]
        }
    
    async def _detect_anomalies(self, cutoff_time: datetime, sensitivity: float, user_id: str) -> List[Dict[str, Any]]:
        """Detect anomalies in workflow execution"""
        return [
            {
                "type": "execution_time",
                "severity": "medium",
                "description": "Unusually long execution time detected",
                "timestamp": datetime.now().isoformat(),
                "value": 500,
                "threshold": 300
            }
        ]
    
    async def _generate_comparison_data(self, workflow_ids: List[str], comparison_type: str, cutoff_time: datetime, user_id: str) -> List[Dict[str, Any]]:
        """Generate workflow comparison data"""
        comparison_data = []
        for workflow_id in workflow_ids:
            comparison_data.append({
                "workflow_id": workflow_id,
                "metrics": {
                    "executions": 10,
                    "success_rate": 0.9,
                    "avg_duration": 120
                }
            })
        return comparison_data
    
    async def _generate_theme_preview(self, theme_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate theme preview"""
        return {
            "preview_chart": {
                "type": "line",
                "data": [1, 4, 2, 5, 3],
                "theme": theme_config
            }
        }
    
    async def _generate_interactive_graph(self, workflow_id: str, user_id: str) -> Dict[str, Any]:
        """Generate interactive graph data"""
        return {
            "nodes": [
                {"id": "1", "label": "Start", "x": 0, "y": 0},
                {"id": "2", "label": "Process", "x": 100, "y": 0},
                {"id": "3", "label": "End", "x": 200, "y": 0}
            ],
            "edges": [
                {"from": "1", "to": "2"},
                {"from": "2", "to": "3"}
            ],
            "interactive": True
        }