"""
Feature Engineering Pipeline for Market Data (RSI, MACD, Volume, Sentiment)
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import yfinance as yf
import talib
from textblob import TextBlob
import requests
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """Calculate technical indicators for market data"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index (RSI)"""
        return talib.RSI(prices.values, timeperiod=period)
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        macd, macd_signal, macd_hist = talib.MACD(prices.values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
        
        return {
            'macd': pd.Series(macd, index=prices.index),
            'macd_signal': pd.Series(macd_signal, index=prices.index),
            'macd_histogram': pd.Series(macd_hist, index=prices.index)
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        upper, middle, lower = talib.BBANDS(prices.values, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        
        return {
            'bb_upper': pd.Series(upper, index=prices.index),
            'bb_middle': pd.Series(middle, index=prices.index),
            'bb_lower': pd.Series(lower, index=prices.index),
            'bb_width': pd.Series((upper - lower) / middle, index=prices.index),
            'bb_position': pd.Series((prices.values - lower) / (upper - lower), index=prices.index)
        }
    
    @staticmethod
    def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return talib.SMA(prices.values, timeperiod=period)
    
    @staticmethod
    def calculate_ema(prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return talib.EMA(prices.values, timeperiod=period)
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        slowk, slowd = talib.STOCH(high.values, low.values, close.values,
                                 fastk_period=k_period, slowk_period=d_period,
                                 slowd_period=d_period)
        
        return {
            'stoch_k': pd.Series(slowk, index=close.index),
            'stoch_d': pd.Series(slowd, index=close.index)
        }
    
    @staticmethod
    def calculate_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Williams %R"""
        return talib.WILLR(high.values, low.values, close.values, timeperiod=period)
    
    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        return talib.ATR(high.values, low.values, close.values, timeperiod=period)
    
    @staticmethod
    def calculate_volume_indicators(volume: pd.Series, close: pd.Series) -> Dict[str, pd.Series]:
        """Calculate volume-based indicators"""
        # Volume SMA
        volume_sma_20 = talib.SMA(volume.values, timeperiod=20)
        volume_ratio = volume / pd.Series(volume_sma_20, index=volume.index)
        
        # On-Balance Volume (OBV)
        obv = talib.OBV(close.values, volume.values)
        
        # Volume Price Trend (VPT)
        price_change = close.pct_change()
        vpt = (volume * price_change).cumsum()
        
        return {
            'volume_sma_20': pd.Series(volume_sma_20, index=volume.index),
            'volume_ratio': volume_ratio,
            'obv': pd.Series(obv, index=volume.index),
            'vpt': vpt
        }


class SentimentAnalyzer:
    """Analyze market sentiment from news and social media"""
    
    def __init__(self, news_api_key: str = None):
        """
        Initialize sentiment analyzer
        
        Args:
            news_api_key: API key for news data
        """
        self.news_api_key = news_api_key or os.getenv('NEWS_API_KEY')
        
    def get_news_sentiment(self, symbol: str, days: int = 7) -> Dict[str, float]:
        """
        Get sentiment from financial news
        
        Args:
            symbol: Stock symbol
            days: Number of days to look back
            
        Returns:
            Sentiment metrics
        """
        try:
            # Fetch news (placeholder - implement with actual news API)
            news_data = self._fetch_news(symbol, days)
            
            # Analyze sentiment for each article
            sentiments = []
            for article in news_data:
                blob = TextBlob(article.get('title', '') + ' ' + article.get('description', ''))
                sentiments.append(blob.sentiment.polarity)
            
            if sentiments:
                return {
                    'news_sentiment_mean': np.mean(sentiments),
                    'news_sentiment_std': np.std(sentiments),
                    'news_sentiment_min': np.min(sentiments),
                    'news_sentiment_max': np.max(sentiments),
                    'news_articles_count': len(sentiments)
                }
            else:
                return self._default_sentiment()
                
        except Exception as e:
            logger.warning(f"Failed to get news sentiment for {symbol}: {str(e)}")
            return self._default_sentiment()
    
    def _fetch_news(self, symbol: str, days: int) -> List[Dict]:
        """Fetch news articles for symbol"""
        # This is a placeholder - implement with actual news API
        # Examples: NewsAPI, Alpha Vantage News, Finnhub News
        
        if not self.news_api_key:
            logger.warning("No news API key configured")
            return []
        
        # Example implementation with NewsAPI
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': f"{symbol} stock",
            'from': start_date.strftime('%Y-%m-%d'),
            'to': end_date.strftime('%Y-%m-%d'),
            'apiKey': self.news_api_key,
            'sortBy': 'publishedAt',
            'language': 'en',
            'pageSize': 50
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return [{'title': article['title'], 'description': article.get('description', '')}
                   for article in data.get('articles', [])]
        else:
            logger.warning(f"Failed to fetch news: {response.status_code}")
            return []
    
    def _default_sentiment(self) -> Dict[str, float]:
        """Return default neutral sentiment"""
        return {
            'news_sentiment_mean': 0.0,
            'news_sentiment_std': 0.0,
            'news_sentiment_min': 0.0,
            'news_sentiment_max': 0.0,
            'news_articles_count': 0
        }


class FeatureEngineeringPipeline:
    """Complete feature engineering pipeline for market data"""
    
    def __init__(self, sentiment_analyzer: SentimentAnalyzer = None):
        """
        Initialize feature engineering pipeline
        
        Args:
            sentiment_analyzer: Sentiment analyzer instance
        """
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
        self.technical_indicators = TechnicalIndicators()
        
    def create_features(self, data: pd.DataFrame, symbols: List[str] = None, 
                       include_sentiment: bool = True, 
                       sentiment_lookback: int = 7) -> pd.DataFrame:
        """
        Create comprehensive feature set for market prediction
        
        Args:
            data: Market data with OHLCV columns
            symbols: List of symbols to process
            include_sentiment: Whether to include sentiment features
            sentiment_lookback: Days to look back for sentiment analysis
            
        Returns:
            DataFrame with engineered features
        """
        logger.info("Starting feature engineering pipeline")
        
        if symbols is None:
            symbols = data['symbol'].unique().tolist() if 'symbol' in data.columns else ['default']
        
        feature_data = []
        
        for symbol in symbols:
            logger.info(f"Processing features for {symbol}")
            
            # Filter data for symbol
            symbol_data = data[data['symbol'] == symbol].copy() if 'symbol' in data.columns else data.copy()
            
            if symbol_data.empty:
                continue
            
            # Sort by date
            symbol_data = symbol_data.sort_values('date' if 'date' in symbol_data.columns else 
                                                symbol_data.columns[0])
            
            # Create features
            features = self._create_technical_features(symbol_data)
            
            # Add sentiment features if requested
            if include_sentiment:
                sentiment_features = self.sentiment_analyzer.get_news_sentiment(symbol, sentiment_lookback)
                for key, value in sentiment_features.items():
                    features[key] = value
            
            # Add derived features
            features.update(self._create_derived_features(symbol_data, features))
            
            # Add lag features
            features.update(self._create_lag_features(symbol_data))
            
            # Add rolling statistics
            features.update(self._create_rolling_features(symbol_data))
            
            feature_data.append(features)
        
        if not feature_data:
            raise ValueError("No data processed for any symbols")
        
        # Combine all features
        final_features = self._combine_features(feature_data)
        
        logger.info(f"Created {final_features.shape[1]} features for {final_features.shape[0]} samples")
        return final_features
    
    def _create_technical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create technical indicator features"""
        features = data.copy()
        
        # Ensure required columns exist
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            logger.warning(f"Missing required columns: {missing_cols}")
            return features
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # Price-based features
        features['price_change'] = close.pct_change()
        features['price_change_lag_1'] = features['price_change'].shift(1)
        features['price_change_lag_2'] = features['price_change'].shift(2)
        
        # RSI
        features['rsi'] = self.technical_indicators.calculate_rsi(close)
        features['rsi_sma'] = self.technical_indicators.calculate_sma(features['rsi'], 5)
        
        # MACD
        macd_data = self.technical_indicators.calculate_macd(close)
        features.update({f'macd_{k}': v for k, v in macd_data.items()})
        
        # Bollinger Bands
        bb_data = self.technical_indicators.calculate_bollinger_bands(close)
        features.update({f'bb_{k}': v for k, v in bb_data.items()})
        
        # Moving Averages
        for period in [5, 10, 20, 50]:
            features[f'sma_{period}'] = self.technical_indicators.calculate_sma(close, period)
            features[f'ema_{period}'] = self.technical_indicators.calculate_ema(close, period)
            features[f'price_sma_{period}_ratio'] = close / features[f'sma_{period}']
            features[f'price_ema_{period}_ratio'] = close / features[f'ema_{period}']
        
        # Stochastic
        stoch_data = self.technical_indicators.calculate_stochastic(high, low, close)
        features.update({f'stoch_{k}': v for k, v in stoch_data.items()})
        
        # Williams %R
        features['williams_r'] = self.technical_indicators.calculate_williams_r(high, low, close)
        
        # ATR
        features['atr'] = self.technical_indicators.calculate_atr(high, low, close)
        features['atr_ratio'] = features['atr'] / close
        
        # Volume indicators
        vol_data = self.technical_indicators.calculate_volume_indicators(volume, close)
        features.update({f'volume_{k}': v for k, v in vol_data.items()})
        
        return features
    
    def _create_derived_features(self, data: pd.DataFrame, features: pd.DataFrame) -> Dict[str, pd.Series]:
        """Create derived features"""
        derived = {}
        
        # Price-based ratios
        if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
            derived['high_low_ratio'] = data['high'] / data['low']
            derived['close_open_ratio'] = data['close'] / data['open']
            derived['price_range'] = (data['high'] - data['low']) / data['close']
        
        # Volatility measures
        if 'price_change' in features.columns:
            derived['volatility_5'] = features['price_change'].rolling(5).std()
            derived['volatility_20'] = features['price_change'].rolling(20).std()
        
        # Trend indicators
        if 'sma_20' in features.columns:
            derived['trend_indicator'] = (data['close'] - features['sma_20']) / features['sma_20']
        
        # Momentum indicators
        for period in [5, 10]:
            if f'price_sma_{period}_ratio' in features.columns:
                derived[f'momentum_{period}'] = features[f'price_sma_{period}_ratio'].pct_change()
        
        return derived
    
    def _create_lag_features(self, data: pd.DataFrame, lags: List[int] = [1, 2, 3, 5]) -> Dict[str, pd.Series]:
        """Create lag features for key variables"""
        lag_features = {}
        
        # Price lags
        for col in ['close', 'volume']:
            if col in data.columns:
                for lag in lags:
                    lag_features[f'{col}_lag_{lag}'] = data[col].shift(lag)
        
        return lag_features
    
    def _create_rolling_features(self, data: pd.DataFrame, windows: List[int] = [5, 10, 20]) -> Dict[str, pd.Series]:
        """Create rolling window features"""
        rolling_features = {}
        
        for window in windows:
            # Rolling correlations
            if all(col in data.columns for col in ['close', 'volume']):
                rolling_features[f'close_volume_corr_{window}'] = (
                    data['close'].rolling(window).corr(data['volume'])
                )
            
            # Rolling statistics
            if 'close' in data.columns:
                rolling_features[f'close_mean_{window}'] = data['close'].rolling(window).mean()
                rolling_features[f'close_std_{window}'] = data['close'].rolling(window).std()
                rolling_features[f'close_skew_{window}'] = data['close'].rolling(window).skew()
                rolling_features[f'close_kurt_{window}'] = data['close'].rolling(window).kurt()
        
        return rolling_features
    
    def _combine_features(self, feature_data: List[pd.DataFrame]) -> pd.DataFrame:
        """Combine features from multiple symbols"""
        if len(feature_data) == 1:
            return feature_data[0]
        
        # Stack features vertically
        combined = pd.concat(feature_data, ignore_index=True)
        return combined
    
    def add_target_variable(self, data: pd.DataFrame, target_column: str = 'close',
                          periods_ahead: int = 1, return_column: str = 'future_return') -> pd.DataFrame:
        """
        Add target variable for prediction
        
        Args:
            data: Feature data
            target_column: Column to predict
            periods_ahead: Number of periods ahead to predict
            return_column: Name for the return column
            
        Returns:
            Data with target variable
        """
        logger.info(f"Adding target variable: {return_column} ({periods_ahead} periods ahead)")
        
        data = data.copy()
        
        if target_column in data.columns:
            # Calculate future return
            future_value = data[target_column].shift(-periods_ahead)
            data[return_column] = (future_value - data[target_column]) / data[target_column]
        else:
            logger.warning(f"Target column '{target_column}' not found in data")
        
        return data
    
    def scale_features(self, data: pd.DataFrame, exclude_columns: List[str] = None) -> Tuple[pd.DataFrame, StandardScaler]:
        """
        Scale features using StandardScaler
        
        Args:
            data: Feature data
            exclude_columns: Columns to exclude from scaling
            
        Returns:
            Scaled data and scaler
        """
        if exclude_columns is None:
            exclude_columns = ['date', 'symbol', 'future_return']
        
        # Identify numeric columns to scale
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        columns_to_scale = [col for col in numeric_columns if col not in exclude_columns]
        
        if not columns_to_scale:
            logger.warning("No columns to scale")
            return data, None
        
        # Create scaler
        scaler = StandardScaler()
        
        # Scale features
        scaled_data = data.copy()
        scaled_data[columns_to_scale] = scaler.fit_transform(data[columns_to_scale])
        
        logger.info(f"Scaled {len(columns_to_scale)} features")
        return scaled_data, scaler
    
    def create_prediction_dataset(self, symbols: List[str], start_date: str, end_date: str,
                                periods_ahead: int = 1, include_sentiment: bool = True) -> pd.DataFrame:
        """
        Create complete prediction dataset
        
        Args:
            symbols: List of symbols
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            periods_ahead: Periods ahead for prediction
            include_sentiment: Whether to include sentiment features
            
        Returns:
            Complete feature dataset with target
        """
        logger.info(f"Creating prediction dataset for symbols: {symbols}")
        
        all_data = []
        
        for symbol in symbols:
            try:
                # Fetch data
                ticker_data = yf.download(symbol, start=start_date, end=end_date)
                
                if ticker_data.empty:
                    logger.warning(f"No data found for {symbol}")
                    continue
                
                # Reset index to make date a column
                ticker_data = ticker_data.reset_index()
                ticker_data['symbol'] = symbol
                
                all_data.append(ticker_data)
                
            except Exception as e:
                logger.error(f"Failed to fetch data for {symbol}: {str(e)}")
        
        if not all_data:
            raise ValueError("No data fetched for any symbols")
        
        # Combine all data
        combined_data = pd.concat(all_data, ignore_index=True)
        
        # Create features
        features = self.create_features(combined_data, include_sentiment=include_sentiment)
        
        # Add target variable
        features = self.add_target_variable(features, periods_ahead=periods_ahead)
        
        # Remove rows with NaN target values
        features = features.dropna(subset=['future_return'])
        
        # Scale features
        features, scaler = self.scale_features(features)
        
        logger.info(f"Created dataset with {features.shape[0]} samples and {features.shape[1]} features")
        
        return features, scaler


class FeatureSelector:
    """Select most relevant features for modeling"""
    
    @staticmethod
    def select_by_correlation(data: pd.DataFrame, target_col: str, 
                            threshold: float = 0.1) -> List[str]:
        """Select features by correlation with target"""
        numeric_data = data.select_dtypes(include=[np.number])
        
        correlations = numeric_data.corr()[target_col].abs().sort_values(ascending=False)
        
        # Remove target column from correlations
        correlations = correlations.drop(target_col, errors='ignore')
        
        # Select features above threshold
        selected_features = correlations[correlations >= threshold].index.tolist()
        
        logger.info(f"Selected {len(selected_features)} features by correlation > {threshold}")
        return selected_features
    
    @staticmethod
    def select_by_importance(importance_scores: Dict[str, float], 
                           top_n: int = None, threshold: float = 0.01) -> List[str]:
        """Select features by importance scores"""
        if top_n:
            sorted_features = sorted(importance_scores.items(), key=lambda x: x[1], reverse=True)
            return [feature for feature, score in sorted_features[:top_n]]
        else:
            return [feature for feature, score in importance_scores.items() if score >= threshold]