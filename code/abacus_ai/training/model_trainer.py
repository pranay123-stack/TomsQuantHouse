"""
Automated Model Training Pipeline for Return Prediction
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import joblib
import json
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.pipeline import Pipeline
import xgboost as xgb
import lightgbm as lgb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """Automated model training pipeline for return prediction"""
    
    def __init__(self, client, config: Dict[str, Any] = None):
        """
        Initialize model trainer
        
        Args:
            client: Abacus.AI client instance
            config: Training configuration
        """
        self.client = client
        self.config = config or self._get_default_config()
        self.models = {}
        self.scalers = {}
        self.best_model = None
        self.best_score = float('inf')
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default training configuration"""
        return {
            "test_size": 0.2,
            "random_state": 42,
            "cv_folds": 5,
            "models": {
                "random_forest": {
                    "algorithm": "random_forest",
                    "params": {
                        "n_estimators": [100, 200, 300],
                        "max_depth": [10, 20, None],
                        "min_samples_split": [2, 5, 10]
                    }
                },
                "gradient_boosting": {
                    "algorithm": "gradient_boosting",
                    "params": {
                        "n_estimators": [100, 200],
                        "max_depth": [3, 5, 7],
                        "learning_rate": [0.01, 0.1, 0.2]
                    }
                },
                "xgboost": {
                    "algorithm": "xgboost",
                    "params": {
                        "n_estimators": [100, 200],
                        "max_depth": [3, 5, 7],
                        "learning_rate": [0.01, 0.1, 0.2],
                        "subsample": [0.8, 1.0]
                    }
                },
                "lightgbm": {
                    "algorithm": "lightgbm",
                    "params": {
                        "n_estimators": [100, 200],
                        "max_depth": [3, 5, 7],
                        "learning_rate": [0.01, 0.1, 0.2],
                        "subsample": [0.8, 1.0]
                    }
                }
            },
            "scaler": "standard",  # standard, minmax, or none
            "target_column": "future_return",
            "feature_columns": None  # Auto-detect if not specified
        }
    
    def prepare_features(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features and target for training
        
        Args:
            data: Input data
            
        Returns:
            Features and target
        """
        logger.info("Preparing features for training")
        
        # Identify feature columns (exclude target and ID columns)
        if self.config["feature_columns"]:
            feature_cols = self.config["feature_columns"]
        else:
            exclude_cols = [self.config["target_column"], "id", "symbol", "date", "timestamp"]
            feature_cols = [col for col in data.columns if col not in exclude_cols]
        
        # Handle missing values
        data_clean = data.copy()
        
        # Fill numeric columns with median
        numeric_cols = data_clean.select_dtypes(include=[np.number]).columns
        data_clean[numeric_cols] = data_clean[numeric_cols].fillna(
            data_clean[numeric_cols].median()
        )
        
        # Fill categorical columns with mode
        categorical_cols = data_clean.select_dtypes(include=["object"]).columns
        for col in categorical_cols:
            if col not in exclude_cols:
                data_clean[col] = data_clean[col].fillna(data_clean[col].mode()[0] if not data_clean[col].mode().empty else "unknown")
        
        X = data_clean[feature_cols]
        y = data_clean[self.config["target_column"]]
        
        logger.info(f"Prepared {len(feature_cols)} features for {len(data_clean)} samples")
        return X, y
    
    def _get_model(self, algorithm: str) -> Any:
        """Get model instance based on algorithm"""
        if algorithm == "random_forest":
            return RandomForestRegressor(random_state=self.config["random_state"])
        elif algorithm == "gradient_boosting":
            return GradientBoostingRegressor(random_state=self.config["random_state"])
        elif algorithm == "xgboost":
            return xgb.XGBRegressor(random_state=self.config["random_state"])
        elif algorithm == "lightgbm":
            return lgb.LGBMRegressor(random_state=self.config["random_state"], verbose=-1)
        elif algorithm == "linear_regression":
            return LinearRegression()
        elif algorithm == "ridge":
            return Ridge(random_state=self.config["random_state"])
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def _get_scaler(self, scaler_type: str):
        """Get scaler instance"""
        if scaler_type == "standard":
            return StandardScaler()
        elif scaler_type == "minmax":
            return MinMaxScaler()
        else:
            return None
    
    def train_models(self, data: pd.DataFrame, validation_split: bool = True) -> Dict[str, Dict]:
        """
        Train multiple models and select the best one
        
        Args:
            data: Training data
            validation_split: Whether to split data for validation
            
        Returns:
            Training results for all models
        """
        logger.info("Starting model training pipeline")
        
        # Prepare features
        X, y = self.prepare_features(data)
        
        # Split data
        if validation_split:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config["test_size"], 
                random_state=self.config["random_state"]
            )
        else:
            X_train, X_test, y_train, y_test = X, X, y, y
        
        training_results = {}
        
        # Train each model
        for model_name, model_config in self.config["models"].items():
            logger.info(f"Training {model_name}")
            
            try:
                # Create pipeline with scaler and model
                scaler = self._get_scaler(self.config["scaler"])
                model = self._get_model(model_config["algorithm"])
                
                if scaler:
                    pipeline = Pipeline([("scaler", scaler), ("model", model)])
                else:
                    pipeline = Pipeline([("model", model)])
                
                # Hyperparameter tuning
                if "params" in model_config:
                    logger.info(f"Performing hyperparameter tuning for {model_name}")
                    grid_search = GridSearchCV(
                        pipeline, 
                        model_config["params"], 
                        cv=self.config["cv_folds"],
                        scoring="neg_mean_squared_error",
                        n_jobs=-1,
                        verbose=0
                    )
                    grid_search.fit(X_train, y_train)
                    best_pipeline = grid_search.best_estimator_
                    best_params = grid_search.best_params_
                else:
                    best_pipeline = pipeline
                    best_pipeline.fit(X_train, y_train)
                    best_params = {}
                
                # Evaluate model
                y_pred_train = best_pipeline.predict(X_train)
                y_pred_test = best_pipeline.predict(X_test)
                
                train_metrics = self._calculate_metrics(y_train, y_pred_train)
                test_metrics = self._calculate_metrics(y_test, y_pred_test)
                
                # Cross-validation score
                cv_scores = cross_val_score(
                    best_pipeline, X_train, y_train, 
                    cv=self.config["cv_folds"], scoring="neg_mean_squared_error"
                )
                
                training_results[model_name] = {
                    "model": best_pipeline,
                    "best_params": best_params,
                    "train_metrics": train_metrics,
                    "test_metrics": test_metrics,
                    "cv_score": -cv_scores.mean(),
                    "cv_std": cv_scores.std()
                }
                
                # Update best model if this one is better
                if test_metrics["rmse"] < self.best_score:
                    self.best_score = test_metrics["rmse"]
                    self.best_model = best_pipeline
                    self.best_model_name = model_name
                
                logger.info(f"{model_name} - Train RMSE: {train_metrics['rmse']:.6f}, "
                           f"Test RMSE: {test_metrics['rmse']:.6f}")
                
            except Exception as e:
                logger.error(f"Failed to train {model_name}: {str(e)}")
                training_results[model_name] = {"error": str(e)}
        
        logger.info(f"Best model: {self.best_model_name} with RMSE: {self.best_score:.6f}")
        return training_results
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate regression metrics"""
        return {
            "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
            "mae": mean_absolute_error(y_true, y_pred),
            "r2": r2_score(y_true, y_pred),
            "mape": np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        }
    
    def save_model(self, filepath: str) -> None:
        """
        Save the best model
        
        Args:
            filepath: Path to save the model
        """
        if self.best_model is None:
            raise ValueError("No trained model to save")
        
        model_data = {
            "model": self.best_model,
            "model_name": self.best_model_name,
            "score": self.best_score,
            "config": self.config,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"Best model saved to {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """
        Load a saved model
        
        Args:
            filepath: Path to the saved model
        """
        model_data = joblib.load(filepath)
        
        self.best_model = model_data["model"]
        self.best_model_name = model_data["model_name"]
        self.best_score = model_data["score"]
        self.config = model_data["config"]
        
        logger.info(f"Model loaded from {filepath}")
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions using the best model
        
        Args:
            X: Features for prediction
            
        Returns:
            Predictions
        """
        if self.best_model is None:
            raise ValueError("No trained model available")
        
        return self.best_model.predict(X)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance from the best model
        
        Returns:
            Feature importance scores
        """
        if self.best_model is None:
            raise ValueError("No trained model available")
        
        model = self.best_model.named_steps['model']
        
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
        elif hasattr(model, 'coef_'):
            importance = np.abs(model.coef_)
        else:
            raise ValueError("Model does not support feature importance")
        
        # Get feature names
        if hasattr(self.best_model, 'named_steps') and 'scaler' in self.best_model.named_steps:
            # Pipeline with scaler - get original feature names
            feature_names = None  # Would need to be passed in
        else:
            feature_names = None  # Would need to be passed in
        
        return dict(zip(range(len(importance)), importance.tolist()))


class ModelEvaluator:
    """Evaluate model performance and generate reports"""
    
    def __init__(self, trainer: ModelTrainer):
        self.trainer = trainer
    
    def generate_report(self, training_results: Dict[str, Dict]) -> Dict[str, Any]:
        """Generate comprehensive model evaluation report"""
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "best_model": {
                "name": self.trainer.best_model_name,
                "score": self.trainer.best_score
            },
            "all_models": {},
            "comparison": {}
        }
        
        # Process each model
        for model_name, result in training_results.items():
            if "error" in result:
                continue
                
            report["all_models"][model_name] = {
                "test_rmse": result["test_metrics"]["rmse"],
                "test_r2": result["test_metrics"]["r2"],
                "cv_score": result["cv_score"],
                "best_params": result["best_params"]
            }
        
        # Find best and worst models
        if report["all_models"]:
            rmse_scores = {name: data["test_rmse"] for name, data in report["all_models"].items()}
            best_model = min(rmse_scores.keys(), key=lambda k: rmse_scores[k])
            worst_model = max(rmse_scores.keys(), key=lambda k: rmse_scores[k])
            
            report["comparison"] = {
                "best_model": best_model,
                "worst_model": worst_model,
                "improvement": rmse_scores[worst_model] - rmse_scores[best_model]
            }
        
        return report
    
    def save_report(self, report: Dict[str, Any], filepath: str) -> None:
        """Save evaluation report to file"""
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Evaluation report saved to {filepath}")