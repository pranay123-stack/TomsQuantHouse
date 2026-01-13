"""
Trading API Instrumentation with OpenTelemetry
Provides tracing, metrics, and logging for trading operations
"""

import logging
import time
import json
from typing import Any, Dict, Optional
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.pymongo import MongoDBInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicMetricReader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class TradingInstrumentor:
    """Comprehensive instrumentation for trading system"""
    
    def __init__(self, service_name: str, jaeger_endpoint: str = "http://jaeger-collector:14268/api/traces"):
        self.service_name = service_name
        self.jaeger_endpoint = jaeger_endpoint
        self.tracer = None
        self.meter = None
        self._initialize_tracing()
        self._initialize_metrics()
    
    def _initialize_tracing(self):
        """Initialize distributed tracing"""
        # Set tracer provider
        trace.set_tracer_provider(TracerProvider())
        
        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name="jaeger-agent",
            agent_port=6831,
        )
        
        # Add span processor
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        self.tracer = trace.get_tracer(__name__)
        
        # Instrument Flask, Redis, etc.
        FlaskInstrumentor().instrument()
        RedisInstrumentor().instrument()
        RequestsInstrumentor().instrument()
    
    def _initialize_metrics(self):
        """Initialize metrics collection"""
        # Set meter provider
        metrics.set_meter_provider(MeterProvider())
        
        self.meter = metrics.get_meter(__name__)
        
        # Create custom trading metrics
        self._create_trading_metrics()
    
    def _create_trading_metrics(self):
        """Create trading-specific metrics"""
        
        # Trading decision counters
        self.trading_decisions = self.meter.create_counter(
            "trading_decisions_total",
            description="Total number of trading decisions",
            unit="decisions"
        )
        
        # Trading profit/loss counter
        self.trading_profit_loss = self.meter.create_counter(
            "trading_profit_loss_total",
            description="Total profit and loss",
            unit="USD"
        )
        
        # Trading latency histogram
        self.trading_latency = self.meter.create_histogram(
            "trading_latency_seconds",
            description="Trading operation latency",
            unit="seconds"
        )
        
        # Market data metrics
        self.market_data_latency = self.meter.create_histogram(
            "market_data_latency_seconds",
            description="Market data retrieval latency",
            unit="seconds"
        )
        
        # Risk metrics
        self.portfolio_risk_score = self.meter.create_gauge(
            "portfolio_risk_score",
            description="Current portfolio risk score",
            unit="score"
        )
        
        # Trading volume
        self.trading_volume = self.meter.create_counter(
            "trading_volume_total",
            description="Trading volume",
            unit="USD"
        )
        
        # Order processing metrics
        self.order_processing_time = self.meter.create_histogram(
            "order_processing_duration_seconds",
            description="Order processing duration",
            unit="seconds"
        )
        
        # API request metrics
        self.api_requests = self.meter.create_counter(
            "api_requests_total",
            description="Total API requests",
            unit="requests"
        )
        
        self.api_request_duration = self.meter.create_histogram(
            "api_request_duration_seconds",
            description="API request duration",
            unit="seconds"
        )
    
    @contextmanager
    def trading_operation(self, operation_name: str, algorithm: str, symbol: str = None):
        """Context manager for tracing trading operations"""
        attributes = {
            "service.name": self.service_name,
            "operation.type": "trading",
            "operation.name": operation_name,
            "trading.algorithm": algorithm,
        }
        
        if symbol:
            attributes["trading.symbol"] = symbol
        
        with self.tracer.start_as_current_span(operation_name, attributes=attributes) as span:
            start_time = time.time()
            try:
                yield span
                span.set_attribute("trading.success", True)
                span.set_attribute("trading.error", False)
            except Exception as e:
                span.set_attribute("trading.success", False)
                span.set_attribute("trading.error", True)
                span.set_attribute("trading.error_message", str(e))
                span.set_attribute("error", True)
                span.set_attribute("error.kind", type(e).__name__)
                raise
            finally:
                duration = time.time() - start_time
                span.set_attribute("trading.duration", duration)
                
                # Record metrics
                self.trading_latency.record(duration)
    
    @contextmanager
    def market_data_operation(self, exchange: str, symbol: str, data_type: str):
        """Context manager for market data operations"""
        attributes = {
            "service.name": self.service_name,
            "operation.type": "market_data",
            "market.exchange": exchange,
            "market.symbol": symbol,
            "market.data_type": data_type,
        }
        
        with self.tracer.start_as_current_span("market_data_retrieval", attributes=attributes) as span:
            start_time = time.time()
            try:
                yield span
                span.set_attribute("market_data.success", True)
            except Exception as e:
                span.set_attribute("market_data.success", False)
                span.set_attribute("market_data.error", str(e))
                raise
            finally:
                duration = time.time() - start_time
                span.set_attribute("market_data.duration", duration)
                
                # Record metrics
                self.market_data_latency.record(duration)
                self.api_requests.add(1, {"endpoint": "market_data", "status": "success" if span.attributes.get("market_data.success") else "error"})
    
    def record_trading_decision(self, algorithm: str, symbol: str, outcome: str, profit_loss: float = 0):
        """Record trading decision metrics"""
        attributes = {
            "trading.algorithm": algorithm,
            "trading.symbol": symbol,
            "trading.outcome": outcome,
        }
        
        self.trading_decisions.add(1, attributes)
        
        if profit_loss != 0:
            self.trading_profit_loss.add(profit_loss, attributes)
        
        # Record trading volume
        self.trading_volume.add(abs(profit_loss), attributes)
    
    def update_risk_metrics(self, risk_score: float, var_95: float, max_drawdown: float):
        """Update portfolio risk metrics"""
        self.portfolio_risk_score.set(risk_score)
        
        # Add additional risk metrics
        self.meter.create_gauge("var_95").set(var_95)
        self.meter.create_gauge("max_drawdown").set(max_drawdown)
    
    def record_api_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Record API request metrics"""
        self.api_requests.add(1, {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code
        })
        
        self.api_request_duration.record(duration, {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code
        })
    
    def record_order_processing(self, order_type: str, status: str, duration: float):
        """Record order processing metrics"""
        self.order_processing_time.record(duration, {
            "order.type": order_type,
            "order.status": status
        })
    
    def add_custom_trace(self, span_name: str, attributes: Dict[str, Any]):
        """Add custom trace with attributes"""
        with self.tracer.start_as_current_span(span_name, attributes={**attributes, "service.name": self.service_name}) as span:
            return span

# Example usage
def main():
    """Example of using trading instrumentation"""
    instrumentor = TradingInstrumentor("trading-api")
    
    # Example trading operation
    with instrumentor.trading_operation("execute_trade", "momentum_algorithm", "AAPL") as span:
        span.set_attribute("trading.side", "buy")
        span.set_attribute("trading.quantity", 100)
        span.set_attribute("trading.price", 150.0)
        
        # Simulate trading logic
        time.sleep(0.1)  # Trading operation
        
        # Record decision
        instrumentor.record_trading_decision("momentum_algorithm", "AAPL", "win", 50.0)
    
    # Example market data operation
    with instrumentor.market_data_operation("NASDAQ", "AAPL", "price") as span:
        time.sleep(0.05)  # Data retrieval
        
        span.set_attribute("market.data_points", 10)
        span.set_attribute("market.last_price", 150.25)
    
    # Example API request
    instrumentor.record_api_request("/api/trade", "POST", 200, 0.15)
    
    # Example order processing
    instrumentor.record_order_processing("market", "completed", 0.25)
    
    # Example risk metrics
    instrumentor.update_risk_metrics(0.6, 10000.0, 0.05)
    
    print("Instrumentation examples completed")

if __name__ == "__main__":
    main()