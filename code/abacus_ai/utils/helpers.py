"""
Utility functions for Abacus.AI integration
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import yaml
from pathlib import Path


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML or JSON file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
            return yaml.safe_load(f)
        elif config_path.suffix.lower() == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {config_path.suffix}")


def save_config(config: Dict[str, Any], config_path: str) -> None:
    """
    Save configuration to file
    
    Args:
        config: Configuration dictionary
        config_path: Path to save configuration
    """
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
            yaml.dump(config, f, default_flow_style=False, indent=2)
        else:
            json.dump(config, f, indent=2)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def validate_environment() -> Dict[str, Any]:
    """
    Validate environment and return status
    
    Returns:
        Environment status dictionary
    """
    status = {
        'timestamp': datetime.utcnow().isoformat(),
        'valid': True,
        'checks': {},
        'errors': [],
        'warnings': []
    }
    
    # Check required environment variables
    required_vars = ['ABACUS_AI_API_KEY']
    optional_vars = [
        'REDIS_HOST', 'REDIS_PORT', 'REDIS_DB', 'NEWS_API_KEY',
        'DOCKER_REGISTRY', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY'
    ]
    
    for var in required_vars:
        if os.getenv(var):
            status['checks'][var] = 'present'
        else:
            status['checks'][var] = 'missing'
            status['valid'] = False
            status['errors'].append(f"Required environment variable {var} is not set")
    
    for var in optional_vars:
        if os.getenv(var):
            status['checks'][var] = 'present'
        else:
            status['checks'][var] = 'missing'
            status['warnings'].append(f"Optional environment variable {var} is not set")
    
    # Check Python packages
    try:
        import redis
        status['checks']['redis'] = 'available'
    except ImportError:
        status['checks']['redis'] = 'missing'
        status['warnings'].append("Redis package not installed")
    
    try:
        import yfinance
        status['checks']['yfinance'] = 'available'
    except ImportError:
        status['checks']['yfinance'] = 'missing'
        status['warnings'].append("yfinance package not installed")
    
    try:
        import talib
        status['checks']['talib'] = 'available'
    except ImportError:
        status['checks']['talib'] = 'missing'
        status['warnings'].append("TA-Lib package not installed")
    
    try:
        import xgboost
        status['checks']['xgboost'] = 'available'
    except ImportError:
        status['checks']['xgboost'] = 'missing'
        status['warnings'].append("XGBoost package not installed")
    
    try:
        import lightgbm
        status['checks']['lightgbm'] = 'available'
    except ImportError:
        status['checks']['lightgbm'] = 'missing'
        status['warnings'].append("LightGBM package not installed")
    
    return status


def create_sample_config(output_path: str) -> None:
    """
    Create sample configuration file
    
    Args:
        output_path: Path to save sample configuration
    """
    sample_config = {
        "abacus_ai": {
            "api_key": "your-api-key-here",
            "base_url": "https://api.abacus.ai",
            "timeout": 30,
            "retries": 3
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": None
        },
        "model": {
            "algorithms": ["random_forest", "xgboost", "lightgbm"],
            "test_size": 0.2,
            "random_state": 42,
            "cv_folds": 5,
            "target_column": "future_return",
            "scaler": "standard"
        },
        "features": {
            "technical_indicators": {
                "rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "bb_period": 20,
                "bb_std": 2
            },
            "sentiment": {
                "enabled": True,
                "lookback_days": 7,
                "news_api_key": "your-news-api-key"
            }
        },
        "deployment": {
            "environment": "production",
            "scaling": {
                "min_instances": 1,
                "max_instances": 10
            },
            "resources": {
                "cpu": "1",
                "memory": "2Gi"
            }
        },
        "cache": {
            "strategy": "ttl",
            "max_memory": 104857600,
            "default_ttl": 300
        }
    }
    
    save_config(sample_config, output_path)
    print(f"Sample configuration saved to {output_path}")


def validate_data_quality(data: pd.DataFrame, target_column: str = None) -> Dict[str, Any]:
    """
    Validate data quality and return statistics
    
    Args:
        data: DataFrame to validate
        target_column: Name of target column
        
    Returns:
        Data quality report
    """
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'shape': data.shape,
        'columns': data.columns.tolist(),
        'dtypes': data.dtypes.to_dict(),
        'missing_values': {},
        'duplicate_rows': 0,
        'numeric_columns': [],
        'categorical_columns': [],
        'target_column_stats': {}
    }
    
    # Missing values
    for column in data.columns:
        missing_count = data[column].isnull().sum()
        missing_percent = (missing_count / len(data)) * 100
        report['missing_values'][column] = {
            'count': int(missing_count),
            'percentage': float(missing_percent)
        }
    
    # Duplicate rows
    report['duplicate_rows'] = int(data.duplicated().sum())
    
    # Column types
    numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
    
    report['numeric_columns'] = numeric_cols
    report['categorical_columns'] = categorical_cols
    
    # Target column statistics
    if target_column and target_column in data.columns:
        target_data = data[target_column].dropna()
        report['target_column_stats'] = {
            'count': len(target_data),
            'mean': float(target_data.mean()) if len(target_data) > 0 else 0,
            'std': float(target_data.std()) if len(target_data) > 0 else 0,
            'min': float(target_data.min()) if len(target_data) > 0 else 0,
            'max': float(target_data.max()) if len(target_data) > 0 else 0,
            'missing_values': int(data[target_column].isnull().sum())
        }
    
    return report


def save_data_quality_report(report: Dict[str, Any], output_path: str) -> None:
    """
    Save data quality report to file
    
    Args:
        report: Data quality report
        output_path: Output file path
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"Data quality report saved to {output_path}")


def format_model_comparison(models_results: Dict[str, Dict]) -> str:
    """
    Format model comparison results for display
    
    Args:
        models_results: Results from model training
        
    Returns:
        Formatted comparison string
    """
    if not models_results:
        return "No model results to compare"
    
    # Find best model
    best_model = None
    best_score = float('inf')
    
    for model_name, result in models_results.items():
        if 'error' not in result and 'test_metrics' in result:
            if result['test_metrics']['rmse'] < best_score:
                best_score = result['test_metrics']['rmse']
                best_model = model_name
    
    comparison_lines = [
        "Model Comparison Results",
        "=" * 50,
        f"Best Model: {best_model} (RMSE: {best_score:.6f})",
        ""
    ]
    
    comparison_lines.append(f"{'Model':<20} {'Train RMSE':<12} {'Test RMSE':<12} {'Test R²':<10} {'CV Score':<10}")
    comparison_lines.append("-" * 75)
    
    for model_name, result in models_results.items():
        if 'error' in result:
            line = f"{model_name:<20} {'ERROR':<12} {'-':<12} {'-':<10} {'-':<10}"
        else:
            train_rmse = result.get('train_metrics', {}).get('rmse', 0)
            test_rmse = result.get('test_metrics', {}).get('rmse', 0)
            test_r2 = result.get('test_metrics', {}).get('r2', 0)
            cv_score = result.get('cv_score', 0)
            
            line = f"{model_name:<20} {train_rmse:<12.6f} {test_rmse:<12.6f} {test_r2:<10.4f} {cv_score:<10.4f}"
        
        comparison_lines.append(line)
    
    return "\n".join(comparison_lines)


def export_model_results(results: Dict[str, Any], output_path: str, 
                        format: str = "json") -> None:
    """
    Export model training results
    
    Args:
        results: Model training results
        output_path: Output file path
        format: Export format (json, csv, excel)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format.lower() == "json":
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    elif format.lower() == "csv":
        # Convert results to DataFrame
        rows = []
        for model_name, result in results.items():
            if 'error' in result:
                rows.append({
                    'model': model_name,
                    'status': 'error',
                    'error': result['error']
                })
            else:
                row = {
                    'model': model_name,
                    'status': 'success',
                    'train_rmse': result.get('train_metrics', {}).get('rmse'),
                    'test_rmse': result.get('test_metrics', {}).get('rmse'),
                    'test_r2': result.get('test_metrics', {}).get('r2'),
                    'cv_score': result.get('cv_score'),
                    'cv_std': result.get('cv_std')
                }
                rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
    
    elif format.lower() == "excel":
        # Create Excel file with multiple sheets
        with pd.ExcelWriter(output_path) as writer:
            # Summary sheet
            summary_rows = []
            for model_name, result in results.items():
                if 'error' not in result:
                    summary_rows.append({
                        'Model': model_name,
                        'Train RMSE': result.get('train_metrics', {}).get('rmse'),
                        'Test RMSE': result.get('test_metrics', {}).get('rmse'),
                        'Test R²': result.get('test_metrics', {}).get('r2'),
                        'CV Score': result.get('cv_score'),
                        'CV Std': result.get('cv_std')
                    })
            
            if summary_rows:
                pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Summary', index=False)
            
            # Best model details
            if hasattr(results, 'get') and 'best_model' in results:
                best_model_details = results['best_model']
                if 'feature_importance' in best_model_details:
                    importance_df = pd.DataFrame(list(best_model_details['feature_importance'].items()),
                                               columns=['Feature', 'Importance'])
                    importance_df.to_excel(writer, sheet_name='Feature Importance', index=False)
    
    print(f"Model results exported to {output_path}")


def create_directory_structure(base_path: str) -> None:
    """
    Create standard directory structure for Abacus.AI integration
    
    Args:
        base_path: Base directory path
    """
    directories = [
        "data/raw",
        "data/processed",
        "data/features",
        "models/trained",
        "models/deployed",
        "logs",
        "config",
        "reports",
        "cache",
        "docs"
    ]
    
    base_path = Path(base_path)
    base_path.mkdir(parents=True, exist_ok=True)
    
    for directory in directories:
        (base_path / directory).mkdir(parents=True, exist_ok=True)
    
    print(f"Directory structure created at {base_path}")


def get_system_info() -> Dict[str, Any]:
    """
    Get system information
    
    Returns:
        System information dictionary
    """
    import sys
    import psutil
    
    info = {
        'python_version': sys.version,
        'platform': sys.platform,
        'cpu_count': psutil.cpu_count(),
        'memory_total': psutil.virtual_memory().total,
        'memory_available': psutil.virtual_memory().available,
        'disk_usage': dict(psutil.disk_usage('/')._asdict()),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return info


def monitor_api_health(base_url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Monitor API health
    
    Args:
        base_url: API base URL
        timeout: Request timeout
        
    Returns:
        Health status
    """
    import requests
    
    health_url = f"{base_url}/health"
    
    try:
        start_time = time.time()
        response = requests.get(health_url, timeout=timeout)
        response_time = time.time() - start_time
        
        return {
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'status_code': response.status_code,
            'response_time': response_time,
            'timestamp': datetime.utcnow().isoformat(),
            'url': health_url
        }
    
    except requests.exceptions.Timeout:
        return {
            'status': 'timeout',
            'error': 'Request timeout',
            'timestamp': datetime.utcnow().isoformat(),
            'url': health_url
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'url': health_url
        }