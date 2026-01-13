"""
ML Prediction Engineer Agent
Specializes in building and deploying machine learning models for trading predictions
"""
from typing import Dict, List, Optional, Any, Tuple
from crewai import Agent
from crewai_tools import BaseTool
from utils.memory_manager import memory_manager
from cache.cache_manager import cache_manager, PredictionCache
from config.settings import AgentPrompts
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import logging
import joblib
from datetime import datetime, timedelta


class FeatureEngineeringTool(BaseTool):
    """Tool for creating trading features"""
    name: str = "Feature Engineering Tool"
    description: str = "Creates technical indicators and trading features from price data"
    
    def _run(self, symbol: str, period: str = "2y") -> Dict[str, Any]:
        """Generate features for ML model"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty:
                return {"error": f"No data available for {symbol}"}
            
            # Technical indicators
            data['Returns'] = data['Close'].pct_change()
            data['SMA_5'] = data['Close'].rolling(window=5).mean()
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['SMA_50'] = data['Close'].rolling(window=50).mean()
            
            # Price ratios
            data['Close_SMA5_Ratio'] = data['Close'] / data['SMA_5']
            data['Close_SMA20_Ratio'] = data['Close'] / data['SMA_20']
            data['Close_SMA50_Ratio'] = data['Close'] / data['SMA_50']
            
            # Volatility
            data['Volatility_5'] = data['Returns'].rolling(window=5).std()
            data['Volatility_20'] = data['Returns'].rolling(window=20).std()
            
            # RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = data['Close'].ewm(span=12).mean()
            exp2 = data['Close'].ewm(span=26).mean()
            data['MACD'] = exp1 - exp2
            data['MACD_Signal'] = data['MACD'].ewm(span=9).mean()
            data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']
            
            # Volume indicators
            data['Volume_SMA'] = data['Volume'].rolling(window=20).mean()
            data['Volume_Ratio'] = data['Volume'] / data['Volume_SMA']
            
            # Bollinger Bands
            data['BB_Middle'] = data['Close'].rolling(window=20).mean()
            bb_std = data['Close'].rolling(window=20).std()
            data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
            data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)
            data['BB_Position'] = (data['Close'] - data['BB_Lower']) / (data['BB_Upper'] - data['BB_Lower'])
            
            # Price momentum
            data['Price_Momentum_5'] = data['Close'] / data['Close'].shift(5)
            data['Price_Momentum_10'] = data['Close'] / data['Close'].shift(10)
            
            # Target variable (next day return)
            data['Target'] = data['Returns'].shift(-1)
            
            # Remove NaN values
            data = data.dropna()
            
            # Select features for modeling
            feature_columns = [
                'Returns', 'Volatility_5', 'Volatility_20', 'RSI', 'MACD', 'MACD_Signal',
                'MACD_Histogram', 'Volume_Ratio', 'BB_Position', 'Price_Momentum_5', 'Price_Momentum_10',
                'Close_SMA5_Ratio', 'Close_SMA20_Ratio', 'Close_SMA50_Ratio'
            ]
            
            features = data[feature_columns].values
            target = data['Target'].values
            
            return {
                "symbol": symbol,
                "features": features.tolist(),
                "target": target.tolist(),
                "feature_names": feature_columns,
                "data_points": len(data),
                "date_range": {
                    "start": data.index[0].isoformat(),
                    "end": data.index[-1].isoformat()
                },
                "latest_features": data[feature_columns].iloc[-1].to_dict()
            }
            
        except Exception as e:
            logging.error(f"Error generating features for {symbol}: {e}")
            return {"error": str(e)}


class ModelTrainingTool(BaseTool):
    """Tool for training ML models"""
    name: str = "Model Training Tool"
    description: str = "Trains machine learning models for price prediction"
    
    def _run(self, symbol: str, features_data: Dict[str, Any], model_type: str = "random_forest") -> Dict[str, Any]:
        """Train prediction model"""
        try:
            if "error" in features_data:
                return features_data
            
            features = np.array(features_data["features"])
            target = np.array(features_data["target"])
            
            # Remove any remaining NaN values
            mask = ~(np.isnan(features).any(axis=1) | np.isnan(target))
            features = features[mask]
            target = target[mask]
            
            if len(features) < 100:
                return {"error": f"Insufficient data points for training: {len(features)}"}
            
            # Split data using time series split to avoid look-ahead bias
            split_idx = int(len(features) * 0.8)
            X_train, X_test = features[:split_idx], features[split_idx:]
            y_train, y_test = target[:split_idx], target[split_idx:]
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model based on type
            if model_type == "random_forest":
                model = RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42,
                    n_jobs=-1
                )
            elif model_type == "gradient_boosting":
                model = GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42
                )
            else:
                return {"error": f"Unsupported model type: {model_type}"}
            
            # Train model
            model.fit(X_train_scaled, y_train)
            
            # Make predictions
            train_pred = model.predict(X_train_scaled)
            test_pred = model.predict(X_test_scaled)
            
            # Calculate metrics
            train_mse = mean_squared_error(y_train, train_pred)
            test_mse = mean_squared_error(y_test, test_pred)
            train_mae = mean_absolute_error(y_train, train_pred)
            test_mae = mean_absolute_error(y_test, test_pred)
            train_r2 = r2_score(y_train, train_pred)
            test_r2 = r2_score(y_test, test_pred)
            
            # Feature importance
            feature_importance = dict(zip(
                features_data["feature_names"],
                model.feature_importances_
            ))
            
            # Sort by importance
            feature_importance = dict(sorted(feature_importance.items(), 
                                          key=lambda x: x[1], reverse=True))
            
            model_info = {
                "symbol": symbol,
                "model_type": model_type,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "metrics": {
                    "train_mse": float(train_mse),
                    "test_mse": float(test_mse),
                    "train_mae": float(train_mae),
                    "test_mae": float(test_mae),
                    "train_r2": float(train_r2),
                    "test_r2": float(test_r2)
                },
                "feature_importance": feature_importance,
                "model_params": model.get_params(),
                "timestamp": datetime.now().isoformat()
            }
            
            # Save model and scaler
            try:
                model_filename = f"models/{symbol}_{model_type}_model.joblib"
                scaler_filename = f"models/{symbol}_{model_type}_scaler.joblib"
                
                joblib.dump(model, model_filename)
                joblib.dump(scaler, scaler_filename)
                
                model_info["model_files"] = {
                    "model": model_filename,
                    "scaler": scaler_filename
                }
            except Exception as e:
                logging.warning(f"Could not save model files: {e}")
            
            return model_info
            
        except Exception as e:
            logging.error(f"Error training model for {symbol}: {e}")
            return {"error": str(e)}


class PredictionTool(BaseTool):
    """Tool for making predictions using trained models"""
    name: str = "Price Prediction Tool"
    description: str = "Makes price predictions using trained ML models"
    
    def _run(self, symbol: str, features_data: Dict[str, Any], model_type: str = "random_forest") -> Dict[str, Any]:
        """Make price prediction"""
        try:
            # Load model and scaler
            try:
                model = joblib.load(f"models/{symbol}_{model_type}_model.joblib")
                scaler = joblib.load(f"models/{symbol}_{model_type}_scaler.joblib")
            except Exception as e:
                return {"error": f"Could not load model for {symbol}: {e}"}
            
            # Prepare features
            latest_features = np.array([features_data["latest_features"][name] 
                                      for name in features_data["feature_names"]])
            
            # Scale features
            latest_features_scaled = scaler.transform(latest_features.reshape(1, -1))
            
            # Make prediction
            predicted_return = model.predict(latest_features_scaled)[0]
            
            # Get current price
            ticker = yf.Ticker(symbol)
            current_data = ticker.history(period="1d")
            current_price = float(current_data['Close'].iloc[-1])
            
            # Calculate predicted price
            predicted_price = current_price * (1 + predicted_return)
            
            # Calculate prediction confidence (using model uncertainty)
            # For RandomForest, we can use the variance of predictions
            if hasattr(model, 'estimators_'):
                tree_predictions = np.array([tree.predict(latest_features_scaled)[0] 
                                           for tree in model.estimators_])
                prediction_std = np.std(tree_predictions)
                confidence_interval = {
                    "lower": float(predicted_price * (1 - prediction_std)),
                    "upper": float(predicted_price * (1 + prediction_std))
                }
            else:
                confidence_interval = {
                    "lower": float(predicted_price * 0.98),
                    "upper": float(predicted_price * 1.02)
                }
            
            prediction = {
                "symbol": symbol,
                "model_type": model_type,
                "current_price": current_price,
                "predicted_return": float(predicted_return),
                "predicted_price": float(predicted_price),
                "confidence_interval": confidence_interval,
                "timestamp": datetime.now().isoformat()
            }
            
            return prediction
            
        except Exception as e:
            logging.error(f"Error making prediction for {symbol}: {e}")
            return {"error": str(e)}


class MLPredictionEngineer:
    """ML Prediction Engineer Agent"""
    
    def __init__(self, crew_id: str):
        self.crew_id = crew_id
        self.logger = logging.getLogger(__name__)
        self.prediction_cache = PredictionCache(cache_manager)
        
        # Create tools
        self.tools = [
            FeatureEngineeringTool(),
            ModelTrainingTool(),
            PredictionTool()
        ]
        
        # Create agent
        self.agent = Agent(
            role="ML Prediction Engineer",
            goal="Build accurate machine learning models for financial prediction and risk assessment",
            backstory="""You are an experienced ML engineer specializing in quantitative finance. You have expertise 
                        in feature engineering, time series modeling, and financial prediction. You excel at creating 
                        robust models that generalize well and provide reliable predictions for trading decisions.""",
            tools=self.tools,
            verbose=True,
            allow_delegation=False,
            max_iter=3,
            memory=True,
            cache=True,
            llm_config={
                "model": "gpt-4",
                "temperature": 0.3,
                "max_tokens": 2000
            }
        )
    
    async def build_prediction_model(self, symbol: str, model_type: str = "random_forest") -> Dict[str, Any]:
        """Build and train prediction model for a symbol"""
        try:
            # Get features with caching
            features_data = self.prediction_cache.get_prediction("features", symbol, "default")
            if not features_data:
                features_data = self.tools[0]._run(symbol)
                self.prediction_cache.cache_prediction("features", symbol, "default", features_data)
            
            if "error" in features_data:
                return features_data
            
            # Train model
            model_info = self.tools[1]._run(symbol, features_data, model_type)
            
            if "error" not in model_info:
                # Store model info in memory
                await memory_manager.store_agent_memory(
                    self.crew_id, 
                    "ml_prediction_engineer", 
                    f"model_{symbol}_{model_type}", 
                    model_info
                )
            
            return model_info
            
        except Exception as e:
            self.logger.error(f"Error building model for {symbol}: {e}")
            return {"error": str(e)}
    
    async def make_prediction(self, symbol: str, model_type: str = "random_forest") -> Dict[str, Any]:
        """Make prediction using trained model"""
        try:
            # Get latest features
            features_data = self.prediction_cache.get_prediction("features", symbol, "default")
            if not features_data:
                features_data = self.tools[0]._run(symbol)
                self.prediction_cache.cache_prediction("features", symbol, "default", features_data)
            
            if "error" in features_data:
                return features_data
            
            # Make prediction
            prediction = self.tools[2]._run(symbol, features_data, model_type)
            
            if "error" not in prediction:
                # Cache prediction
                await self.prediction_cache.cache_prediction(model_type, symbol, "1d", prediction)
                
                # Store in memory
                await memory_manager.store_agent_memory(
                    self.crew_id, 
                    "ml_prediction_engineer", 
                    f"prediction_{symbol}_{model_type}", 
                    prediction
                )
            
            return prediction
            
        except Exception as e:
            self.logger.error(f"Error making prediction for {symbol}: {e}")
            return {"error": str(e)}
    
    async def backtest_strategy(self, symbol: str, model_type: str = "random_forest", 
                              start_date: str = None) -> Dict[str, Any]:
        """Backtest prediction strategy"""
        try:
            # Set default start date if not provided
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            
            # Get historical data
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date)
            
            if data.empty:
                return {"error": f"No data available for {symbol} from {start_date}"}
            
            # Generate features
            features_data = self.tools[0]._run(symbol, "3y")
            if "error" in features_data:
                return features_data
            
            # Train model on historical data
            model_info = self.tools[1]._run(symbol, features_data, model_type)
            if "error" in model_info:
                return model_info
            
            # Simulate trading based on predictions
            capital = 100000  # Starting capital
            positions = []
            portfolio_value = [capital]
            trades = []
            
            features = np.array(features_data["features"])
            target = np.array(features_data["target"])
            feature_names = features_data["feature_names"]
            
            # Remove NaN values
            mask = ~(np.isnan(features).any(axis=1) | np.isnan(target))
            features = features[mask]
            target = target[mask]
            
            if len(features) < 100:
                return {"error": f"Insufficient data for backtesting: {len(features)}"}
            
            # Load model
            try:
                model = joblib.load(f"models/{symbol}_{model_type}_model.joblib")
                scaler = joblib.load(f"models/{symbol}_{model_type}_scaler.joblib")
            except Exception as e:
                return {"error": f"Could not load model for backtesting: {e}"}
            
            # Run backtest
            for i in range(50, len(features)):  # Start after enough data for features
                # Prepare features for prediction
                current_features = features[i].reshape(1, -1)
                current_features_scaled = scaler.transform(current_features)
                
                # Make prediction
                predicted_return = model.predict(current_features_scaled)[0]
                actual_return = target[i]
                
                # Simple trading strategy: buy if prediction > 0.01, sell if < -0.01
                signal = 0
                if predicted_return > 0.01:
                    signal = 1  # Buy
                elif predicted_return < -0.01:
                    signal = -1  # Sell
                
                # Track position
                if signal != 0 and i > 0:
                    entry_price = data['Close'].iloc[i-50+i] if i-50+i < len(data) else data['Close'].iloc[-1]
                    exit_price = data['Close'].iloc[i-50+i+1] if i-50+i+1 < len(data) else data['Close'].iloc[-1]
                    
                    trade_return = (exit_price - entry_price) / entry_price * signal
                    capital *= (1 + trade_return)
                    
                    trades.append({
                        "date": data.index[i-50+i].isoformat(),
                        "signal": signal,
                        "predicted_return": predicted_return,
                        "actual_return": actual_return,
                        "trade_return": trade_return,
                        "capital": capital
                    })
                
                portfolio_value.append(capital)
            
            # Calculate performance metrics
            total_return = (portfolio_value[-1] - portfolio_value[0]) / portfolio_value[0]
            returns_array = np.diff(portfolio_value) / portfolio_value[:-1]
            sharpe_ratio = np.mean(returns_array) / np.std(returns_array) * np.sqrt(252) if np.std(returns_array) > 0 else 0
            max_drawdown = np.min((np.array(portfolio_value) - np.maximum.accumulate(portfolio_value)) / np.maximum.accumulate(portfolio_value))
            
            backtest_results = {
                "symbol": symbol,
                "model_type": model_type,
                "period": {"start": start_date, "end": datetime.now().strftime("%Y-%m-%d")},
                "performance": {
                    "total_return": float(total_return),
                    "sharpe_ratio": float(sharpe_ratio),
                    "max_drawdown": float(max_drawdown),
                    "final_capital": float(capital),
                    "num_trades": len(trades)
                },
                "trades": trades[-10:],  # Last 10 trades
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache and store results
            await self.prediction_cache.cache_backtest_results(model_type, symbol, backtest_results)
            
            await memory_manager.store_agent_memory(
                self.crew_id, 
                "ml_prediction_engineer", 
                f"backtest_{symbol}_{model_type}", 
                backtest_results
            )
            
            return backtest_results
            
        except Exception as e:
            self.logger.error(f"Error backtesting strategy for {symbol}: {e}")
            return {"error": str(e)}
    
    async def get_model_performance(self, symbol: str, model_type: str = "random_forest") -> Dict[str, Any]:
        """Get performance metrics for trained model"""
        try:
            model_info = await memory_manager.get_agent_memory(
                self.crew_id, 
                "ml_prediction_engineer", 
                f"model_{symbol}_{model_type}"
            )
            
            return model_info or {"error": f"No model information found for {symbol}"}
            
        except Exception as e:
            self.logger.error(f"Error getting model performance for {symbol}: {e}")
            return {"error": str(e)}
    
    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance"""
        return self.agent


# Example usage function
async def create_ml_prediction_engineer(crew_id: str) -> MLPredictionEngineer:
    """Factory function to create ML Prediction Engineer"""
    engineer = MLPredictionEngineer(crew_id)
    
    # Initialize memory connections
    await memory_manager.connect()
    
    return engineer