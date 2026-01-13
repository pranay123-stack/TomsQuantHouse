"""
Unit tests for ML Prediction Engineer Agent
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import joblib
import tempfile
import os

# Import the agent
from agents.ml_prediction_engineer import MLPredictionEngineer
from config.settings import TradingSettings


class TestMLPredictionEngineer:
    """Test cases for ML Prediction Engineer"""
    
    @pytest.fixture
    def ml_engineer(self):
        """Create ML Prediction Engineer instance"""
        return MLPredictionEngineer()
    
    @pytest.fixture
    def mock_tools(self):
        """Mock tools for testing"""
        with patch('agents.ml_prediction_engineer.FeatureEngineeringTool') as mock_feature_tool, \
             patch('agents.ml_prediction_engineer.ModelTrainingTool') as mock_training_tool, \
             patch('agents.ml_prediction_engineer.PredictionTool') as mock_prediction_tool, \
             patch('agents.ml_prediction_engineer.BacktestingTool') as mock_backtesting_tool:
            
            # Configure mock feature engineering tool
            mock_feature_tool.return_value.run = AsyncMock(return_value={
                'features': np.random.random((100, 20)),
                'feature_names': [f'feature_{i}' for i in range(20)],
                'feature_importance': np.random.random(20),
                'correlation_matrix': np.random.random((20, 20))
            })
            
            # Configure mock model training tool
            mock_training_tool.return_value.run = AsyncMock(return_value={
                'model': Mock(),
                'training_metrics': {
                    'accuracy': 0.87,
                    'precision': 0.85,
                    'recall': 0.83,
                    'f1_score': 0.84,
                    'mse': 0.02,
                    'mae': 0.01
                },
                'cross_validation_score': 0.82,
                'feature_importance': np.random.random(20),
                'model_params': {'n_estimators': 100, 'max_depth': 10}
            })
            
            # Configure mock prediction tool
            mock_prediction_tool.return_value.run = AsyncMock(return_value={
                'predictions': np.random.random(10),
                'confidence_intervals': np.random.random((10, 2)),
                'feature_importance': np.random.random(20),
                'model_explanation': {
                    'shap_values': np.random.random((10, 20)),
                    'lime_explanation': 'Feature X1 contributes positively to prediction'
                }
            })
            
            # Configure mock backtesting tool
            mock_backtesting_tool.return_value.run = AsyncMock(return_value={
                'performance_metrics': {
                    'total_return': 0.25,
                    'sharpe_ratio': 1.5,
                    'max_drawdown': 0.15,
                    'win_rate': 0.65,
                    'avg_win': 0.08,
                    'avg_loss': 0.03
                },
                'trades': [
                    {'date': '2024-01-01', 'action': 'buy', 'return': 0.05},
                    {'date': '2024-01-02', 'action': 'sell', 'return': -0.02}
                ],
                'equity_curve': np.random.random(252)
            })
            
            yield {
                'feature': mock_feature_tool.return_value,
                'training': mock_training_tool.return_value,
                'prediction': mock_prediction_tool.return_value,
                'backtesting': mock_backtesting_tool.return_value
            }
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, ml_engineer):
        """Test agent initialization"""
        assert ml_engineer.name == "ML Prediction Engineer"
        assert ml_engineer.role == "Machine Learning & Prediction Specialist"
        assert len(ml_engineer.tools) > 0
        
        # Check that all expected tools are present
        tool_names = [tool.__class__.__name__ for tool in ml_engineer.tools]
        expected_tools = [
            'FeatureEngineeringTool', 
            'ModelTrainingTool', 
            'PredictionTool', 
            'BacktestingTool'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    async def test_predict_price_movement(self, ml_engineer, mock_tools):
        """Test price movement prediction"""
        prediction_request = {
            'symbol': 'AAPL',
            'prediction_horizon': 5,  # 5 days
            'model_type': 'random_forest',
            'features': ['price', 'volume', 'rsi', 'macd']
        }
        
        result = await ml_engineer.predict_price_movement(prediction_request)
        
        # Verify structure
        assert 'symbol' in result
        assert 'prediction_horizon' in result
        assert 'predictions' in result
        assert 'confidence' in result
        assert 'model_info' in result
        
        # Verify values
        assert len(result['predictions']) == 5
        assert 0 <= result['confidence'] <= 1
        assert 'model_type' in result['model_info']
    
    @pytest.mark.asyncio
    async def test_engineer_features(self, ml_engineer, mock_tools):
        """Test feature engineering"""
        feature_request = {
            'symbol': 'MSFT',
            'data_source': 'market_data',
            'feature_types': ['technical', 'fundamental', 'sentiment'],
            'lookback_period': 60
        }
        
        result = await ml_engineer.engineer_features(feature_request)
        
        # Verify structure
        assert 'features' in result
        assert 'feature_names' in result
        assert 'feature_importance' in result
        assert 'data_quality' in result
        
        # Verify values
        assert isinstance(result['features'], np.ndarray)
        assert len(result['feature_names']) == result['features'].shape[1]
        assert len(result['feature_importance']) == result['features'].shape[1]
        assert 0 <= result['data_quality']['completeness'] <= 1
    
    @pytest.mark.asyncio
    async def test_train_model(self, ml_engineer, mock_tools):
        """Test model training"""
        training_request = {
            'model_type': 'gradient_boosting',
            'target_variable': 'price_return',
            'feature_matrix': np.random.random((100, 20)),
            'target_vector': np.random.random(100),
            'hyperparameters': {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1
            }
        }
        
        result = await ml_engineer.train_model(training_request)
        
        # Verify structure
        assert 'model' in result
        assert 'training_metrics' in result
        assert 'cross_validation_score' in result
        assert 'feature_importance' in result
        assert 'model_params' in result
        
        # Verify metrics
        metrics = result['training_metrics']
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        
        # Verify score ranges
        assert 0 <= result['cross_validation_score'] <= 1
    
    @pytest.mark.asyncio
    async def test_generate_signals(self, ml_engineer, mock_tools):
        """Test signal generation"""
        signal_request = {
            'model': Mock(),
            'latest_data': np.random.random((1, 20)),
            'threshold': 0.7,
            'signal_types': ['buy', 'sell', 'hold']
        }
        
        result = await ml_engineer.generate_signals(signal_request)
        
        # Verify structure
        assert 'signals' in result
        assert 'confidence' in result
        assert 'position_size' in result
        assert 'execution_priority' in result
        
        # Verify signal values
        signals = result['signals']
        assert signal_request['signal_types'] == sorted(signals.keys())
        for signal_type in signals:
            assert signals[signal_type] >= 0
    
    @pytest.mark.asyncio
    async def test_backtest_strategy(self, ml_engineer, mock_tools):
        """Test strategy backtesting"""
        backtest_request = {
            'strategy': Mock(),
            'historical_data': np.random.random((252, 20)),
            'start_date': '2023-01-01',
            'end_date': '2024-01-01',
            'initial_capital': 100000,
            'transaction_costs': 0.001
        }
        
        result = await ml_engineer.backtest_strategy(backtest_request)
        
        # Verify structure
        assert 'performance_metrics' in result
        assert 'trades' in result
        assert 'equity_curve' in result
        assert 'risk_metrics' in result
        
        # Verify metrics
        metrics = result['performance_metrics']
        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'win_rate' in metrics
        
        # Verify equity curve
        assert len(result['equity_curve']) == 252
        assert all(isinstance(x, (int, float)) for x in result['equity_curve'])
    
    @pytest.mark.asyncio
    async def test_model_evaluation(self, ml_engineer, mock_tools):
        """Test model evaluation"""
        evaluation_request = {
            'model': Mock(),
            'test_data': np.random.random((50, 20)),
            'test_targets': np.random.random(50),
            'evaluation_metrics': ['accuracy', 'precision', 'recall', 'f1_score', 'mse']
        }
        
        result = await ml_engineer.model_evaluation(evaluation_request)
        
        # Verify structure
        assert 'evaluation_metrics' in result
        assert 'confusion_matrix' in result
        assert 'feature_importance' in result
        assert 'model_interpretation' in result
        
        # Verify metrics
        metrics = result['evaluation_metrics']
        for metric in evaluation_request['evaluation_metrics']:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))
    
    @pytest.mark.asyncio
    async def test_ensemble_prediction(self, ml_engineer, mock_tools):
        """Test ensemble prediction"""
        ensemble_request = {
            'models': {
                'random_forest': Mock(),
                'gradient_boosting': Mock(),
                'neural_network': Mock()
            },
            'data': np.random.random((10, 20)),
            'ensemble_method': 'voting',
            'weights': [0.4, 0.4, 0.2]
        }
        
        # Configure mock predictions for each model
        mock_tools['prediction'].run.side_effect = [
            {'predictions': np.random.random(10), 'confidence': 0.8},
            {'predictions': np.random.random(10), 'confidence': 0.85},
            {'predictions': np.random.random(10), 'confidence': 0.75}
        ]
        
        result = await ml_engineer.ensemble_prediction(ensemble_request)
        
        # Verify structure
        assert 'ensemble_prediction' in result
        assert 'individual_predictions' in result
        assert 'confidence' in result
        assert 'ensemble_method' in result
        
        # Verify ensemble prediction
        assert len(result['individual_predictions']) == 3
        assert result['ensemble_method'] == 'voting'
    
    @pytest.mark.asyncio
    async def test_feature_selection(self, ml_engineer, mock_tools):
        """Test feature selection"""
        selection_request = {
            'feature_matrix': np.random.random((100, 30)),
            'target_vector': np.random.random(100),
            'selection_method': 'mutual_info',
            'max_features': 15,
            'threshold': 0.01
        }
        
        result = await ml_engineer.feature_selection(selection_request)
        
        # Verify structure
        assert 'selected_features' in result
        assert 'feature_scores' in result
        assert 'selection_method' in result
        assert 'performance_impact' in result
        
        # Verify selected features
        assert len(result['selected_features']) <= selection_request['max_features']
        assert all(score >= 0 for score in result['feature_scores'].values())
    
    @pytest.mark.asyncio
    async def test_hyperparameter_optimization(self, ml_engineer, mock_tools):
        """Test hyperparameter optimization"""
        optimization_request = {
            'model_type': 'random_forest',
            'parameter_space': {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, 15, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            },
            'optimization_metric': 'accuracy',
            'cv_folds': 5
        }
        
        result = await ml_engineer.hyperparameter_optimization(optimization_request)
        
        # Verify structure
        assert 'best_params' in result
        assert 'best_score' in result
        assert 'optimization_results' in result
        assert 'performance_curve' in result
        
        # Verify best parameters
        best_params = result['best_params']
        assert 'n_estimators' in best_params
        assert 'max_depth' in best_params
        assert result['best_score'] >= 0
    
    @pytest.mark.asyncio
    async def test_model_ensemble_creation(self, ml_engineer, mock_tools):
        """Test model ensemble creation"""
        ensemble_creation_request = {
            'base_models': [
                {'type': 'random_forest', 'params': {}},
                {'type': 'gradient_boosting', 'params': {}},
                {'type': 'svm', 'params': {}}
            ],
            'ensemble_method': 'stacking',
            'meta_model': 'linear_regression'
        }
        
        result = await ml_engineer.model_ensemble_creation(ensemble_creation_request)
        
        # Verify structure
        assert 'ensemble_model' in result
        assert 'individual_models' in result
        assert 'meta_model' in result
        assert 'ensemble_performance' in result
        
        # Verify ensemble components
        assert len(result['individual_models']) == 3
        assert result['meta_model']['type'] == 'linear_regression'
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_data(self, ml_engineer):
        """Test error handling for invalid data"""
        # Test with empty feature matrix
        with pytest.raises(ValueError):
            await ml_engineer.train_model({
                'model_type': 'random_forest',
                'feature_matrix': np.array([]),
                'target_vector': np.array([])
            })
        
        # Test with mismatched dimensions
        with pytest.raises(ValueError):
            await ml_engineer.predict_price_movement({
                'symbol': 'AAPL',
                'model': Mock(),
                'data': np.random.random((5, 10)),
                'target': np.random.random(10)  # Wrong size
            })
    
    @pytest.mark.asyncio
    async def test_error_handling_model_failure(self, ml_engineer, mock_tools):
        """Test error handling for model failures"""
        # Configure mock to raise exception
        mock_tools['training'].run.side_effect = Exception("Model training failed")
        
        training_request = {
            'model_type': 'invalid_model',
            'feature_matrix': np.random.random((100, 20)),
            'target_vector': np.random.random(100)
        }
        
        with pytest.raises(Exception, match="Model training failed"):
            await ml_engineer.train_model(training_request)
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, ml_engineer, performance_monitor):
        """Test performance metrics"""
        performance_monitor.start()
        
        # Simulate ML operation
        await asyncio.sleep(0.01)
        
        execution_time = performance_monitor.stop()
        
        # Should complete within reasonable time
        assert execution_time < 1.0
    
    @pytest.mark.asyncio
    async def test_concurrent_predictions(self, ml_engineer):
        """Test concurrent predictions"""
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        
        with patch.object(ml_engineer, 'predict_price_movement') as mock_predict:
            mock_predict.side_effect = lambda req: {
                'symbol': req['symbol'],
                'predictions': np.random.random(5),
                'confidence': 0.8
            }
            
            results = await asyncio.gather(*[
                ml_engineer.predict_price_movement({'symbol': symbol}) 
                for symbol in symbols
            ])
            
            # Verify all predictions completed
            assert len(results) == 4
            for i, result in enumerate(results):
                assert result['symbol'] == symbols[i]
                assert len(result['predictions']) == 5
    
    @pytest.mark.asyncio
    async def test_model_saving_loading(self, ml_engineer, mock_tools):
        """Test model persistence"""
        # Create temporary directory for model storage
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = os.path.join(temp_dir, 'test_model.pkl')
            
            # Mock model
            mock_model = Mock()
            mock_model.predict = Mock(return_value=np.random.random(10))
            
            # Test saving
            result = await ml_engineer.save_model(mock_model, model_path)
            assert result['success'] is True
            assert 'model_path' in result
            
            # Test loading
            with patch('joblib.load') as mock_load:
                mock_load.return_value = mock_model
                loaded_result = await ml_engineer.load_model(model_path)
                assert loaded_result['success'] is True
                assert 'model' in loaded_result
    
    @pytest.mark.asyncio
    async def test_cross_validation(self, ml_engineer, mock_tools):
        """Test cross-validation functionality"""
        cv_request = {
            'model': Mock(),
            'feature_matrix': np.random.random((100, 20)),
            'target_vector': np.random.random(100),
            'cv_method': 'time_series',
            'cv_folds': 5,
            'scoring': 'accuracy'
        }
        
        result = await ml_engineer.cross_validation(cv_request)
        
        # Verify structure
        assert 'cv_scores' in result
        assert 'mean_score' in result
        assert 'std_score' in result
        assert 'fold_details' in result
        
        # Verify scores
        assert len(result['cv_scores']) == 5
        assert result['mean_score'] >= 0
        assert result['std_score'] >= 0
    
    @pytest.mark.asyncio
    async def test_feature_importance_analysis(self, ml_engineer, mock_tools):
        """Test feature importance analysis"""
        importance_request = {
            'model': Mock(),
            'feature_names': [f'feature_{i}' for i in range(20)],
            'analysis_method': 'shap',
            'sample_data': np.random.random((10, 20))
        }
        
        result = await ml_engineer.feature_importance_analysis(importance_request)
        
        # Verify structure
        assert 'importance_scores' in result
        assert 'feature_ranking' in result
        assert 'interpretation' in result
        assert 'top_features' in result
        
        # Verify ranking
        ranking = result['feature_ranking']
        assert len(ranking) == 20
        assert all(isinstance(feature, str) for feature in ranking)
    
    @pytest.mark.asyncio
    async def test_prediction_uncertainty_quantification(self, ml_engineer, mock_tools):
        """Test prediction uncertainty quantification"""
        uncertainty_request = {
            'model': Mock(),
            'data': np.random.random((10, 20)),
            'method': 'monte_carlo',
            'n_simulations': 100,
            'confidence_levels': [0.68, 0.95, 0.99]
        }
        
        result = await ml_engineer.prediction_uncertainty_quantification(uncertainty_request)
        
        # Verify structure
        assert 'predictions' in result
        assert 'uncertainty_bounds' in result
        assert 'confidence_intervals' in result
        assert 'prediction_std' in result
        
        # Verify bounds
        bounds = result['uncertainty_bounds']
        assert len(bounds) == len(uncertainty_request['confidence_levels'])
        for level in bounds:
            assert 'lower' in level
            assert 'upper' in level
            assert level['lower'] <= level['upper']


class TestFeatureEngineeringTool:
    """Test cases for FeatureEngineeringTool"""
    
    @pytest.fixture
    def feature_tool(self):
        """Create FeatureEngineeringTool instance"""
        from agents.tools.feature_engineering_tool import FeatureEngineeringTool
        return FeatureEngineeringTool()
    
    @pytest.mark.asyncio
    async def test_technical_features(self, feature_tool, sample_market_data):
        """Test technical indicator feature engineering"""
        symbol = "AAPL"
        
        with patch('yfinance.download') as mock_download:
            mock_download.return_value = sample_market_data
            
            result = await feature_tool.run(symbol=symbol, feature_type='technical')
            
            assert 'rsi' in result
            assert 'macd' in result
            assert 'bollinger_position' in result
            assert 'moving_averages' in result
            
            # Verify indicator ranges
            assert 0 <= result['rsi'] <= 100
            assert isinstance(result['macd'], (int, float))
    
    @pytest.mark.asyncio
    async def test_statistical_features(self, feature_tool):
        """Test statistical feature engineering"""
        price_series = np.random.random(100)
        
        result = await feature_tool.run(price_series=price_series, feature_type='statistical')
        
        assert 'mean' in result
        assert 'std' in result
        assert 'skewness' in result
        assert 'kurtosis' in result
        assert 'autocorrelation' in result
    
    @pytest.mark.asyncio
    async def test_lagged_features(self, feature_tool):
        """Test lagged feature engineering"""
        data = {
            'price': np.random.random(100),
            'volume': np.random.random(100)
        }
        lags = [1, 2, 3, 5, 10]
        
        result = await feature_tool.run(data=data, lags=lags, feature_type='lagged')
        
        for col in data.keys():
            for lag in lags:
                assert f'{col}_lag_{lag}' in result
    
    @pytest.mark.asyncio
    async def test_sentiment_features(self, feature_tool):
        """Test sentiment-based feature engineering"""
        news_data = [
            {'sentiment': 'positive', 'relevance': 0.8, 'timestamp': datetime.now()},
            {'sentiment': 'negative', 'relevance': 0.6, 'timestamp': datetime.now()}
        ]
        
        result = await feature_tool.run(news_data=news_data, feature_type='sentiment')
        
        assert 'sentiment_score' in result
        assert 'sentiment_volatility' in result
        assert 'news_volume' in result
        assert -1 <= result['sentiment_score'] <= 1


class TestModelTrainingTool:
    """Test cases for ModelTrainingTool"""
    
    @pytest.fixture
    def training_tool(self):
        """Create ModelTrainingTool instance"""
        from agents.tools.model_training_tool import ModelTrainingTool
        return ModelTrainingTool()
    
    @pytest.mark.asyncio
    async def test_random_forest_training(self, training_tool):
        """Test Random Forest model training"""
        X = np.random.random((100, 20))
        y = np.random.random(100)
        
        with patch('sklearn.ensemble.RandomForestRegressor') as mock_rf:
            mock_model = Mock()
            mock_model.fit = Mock()
            mock_model.predict = Mock(return_value=np.random.random(20))
            mock_model.score = Mock(return_value=0.85)
            mock_model.feature_importances_ = np.random.random(20)
            
            mock_rf.return_value = mock_model
            
            result = await training_tool.run(X=X, y=y, model_type='random_forest')
            
            assert 'model' in result
            assert 'training_score' in result
            assert 'feature_importance' in result
            assert result['training_score'] >= 0
    
    @pytest.mark.asyncio
    async def test_gradient_boosting_training(self, training_tool):
        """Test Gradient Boosting model training"""
        X = np.random.random((100, 20))
        y = np.random.random(100)
        
        with patch('sklearn.ensemble.GradientBoostingRegressor') as mock_gb:
            mock_model = Mock()
            mock_model.fit = Mock()
            mock_model.predict = Mock(return_value=np.random.random(20))
            mock_model.score = Mock(return_value=0.82)
            mock_model.feature_importances_ = np.random.random(20)
            
            mock_gb.return_value = mock_model
            
            result = await training_tool.run(X=X, y=y, model_type='gradient_boosting')
            
            assert 'model' in result
            assert 'training_score' in result
            assert 'feature_importance' in result
    
    @pytest.mark.asyncio
    async def test_neural_network_training(self, training_tool):
        """Test Neural Network model training"""
        X = np.random.random((100, 20))
        y = np.random.random(100)
        
        with patch('sklearn.neural_network.MLPRegressor') as mock_nn:
            mock_model = Mock()
            mock_model.fit = Mock()
            mock_model.predict = Mock(return_value=np.random.random(20))
            mock_model.score = Mock(return_value=0.78)
            
            mock_nn.return_value = mock_model
            
            result = await training_tool.run(X=X, y=y, model_type='neural_network')
            
            assert 'model' in result
            assert 'training_score' in result
            assert 'convergence' in result


class TestPredictionTool:
    """Test cases for PredictionTool"""
    
    @pytest.fixture
    def prediction_tool(self):
        """Create PredictionTool instance"""
        from agents.tools.prediction_tool import PredictionTool
        return PredictionTool()
    
    @pytest.mark.asyncio
    async def test_single_prediction(self, prediction_tool):
        """Test single data point prediction"""
        model = Mock()
        model.predict = Mock(return_value=np.array([105.5]))
        
        data = np.random.random((1, 20))
        
        result = await prediction_tool.run(model=model, data=data)
        
        assert 'prediction' in result
        assert 'confidence' in result
        assert isinstance(result['prediction'], (int, float))
    
    @pytest.mark.asyncio
    async def test_batch_prediction(self, prediction_tool):
        """Test batch prediction"""
        model = Mock()
        model.predict = Mock(return_value=np.random.random(10))
        
        data = np.random.random((10, 20))
        
        result = await prediction_tool.run(model=model, data=data, batch_size=5)
        
        assert 'predictions' in result
        assert len(result['predictions']) == 10
        assert 'batch_info' in result
    
    @pytest.mark.asyncio
    async def test_probabilistic_prediction(self, prediction_tool):
        """Test probabilistic prediction"""
        model = Mock()
        model.predict_proba = Mock(return_value=np.random.random((10, 3)))  # 3 classes
        
        data = np.random.random((10, 20))
        
        result = await prediction_tool.run(model=model, data=data, prediction_type='probabilistic')
        
        assert 'probabilities' in result
        assert 'class_predictions' in result
        assert 'confidence_scores' in result


class TestBacktestingTool:
    """Test cases for BacktestingTool"""
    
    @pytest.fixture
    def backtesting_tool(self):
        """Create BacktestingTool instance"""
        from agents.tools.backtesting_tool import BacktestingTool
        return BacktestingTool()
    
    @pytest.mark.asyncio
    async def test_strategy_backtest(self, backtesting_tool):
        """Test strategy backtesting"""
        strategy = Mock()
        strategy.generate_signals = Mock(return_value=np.random.choice(['buy', 'sell', 'hold'], 252))
        strategy.position_size = Mock(return_value=1000)
        
        price_data = np.random.random(252) * 100 + 100  # Price series
        
        result = await backtesting_tool.run(strategy=strategy, price_data=price_data)
        
        assert 'total_return' in result
        assert 'sharpe_ratio' in result
        assert 'max_drawdown' in result
        assert 'trades' in result
        assert 'equity_curve' in result
        
        # Verify equity curve
        assert len(result['equity_curve']) == 252
        assert all(isinstance(x, (int, float)) for x in result['equity_curve'])
    
    @pytest.mark.asyncio
    async def test_walk_forward_test(self, backtesting_tool):
        """Test walk-forward testing"""
        strategy = Mock()
        strategy.fit = Mock()
        strategy.predict = Mock(return_value=np.random.random(50))
        
        data = np.random.random((300, 20))  # Historical data
        lookback = 200  # Training period
        forward = 50    # Testing period
        
        result = await backtesting_tool.run(
            strategy=strategy, 
            data=data, 
            method='walk_forward',
            lookback=lookback,
            forward=forward
        )
        
        assert 'out_of_sample_performance' in result
        assert 'rolling_performance' in result
        assert 'stability_metrics' in result


class TestIntegration:
    """Integration tests for ML Prediction Engineer"""
    
    @pytest.mark.asyncio
    async def test_full_ml_workflow(self):
        """Test complete ML workflow"""
        from agents.ml_prediction_engineer import MLPredictionEngineer
        
        ml_engineer = MLPredictionEngineer()
        
        # Mock all tools
        with patch.multiple(
            'agents.ml_prediction_engineer.FeatureEngineeringTool',
            run=AsyncMock(return_value={
                'features': np.random.random((100, 20)),
                'feature_names': [f'feature_{i}' for i in range(20)]
            })
        ), patch.multiple(
            'agents.ml_prediction_engineer.ModelTrainingTool',
            run=AsyncMock(return_value={
                'model': Mock(),
                'training_metrics': {'accuracy': 0.85},
                'feature_importance': np.random.random(20)
            })
        ), patch.multiple(
            'agents.ml_prediction_engineer.PredictionTool',
            run=AsyncMock(return_value={
                'predictions': np.random.random(10),
                'confidence': 0.8
            })
        ), patch.multiple(
            'agents.ml_prediction_engineer.BacktestingTool',
            run=AsyncMock(return_value={
                'performance_metrics': {'sharpe_ratio': 1.5},
                'equity_curve': np.random.random(252)
            })
        ):
            
            symbol = "AAPL"
            
            # Step 1: Feature Engineering
            feature_request = {
                'symbol': symbol,
                'feature_types': ['technical', 'fundamental'],
                'lookback_period': 60
            }
            features = await ml_engineer.engineer_features(feature_request)
            assert features['features'].shape[1] == 20
            
            # Step 2: Model Training
            training_request = {
                'model_type': 'random_forest',
                'feature_matrix': features['features'],
                'target_vector': np.random.random(100),
                'hyperparameters': {'n_estimators': 100}
            }
            model_result = await ml_engineer.train_model(training_request)
            assert 'model' in model_result
            assert model_result['training_metrics']['accuracy'] >= 0
            
            # Step 3: Prediction
            prediction_request = {
                'model': model_result['model'],
                'symbol': symbol,
                'prediction_horizon': 10
            }
            predictions = await ml_engineer.predict_price_movement(prediction_request)
            assert len(predictions['predictions']) == 10
            
            # Step 4: Backtesting
            backtest_request = {
                'strategy': model_result['model'],
                'symbol': symbol,
                'start_date': '2023-01-01',
                'end_date': '2024-01-01'
            }
            backtest_result = await ml_engineer.backtest_strategy(backtest_request)
            assert 'performance_metrics' in backtest_result
            assert backtest_result['performance_metrics']['sharpe_ratio'] >= 0