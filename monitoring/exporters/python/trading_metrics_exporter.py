#!/usr/bin/env python3
"""
Trading System Custom Metrics Exporter
Collects and exposes custom trading metrics for Prometheus monitoring
"""

import os
import sys
import time
import json
import logging
import asyncio
import aiohttp
import psutil
import redis
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from prometheus_client import start_http_server, Gauge, Counter, Histogram, generate_latest, CollectorRegistry
from prometheus_client.core import REGISTRY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/trading-metrics.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TradingMetricsCollector:
    """Collector for trading system metrics"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_client = None
        self.db_connection = None
        self.session = None
        
        # Initialize Prometheus metrics
        self._init_metrics()
        
        # Initialize connections
        self._init_connections()
    
    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        
        # Trading Performance Metrics
        self.trading_decisions = Counter(
            'trading_decisions_total',
            'Total number of trading decisions',
            ['algorithm', 'symbol', 'side', 'outcome']
        )
        
        self.trading_profit_loss = Counter(
            'trading_profit_loss_total',
            'Total profit and loss in USD',
            ['algorithm', 'symbol', 'side']
        )
        
        self.trading_volume = Counter(
            'trading_volume_total',
            'Trading volume in USD',
            ['symbol', 'side']
        )
        
        self.trading_latency = Histogram(
            'trading_latency_seconds',
            'Trading operation latency',
            ['operation', 'algorithm']
        )
        
        # Market Data Metrics
        self.market_data_latency = Histogram(
            'market_data_latency_seconds',
            'Market data retrieval latency',
            ['exchange', 'symbol', 'data_type']
        )
        
        self.market_data_points = Counter(
            'market_data_points_total',
            'Total market data points received',
            ['exchange', 'symbol', 'data_type']
        )
        
        self.market_data_freshness = Gauge(
            'market_data_freshness_seconds',
            'Time since last data point',
            ['exchange', 'symbol']
        )
        
        # Risk Metrics
        self.portfolio_risk_score = Gauge(
            'portfolio_risk_score',
            'Current portfolio risk score'
        )
        
        self.var_95 = Gauge(
            'value_at_risk_95',
            'Value at Risk 95% confidence level'
        )
        
        self.max_drawdown = Gauge(
            'portfolio_max_drawdown',
            'Maximum portfolio drawdown'
        )
        
        self.position_risk = Gauge(
            'position_risk_score',
            'Individual position risk score',
            ['symbol']
        )
        
        self.capital_allocation = Gauge(
            'capital_allocation_ratio',
            'Capital allocation ratio',
            ['symbol']
        )
        
        # System Performance Metrics
        self.api_response_time = Histogram(
            'api_response_time_seconds',
            'API response time',
            ['endpoint', 'method']
        )
        
        self.api_request_rate = Counter(
            'api_requests_total',
            'Total API requests',
            ['endpoint', 'method', 'status_code']
        )
        
        self.error_rate = Counter(
            'errors_total',
            'Total errors by type',
            ['service', 'error_type']
        )
        
        # Business Metrics
        self.order_processing_time = Histogram(
            'order_processing_duration_seconds',
            'Order processing duration',
            ['order_type', 'status']
        )
        
        self.settlement_success_rate = Gauge(
            'settlement_success_rate',
            'Settlement success rate',
            ['venue']
        )
        
        self.circuit_breaker_status = Gauge(
            'circuit_breaker_status',
            'Circuit breaker status (0=closed, 1=half-open, 2=open)',
            ['algorithm', 'symbol']
        )
        
        # Compliance and Security Metrics
        self.auth_failures = Counter(
            'authentication_failures_total',
            'Total authentication failures',
            ['method', 'ip_address']
        )
        
        self.unauthorized_access = Counter(
            'unauthorized_access_attempts_total',
            'Total unauthorized access attempts',
            ['resource', 'ip_address']
        )
        
        self.security_threats = Counter(
            'security_threats_total',
            'Total security threats detected',
            ['threat_type', 'severity']
        )
        
        # Infrastructure Metrics
        self.database_connections = Gauge(
            'database_connections_active',
            'Active database connections',
            ['database']
        )
        
        self.message_queue_depth = Gauge(
            'message_queue_depth',
            'Message queue depth',
            ['queue_name']
        )
        
        self.cache_hit_rate = Gauge(
            'cache_hit_rate',
            'Cache hit rate',
            ['cache_type']
        )
    
    def _init_connections(self):
        """Initialize database and Redis connections"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.get('redis_host', 'localhost'),
                port=self.config.get('redis_port', 6379),
                password=self.config.get('redis_password', ''),
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
        
        try:
            self.db_connection = psycopg2.connect(
                host=self.config.get('db_host', 'localhost'),
                port=self.config.get('db_port', 5432),
                database=self.config.get('db_name', 'trading'),
                user=self.config.get('db_user', 'postgres'),
                password=self.config.get('db_password', 'changeme'),
                connect_timeout=5
            )
            logger.info("Connected to database successfully")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
    
    async def collect_trading_metrics(self):
        """Collect trading performance metrics"""
        try:
            # Get trading decisions from database or Redis
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    SELECT algorithm, symbol, side, outcome, 
                           COUNT(*) as count,
                           SUM(profit_loss) as total_pl
                    FROM trading_decisions 
                    WHERE timestamp > NOW() - INTERVAL '1 hour'
                    GROUP BY algorithm, symbol, side, outcome
                """)
                
                for row in cursor.fetchall():
                    algorithm, symbol, side, outcome, count, total_pl = row
                    self.trading_decisions.labels(
                        algorithm=algorithm,
                        symbol=symbol,
                        side=side,
                        outcome=outcome
                    )._value._value += count
                    
                    if total_pl:
                        self.trading_profit_loss.labels(
                            algorithm=algorithm,
                            symbol=symbol,
                            side=side
                        )._value._value += total_pl
            
            # Simulate real-time metrics (replace with actual collection)
            await self._simulate_trading_metrics()
            
        except Exception as e:
            logger.error(f"Error collecting trading metrics: {e}")
    
    async def _simulate_trading_metrics(self):
        """Simulate trading metrics for demonstration"""
        import random
        
        algorithms = ['momentum', 'mean_reversion', 'arbitrage', 'ml_algorithm']
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'BTC-USD']
        sides = ['buy', 'sell']
        outcomes = ['win', 'loss', 'neutral']
        
        # Generate random trading decisions
        for _ in range(random.randint(1, 5)):
            algorithm = random.choice(algorithms)
            symbol = random.choice(symbols)
            side = random.choice(sides)
            outcome = random.choice(outcomes)
            profit_loss = random.uniform(-1000, 1000)
            
            self.trading_decisions.labels(
                algorithm=algorithm,
                symbol=symbol,
                side=side,
                outcome=outcome
            ).inc()
            
            self.trading_volume.labels(
                symbol=symbol,
                side=side
            ).inc(random.uniform(1000, 50000))
            
            if outcome == 'win':
                self.trading_profit_loss.labels(
                    algorithm=algorithm,
                    symbol=symbol,
                    side=side
                ).inc(profit_loss)
            else:
                self.trading_profit_loss.labels(
                    algorithm=algorithm,
                    symbol=symbol,
                    side=side
                ).dec(abs(profit_loss))
    
    async def collect_market_data_metrics(self):
        """Collect market data metrics"""
        try:
            # Simulate market data metrics
            exchanges = ['NASDAQ', 'NYSE', 'BINANCE', 'COINBASE']
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'BTC-USD']
            data_types = ['price', 'volume', 'orderbook', 'trade']
            
            for exchange in exchanges:
                for symbol in symbols:
                    # Update data freshness
                    self.market_data_freshness.labels(
                        exchange=exchange,
                        symbol=symbol
                    ).set(time.time() % 300)  # Random freshness up to 5 minutes
                    
                    # Simulate data points
                    for data_type in data_types:
                        self.market_data_points.labels(
                            exchange=exchange,
                            symbol=symbol,
                            data_type=data_type
                        ).inc(random.randint(1, 10))
                        
                        # Simulate latency
                        latency = random.uniform(0.001, 0.1)
                        self.market_data_latency.labels(
                            exchange=exchange,
                            symbol=symbol,
                            data_type=data_type
                        ).observe(latency)
        
        except Exception as e:
            logger.error(f"Error collecting market data metrics: {e}")
    
    async def collect_risk_metrics(self):
        """Collect portfolio risk metrics"""
        try:
            # Calculate portfolio risk score (0.0 to 1.0)
            risk_score = random.uniform(0.1, 0.8)
            self.portfolio_risk_score.set(risk_score)
            
            # Value at Risk 95%
            var_95 = random.uniform(10000, 100000)
            self.var_95.set(var_95)
            
            # Maximum drawdown
            max_drawdown = random.uniform(0.01, 0.15)
            self.max_drawdown.set(max_drawdown)
            
            # Position-level risk
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
            for symbol in symbols:
                position_risk = random.uniform(0.05, 0.3)
                self.position_risk.labels(symbol=symbol).set(position_risk)
                
                # Capital allocation
                allocation = random.uniform(0.1, 0.3)
                self.capital_allocation.labels(symbol=symbol).set(allocation)
        
        except Exception as e:
            logger.error(f"Error collecting risk metrics: {e}")
    
    async def collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # System CPU and memory
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # API response times (simulated)
            endpoints = ['/api/trade', '/api/market-data', '/api/risk', '/api/portfolio']
            methods = ['GET', 'POST', 'PUT', 'DELETE']
            
            for endpoint in endpoints:
                for method in methods:
                    # Simulate response time
                    response_time = random.uniform(0.01, 2.0)
                    self.api_response_time.labels(
                        endpoint=endpoint,
                        method=method
                    ).observe(response_time)
                    
                    # Simulate request count
                    requests = random.randint(0, 100)
                    status_code = random.choice([200, 201, 400, 404, 500])
                    self.api_request_rate.labels(
                        endpoint=endpoint,
                        method=method,
                        status_code=status_code
                    ).inc(requests)
            
            # Database connections
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM pg_stat_activity")
                db_connections = cursor.fetchone()[0]
                self.database_connections.labels(database='postgres').set(db_connections)
            
            # Redis connections
            if self.redis_client:
                redis_info = self.redis_client.info()
                self.cache_hit_rate.labels(cache_type='redis').set(
                    redis_info.get('keyspace_hits', 0) / 
                    max(redis_info.get('keyspace_hits', 0) + redis_info.get('keyspace_misses', 0), 1)
                )
            
            # Message queue depth
            queue_names = ['trading-orders', 'risk-assessment', 'market-data', 'notifications']
            for queue in queue_names:
                depth = random.randint(0, 1000)
                self.message_queue_depth.labels(queue_name=queue).set(depth)
        
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def collect_compliance_metrics(self):
        """Collect compliance and security metrics"""
        try:
            # Security metrics
            threat_types = ['malware', 'phishing', 'ddos', 'unauthorized_access', 'data_breach']
            severities = ['low', 'medium', 'high', 'critical']
            
            # Random security threats
            for _ in range(random.randint(0, 3)):
                threat_type = random.choice(threat_types)
                severity = random.choice(severities)
                self.security_threats.labels(
                    threat_type=threat_type,
                    severity=severity
                ).inc()
            
            # Authentication failures
            methods = ['password', '2fa', 'certificate', 'oauth']
            for method in methods:
                failures = random.randint(0, 50)
                self.auth_failures.labels(
                    method=method,
                    ip_address='192.168.1.100'
                ).inc(failures)
        
        except Exception as e:
            logger.error(f"Error collecting compliance metrics: {e}")
    
    async def run_collection_cycle(self):
        """Run one complete metrics collection cycle"""
        logger.info("Starting metrics collection cycle")
        
        # Run all collectors concurrently
        tasks = [
            self.collect_trading_metrics(),
            self.collect_market_data_metrics(),
            self.collect_risk_metrics(),
            self.collect_system_metrics(),
            self.collect_compliance_metrics()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("Completed metrics collection cycle")
    
    async def run_continuously(self):
        """Run metrics collection continuously"""
        collection_interval = self.config.get('collection_interval', 15)
        
        logger.info(f"Starting continuous metrics collection (interval: {collection_interval}s)")
        
        while True:
            try:
                await self.run_collection_cycle()
                await asyncio.sleep(collection_interval)
            except KeyboardInterrupt:
                logger.info("Stopping metrics collection")
                break
            except Exception as e:
                logger.error(f"Error in collection cycle: {e}")
                await asyncio.sleep(5)  # Wait before retrying

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables or config file"""
    config = {
        'redis_host': os.getenv('REDIS_HOST', 'localhost'),
        'redis_port': int(os.getenv('REDIS_PORT', '6379')),
        'redis_password': os.getenv('REDIS_PASSWORD', ''),
        'db_host': os.getenv('DB_HOST', 'localhost'),
        'db_port': int(os.getenv('DB_PORT', '5432')),
        'db_name': os.getenv('DB_NAME', 'trading'),
        'db_user': os.getenv('DB_USER', 'postgres'),
        'db_password': os.getenv('DB_PASSWORD', 'changeme'),
        'collection_interval': int(os.getenv('COLLECTION_INTERVAL', '15')),
        'metrics_port': int(os.getenv('METRICS_PORT', '8080')),
        'metrics_host': os.getenv('METRICS_HOST', '0.0.0.0'),
    }
    
    # Load additional config from file if exists
    config_file = os.getenv('CONFIG_FILE', '/etc/trading-metrics/config.json')
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")
    
    return config

async def main():
    """Main function"""
    config = load_config()
    
    # Initialize collector
    collector = TradingMetricsCollector(config)
    
    # Start Prometheus metrics server
    start_http_server(config['metrics_port'], addr=config['metrics_host'])
    logger.info(f"Prometheus metrics server started on {config['metrics_host']}:{config['metrics_port']}")
    
    # Run continuous collection
    await collector.run_continuously()

if __name__ == "__main__":
    import random
    
    # Set random seed for reproducible simulation
    random.seed(42)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        sys.exit(1)