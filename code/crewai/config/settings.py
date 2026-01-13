"""
Configuration settings for CrewAI Trading Agent System
"""
from typing import Dict, List, Optional, Any
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingSettings(BaseSettings):
    """Trading configuration settings"""
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4"
    
    # Data Sources
    alpha_vantage_api_key: str = ""
    yahoo_finance_enabled: bool = True
    
    # Risk Management
    max_position_size: float = 10000
    risk_tolerance: float = 0.02
    max_drawdown: float = 0.05
    
    # Agent Configuration
    max_retries: int = 3
    cache_ttl: int = 300
    memory_retention: int = 86400
    
    # Approval Workflow
    high_risk_threshold: float = 0.05
    approval_required_amount: float = 50000
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


class RedisKeys:
    """Redis key namespace for memory storage"""
    
    MEMORY_PREFIX = "crewai:memory:"
    CACHE_PREFIX = "crewai:cache:"
    CONTEXT_PREFIX = "crewai:context:"
    APPROVAL_PREFIX = "crewai:approval:"
    
    # Crew memory keys
    CREW_MEMORY = "{memory_prefix}crew:{crew_id}"
    AGENT_MEMORY = "{memory_prefix}agent:{agent_id}:crew:{crew_id}"
    MARKET_DATA = "{cache_prefix}market:{symbol}:{timeframe}"
    APPROVAL_QUEUE = "{approval_prefix}queue:{crew_id}"
    
    @classmethod
    def format_key(cls, template: str, **kwargs) -> str:
        """Format Redis key template with provided parameters"""
        # Replace prefixes
        template = template.replace("{memory_prefix}", cls.MEMORY_PREFIX)
        template = template.replace("{cache_prefix}", cls.CACHE_PREFIX)
        template = template.replace("{context_prefix}", cls.CONTEXT_PREFIX)
        template = template.replace("{approval_prefix}", cls.APPROVAL_PREFIX)
        
        # Format with provided kwargs
        return template.format(**kwargs)
    
    @staticmethod
    def memory_key(agent_id: str) -> str:
        return f"{RedisKeys.MEMORY_PREFIX}{agent_id}"
    
    @staticmethod
    def cache_key(function_name: str, params: str) -> str:
        return f"{RedisKeys.CACHE_PREFIX}{function_name}:{params}"
    
    @staticmethod
    def context_key(crew_id: str) -> str:
        return f"{RedisKeys.CONTEXT_PREFIX}{crew_id}"
    
    @staticmethod
    def approval_key(request_id: str) -> str:
        return f"{RedisKeys.APPROVAL_PREFIX}{request_id}"


class AgentPrompts:
    """Prompts for specialized trading agents"""
    
    MARKET_RESEARCH_ANALYST = """
    You are a market research analyst specializing in financial markets.
    Your role is to conduct comprehensive market analysis and identify trading opportunities.
    Focus on fundamental analysis, technical indicators, market sentiment, and sector trends.
    Always provide data-driven insights and actionable recommendations.
    """
    
    ML_PREDICTION_ENGINEER = """
    You are a machine learning engineer specializing in quantitative finance.
    Your expertise includes feature engineering, time series modeling, and financial prediction.
    Build robust models that provide reliable predictions for trading decisions.
    Always explain model limitations and confidence levels.
    """
    
    CHIEF_RISK_OFFICER = """
    You are a Chief Risk Officer with expertise in quantitative risk management.
    Your responsibility is to protect the organization from financial losses while enabling profitable trading.
    Assess portfolio risk, ensure compliance, and provide risk management recommendations.
    Always prioritize risk management over potential profits.
    """
    
    EXECUTION_TRADER = """
    You are an execution trader with expertise in algorithmic trading and market microstructure.
    Your role is to execute trades with optimal timing and minimal market impact.
    Understand market conditions, timing, and execution strategies to maximize efficiency.
    Always consider liquidity, volatility, and market impact in execution decisions.
    """


class AgentConfig:
    """Configuration for specialized trading agents"""
    
    MARKET_RESEARCH = {
        "name": "Market Research Analyst",
        "description": "Analyzes market trends, sentiment, and technical indicators",
        "tools": ["market_data", "news_sentiment", "technical_analysis"]
    }
    
    ML_PREDICTION = {
        "name": "ML Prediction Engineer", 
        "description": "Develops and deploys machine learning models for price prediction",
        "tools": ["train_model", "predict", "backtest", "feature_importance"]
    }
    
    RISK_OFFICER = {
        "name": "Chief Risk Officer",
        "description": "Assesses portfolio risk and ensures compliance with risk limits",
        "tools": ["calculate_var", "position_sizing", "portfolio_optimization", "stress_test"]
    }
    
    EXECUTION_TRADER = {
        "name": "Execution Trader",
        "description": "Executes trades and monitors execution quality",
        "tools": ["execute_trade", "monitor_execution", "cancel_order", "reconcile_trades"]
    }


class CrewConfig:
    """Configuration for crew orchestration"""
    
    DEFAULT_CREW_SIZE = 4
    TASK_TIMEOUT = 300  # 5 minutes
    MAX_PARALLEL_TASKS = 2
    MEMORY_UPDATE_INTERVAL = 60  # 1 minute
    
    APPROVAL_TIMEOUTS = {
        "low": 300,      # 5 minutes
        "medium": 1800,  # 30 minutes
        "high": 3600     # 1 hour
    }


# Global settings instance
settings = TradingSettings()