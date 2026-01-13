#!/usr/bin/env python3
"""
Database Optimization and Connection Pooling
Optimizes database queries and manages connection pooling for improved performance
"""

import asyncio
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import psycopg2
import psycopg2.pool
import psycopg2.extras
import redis
import sqlite3
from contextlib import contextmanager
from functools import wraps
import threading
import weakref
from pathlib import Path

class DatabaseEngine(Enum):
    """Supported database engines"""
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    SQLITE = "sqlite"
    MYSQL = "mysql"

class ConnectionPoolType(Enum):
    """Connection pool types"""
    SIMPLE = "simple"
    THREADED = "threaded"
    STUBBORN = "stubborn"

@dataclass
class QueryMetrics:
    """Database query performance metrics"""
    query_id: str
    query_text: str
    execution_time: float
    rows_affected: int
    rows_returned: int
    timestamp: datetime
    connection_id: str
    cache_hit: bool
    status: str  # success, error, timeout
    error_message: Optional[str] = None

@dataclass
class ConnectionPoolMetrics:
    """Connection pool performance metrics"""
    timestamp: datetime
    pool_size: int
    active_connections: int
    idle_connections: int
    waiting_requests: int
    total_requests: int
    failed_requests: int
    average_wait_time: float
    max_wait_time: float

@dataclass
class DatabaseOptimization:
    """Database optimization recommendation"""
    optimization_id: str
    category: str  # index, query, configuration, schema
    priority: str  # high, medium, low
    title: str
    description: str
    potential_improvement: float  # percentage improvement
    implementation_effort: str  # low, medium, high
    estimated_impact: str

class ConnectionPool:
    """Enhanced connection pool with performance monitoring"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.engine = DatabaseEngine(config.get('engine', 'postgresql'))
        self.pool_type = ConnectionPoolType(config.get('pool_type', 'simple'))
        
        # Pool configuration
        self.min_connections = config.get('min_connections', 5)
        self.max_connections = config.get('max_connections', 20)
        self.connection_timeout = config.get('connection_timeout', 30)
        self.idle_timeout = config.get('idle_timeout', 600)
        self.max_retries = config.get('max_retries', 3)
        
        # Internal state
        self.connections = []
        self.active_connections = set()
        self.waiting_queue = asyncio.Queue()
        self.metrics = []
        self.lock = asyncio.Lock()
        self.connection_counter = 0
        
        # Initialize pool
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        try:
            if self.engine == DatabaseEngine.POSTGRESQL:
                self._initialize_postgresql_pool()
            elif self.engine == DatabaseEngine.REDIS:
                self._initialize_redis_pool()
            elif self.engine == DatabaseEngine.SQLITE:
                self._initialize_sqlite_pool()
            else:
                raise ValueError(f"Unsupported database engine: {self.engine}")
            
            self.logger.info(f"Connection pool initialized with {len(self.connections)} connections")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def _initialize_postgresql_pool(self):
        """Initialize PostgreSQL connection pool"""
        database_config = self.config.get('database', {})
        
        for i in range(self.min_connections):
            try:
                conn = psycopg2.connect(
                    host=database_config.get('host', 'localhost'),
                    port=database_config.get('port', 5432),
                    database=database_config.get('database', 'postgres'),
                    user=database_config.get('user', 'postgres'),
                    password=database_config.get('password', ''),
                    cursor_factory=psycopg2.extras.RealDictCursor
                )
                
                self.connections.append({
                    'connection': conn,
                    'created_at': time.time(),
                    'last_used': time.time(),
                    'connection_id': f"pg_conn_{i}",
                    'in_use': False
                })
                
            except Exception as e:
                self.logger.error(f"Failed to create PostgreSQL connection {i}: {e}")
    
    def _initialize_redis_pool(self):
        """Initialize Redis connection pool"""
        redis_config = self.config.get('redis', {})
        
        pool = redis.ConnectionPool(
            host=redis_config.get('host', 'localhost'),
            port=redis_config.get('port', 6379),
            db=redis_config.get('db', 0),
            password=redis_config.get('password'),
            max_connections=self.max_connections,
            socket_timeout=self.connection_timeout,
            socket_connect_timeout=self.connection_timeout,
            health_check_interval=30
        )
        
        self.redis_pool = redis.Redis(connection_pool=pool)
        
        # Test connection
        self.redis_pool.ping()
        self.logger.info("Redis pool initialized successfully")
    
    def _initialize_sqlite_pool(self):
        """Initialize SQLite connection pool"""
        db_path = self.config.get('database', {}).get('path', ':memory:')
        
        for i in range(self.min_connections):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            self.connections.append({
                'connection': conn,
                'created_at': time.time(),
                'last_used': time.time(),
                'connection_id': f"sqlite_conn_{i}",
                'in_use': False
            })
    
    async def get_connection(self) -> Any:
        """Get a connection from the pool"""
        async with self.lock:
            # Try to get an existing idle connection
            for conn_info in self.connections:
                if not conn_info['in_use']:
                    conn_info['in_use'] = True
                    conn_info['last_used'] = time.time()
                    self.active_connections.add(conn_info['connection_id'])
                    
                    # Record metrics
                    self._record_pool_metrics(wait_time=0)
                    return conn_info['connection']
            
            # No idle connections available, create new one if under max
            if len(self.connections) < self.max_connections:
                new_connection = self._create_new_connection()
                if new_connection:
                    conn_id = f"dynamic_conn_{self.connection_counter}"
                    self.connection_counter += 1
                    
                    conn_info = {
                        'connection': new_connection,
                        'created_at': time.time(),
                        'last_used': time.time(),
                        'connection_id': conn_id,
                        'in_use': True
                    }
                    
                    self.connections.append(conn_info)
                    self.active_connections.add(conn_id)
                    
                    self._record_pool_metrics(wait_time=0)
                    return new_connection
            
            # No connections available, add to waiting queue
            try:
                await asyncio.wait_for(self.waiting_queue.put(None), timeout=self.connection_timeout)
                self._record_pool_metrics(wait_time=0.1)  # Estimated wait time
                # This is a simplified implementation
                # In production, you'd properly handle the queue
            except asyncio.TimeoutError:
                raise Exception("Connection pool exhausted")
    
    def _create_new_connection(self) -> Optional[Any]:
        """Create a new database connection"""
        try:
            if self.engine == DatabaseEngine.POSTGRESQL:
                return psycopg2.connect(
                    host=self.config.get('database', {}).get('host', 'localhost'),
                    port=self.config.get('database', {}).get('port', 5432),
                    database=self.config.get('database', {}).get('database', 'postgres'),
                    user=self.config.get('database', {}).get('user', 'postgres'),
                    password=self.config.get('database', {}).get('password', ''),
                    cursor_factory=psycopg2.extras.RealDictCursor
                )
            elif self.engine == DatabaseEngine.REDIS:
                return self.redis_pool
            elif self.engine == DatabaseEngine.SQLITE:
                return sqlite3.connect(':memory:', check_same_thread=False)
        except Exception as e:
            self.logger.error(f"Failed to create new connection: {e}")
        return None
    
    async def return_connection(self, connection: Any):
        """Return a connection to the pool"""
        async with self.lock:
            for conn_info in self.connections:
                if conn_info['connection'] is connection:
                    conn_info['in_use'] = False
                    self.active_connections.discard(conn_info['connection_id'])
                    break
    
    def _record_pool_metrics(self, wait_time: float = 0):
        """Record connection pool metrics"""
        metrics = ConnectionPoolMetrics(
            timestamp=datetime.now(),
            pool_size=len(self.connections),
            active_connections=len(self.active_connections),
            idle_connections=len(self.connections) - len(self.active_connections),
            waiting_requests=self.waiting_queue.qsize(),
            total_requests=1,  # Would track actual requests
            failed_requests=0,
            average_wait_time=wait_time,
            max_wait_time=wait_time
        )
        
        self.metrics.append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-1000:]
    
    def get_pool_stats(self) -> Dict:
        """Get current pool statistics"""
        return {
            'pool_size': len(self.connections),
            'active_connections': len(self.active_connections),
            'idle_connections': len(self.connections) - len(self.active_connections),
            'waiting_requests': self.waiting_queue.qsize(),
            'engine': self.engine.value,
            'pool_type': self.pool_type.value
        }

class QueryOptimizer:
    """Database query optimizer"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.query_metrics = []
        self.slow_query_threshold = config.get('slow_query_threshold', 1.0)  # seconds
        self.cache = {}
        self.cache_ttl = config.get('cache_ttl', 300)  # 5 minutes
    
    def monitor_query(self, query: str) -> Callable:
        """Decorator to monitor query performance"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                query_id = f"query_{int(time.time())}_{len(self.query_metrics)}"
                
                try:
                    result = await func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Record metrics
                    self._record_query_metrics(
                        query_id=query_id,
                        query=query,
                        execution_time=execution_time,
                        rows_affected=getattr(result, 'rowcount', 0),
                        rows_returned=len(result) if hasattr(result, '__len__') else 1,
                        status='success'
                    )
                    
                    return result
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    
                    self._record_query_metrics(
                        query_id=query_id,
                        query=query,
                        execution_time=execution_time,
                        rows_affected=0,
                        rows_returned=0,
                        status='error',
                        error_message=str(e)
                    )
                    
                    raise
            
            return wrapper
        return decorator
    
    def _record_query_metrics(self, **kwargs):
        """Record query performance metrics"""
        metrics = QueryMetrics(
            query_id=kwargs['query_id'],
            query_text=kwargs['query'],
            execution_time=kwargs['execution_time'],
            rows_affected=kwargs['rows_affected'],
            rows_returned=kwargs['rows_returned'],
            timestamp=datetime.now(),
            connection_id='unknown',
            cache_hit=False,
            status=kwargs['status'],
            error_message=kwargs.get('error_message')
        )
        
        self.query_metrics.append(metrics)
        
        # Keep only last 10000 metrics
        if len(self.query_metrics) > 10000:
            self.query_metrics = self.query_metrics[-10000:]
    
    def analyze_slow_queries(self) -> List[QueryMetrics]:
        """Identify and analyze slow queries"""
        slow_queries = [
            metric for metric in self.query_metrics 
            if metric.execution_time > self.slow_query_threshold and metric.status == 'success'
        ]
        
        # Sort by execution time descending
        slow_queries.sort(key=lambda x: x.execution_time, reverse=True)
        
        return slow_queries[:10]  # Return top 10 slowest queries
    
    def generate_optimization_recommendations(self) -> List[DatabaseOptimization]:
        """Generate database optimization recommendations"""
        recommendations = []
        
        # Analyze slow queries
        slow_queries = self.analyze_slow_queries()
        
        if slow_queries:
            recommendations.append(DatabaseOptimization(
                optimization_id="slow_queries",
                category="query",
                priority="high",
                title="Optimize Slow Queries",
                description=f"Found {len(slow_queries)} slow queries exceeding {self.slow_query_threshold}s threshold",
                potential_improvement=30.0,
                implementation_effort="medium",
                estimated_impact="Significant performance improvement for frequent queries"
            ))
        
        # Check for missing indexes (simplified analysis)
        for query in slow_queries:
            if "WHERE" in query.query_text.upper() and "JOIN" in query.query_text.upper():
                recommendations.append(DatabaseOptimization(
                    optimization_id=f"index_{query.query_id}",
                    category="index",
                    priority="medium",
                    title="Add Database Indexes",
                    description="Queries with WHERE and JOIN clauses may benefit from additional indexes",
                    potential_improvement=50.0,
                    implementation_effort="low",
                    estimated_impact="Faster query execution for filtered and joined data"
                ))
        
        # Check connection pool efficiency
        if len(self.query_metrics) > 100:
            recent_metrics = [m for m in self.query_metrics if 
                            (datetime.now() - m.timestamp).seconds < 3600]
            if recent_metrics:
                avg_execution_time = sum(m.execution_time for m in recent_metrics) / len(recent_metrics)
                if avg_execution_time > 0.5:
                    recommendations.append(DatabaseOptimization(
                        optimization_id="connection_pool",
                        category="configuration",
                        priority="medium",
                        title="Optimize Connection Pool",
                        description="High average query execution time may indicate connection pool issues",
                        potential_improvement=20.0,
                        implementation_effort="low",
                        estimated_impact="Better connection utilization and reduced wait times"
                    ))
        
        return recommendations
    
    def get_query_performance_summary(self) -> Dict:
        """Get summary of query performance statistics"""
        if not self.query_metrics:
            return {"error": "No query metrics available"}
        
        recent_metrics = [m for m in self.query_metrics if 
                         (datetime.now() - m.timestamp).seconds < 3600]
        
        if not recent_metrics:
            recent_metrics = self.query_metrics
        
        total_queries = len(recent_metrics)
        successful_queries = [m for m in recent_metrics if m.status == 'success']
        failed_queries = [m for m in recent_metrics if m.status == 'error']
        
        avg_execution_time = sum(m.execution_time for m in successful_queries) / len(successful_queries) if successful_queries else 0
        
        p95_execution_time = sorted([m.execution_time for m in successful_queries])[int(len(successful_queries) * 0.95)] if successful_queries else 0
        
        return {
            'total_queries': total_queries,
            'successful_queries': len(successful_queries),
            'failed_queries': len(failed_queries),
            'success_rate': len(successful_queries) / total_queries if total_queries > 0 else 0,
            'average_execution_time': avg_execution_time,
            'p95_execution_time': p95_execution_time,
            'slow_queries_count': len([m for m in recent_metrics if m.execution_time > self.slow_query_threshold])
        }

class DatabaseOptimizer:
    """Main database optimization orchestrator"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.connection_pool = ConnectionPool(config.get('connection_pool', {}))
        self.query_optimizer = QueryOptimizer(config.get('query_optimizer', {}))
        
        # Performance monitoring
        self.optimization_history = []
        self.performance_baselines = {}
    
    @contextmanager
    async def get_db_connection(self):
        """Context manager for database connections"""
        connection = await self.connection_pool.get_connection()
        try:
            yield connection
        finally:
            await self.connection_pool.return_connection(connection)
    
    async def execute_optimized_query(self, query: str, params: Tuple = None, use_cache: bool = True) -> Any:
        """Execute a query with optimization and monitoring"""
        start_time = time.time()
        
        # Check cache
        cache_key = f"{query}:{str(params)}"
        if use_cache and cache_key in self.query_optimizer.cache:
            cached_result, timestamp = self.query_optimizer.cache[cache_key]
            if time.time() - timestamp < self.query_optimizer.cache_ttl:
                # Cache hit
                self.query_optimizer._record_query_metrics(
                    query_id=f"cache_hit_{int(time.time())}",
                    query=query,
                    execution_time=0.001,  # Cache hit is very fast
                    rows_affected=len(cached_result),
                    rows_returned=len(cached_result),
                    status='success'
                )
                return cached_result
        
        try:
            async with self.get_db_connection() as conn:
                if isinstance(conn, sqlite3.Connection):
                    # SQLite execution
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    result = cursor.fetchall()
                elif hasattr(conn, 'cursor'):
                    # PostgreSQL execution
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    result = cursor.fetchall()
                else:
                    # Redis execution
                    if query.upper().startswith('GET'):
                        result = conn.get(query[4:].strip())
                    elif query.upper().startswith('SET'):
                        key, value = query[4:].split(' ', 1)
                        conn.set(key, value)
                        result = "OK"
                    else:
                        result = conn.execute(query)
                
                # Cache the result if caching is enabled
                if use_cache:
                    self.query_optimizer.cache[cache_key] = (result, time.time())
                
                execution_time = time.time() - start_time
                
                # Record metrics
                self.query_optimizer._record_query_metrics(
                    query_id=f"query_{int(time.time())}",
                    query=query,
                    execution_time=execution_time,
                    rows_affected=len(result) if hasattr(result, '__len__') else 1,
                    rows_returned=len(result) if hasattr(result, '__len__') else 1,
                    status='success'
                )
                
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.query_optimizer._record_query_metrics(
                query_id=f"query_{int(time.time())}",
                query=query,
                execution_time=execution_time,
                rows_affected=0,
                rows_returned=0,
                status='error',
                error_message=str(e)
            )
            
            raise
    
    async def optimize_database(self) -> List[DatabaseOptimization]:
        """Run comprehensive database optimization analysis"""
        self.logger.info("Starting database optimization analysis")
        
        # Get recommendations from query optimizer
        recommendations = self.query_optimizer.generate_optimization_recommendations()
        
        # Add connection pool optimization recommendations
        pool_stats = self.connection_pool.get_pool_stats()
        if pool_stats['active_connections'] == pool_stats['pool_size']:
            recommendations.append(DatabaseOptimization(
                optimization_id="connection_pool_sizing",
                category="configuration",
                priority="medium",
                title="Optimize Connection Pool Size",
                description="All connections are active, consider increasing pool size",
                potential_improvement=15.0,
                implementation_effort="low",
                estimated_impact="Reduced connection wait times"
            ))
        
        # Record optimization session
        optimization_session = {
            'timestamp': datetime.now(),
            'recommendations': [asdict(rec) for rec in recommendations],
            'pool_stats': pool_stats,
            'query_performance': self.query_optimizer.get_query_performance_summary()
        }
        
        self.optimization_history.append(optimization_session)
        
        self.logger.info(f"Database optimization completed with {len(recommendations)} recommendations")
        
        return recommendations
    
    def export_optimization_report(self, filepath: str):
        """Export optimization report to file"""
        report = {
            'optimization_history': self.optimization_history,
            'current_pool_stats': self.connection_pool.get_pool_stats(),
            'query_performance_summary': self.query_optimizer.get_query_performance_summary(),
            'slow_queries': [asdict(q) for q in self.query_optimizer.analyze_slow_queries()],
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.info(f"Optimization report exported to {filepath}")

def create_sample_db_config() -> Dict:
    """Create sample database configuration"""
    return {
        'connection_pool': {
            'engine': 'postgresql',
            'pool_type': 'simple',
            'min_connections': 5,
            'max_connections': 20,
            'connection_timeout': 30,
            'idle_timeout': 600,
            'max_retries': 3,
            'database': {
                'host': 'localhost',
                'port': 5432,
                'database': 'performance_test',
                'user': 'postgres',
                'password': 'password'
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0,
                'password': None
            }
        },
        'query_optimizer': {
            'slow_query_threshold': 1.0,
            'cache_ttl': 300
        }
    }

def main():
    """Example usage and testing"""
    async def demo_database_optimization():
        # Create sample configuration
        config = create_sample_db_config()
        
        # Initialize database optimizer
        db_optimizer = DatabaseOptimizer(config)
        
        print("Database Optimization Demo")
        print("=" * 50)
        
        # Test query execution
        try:
            print("Testing query execution...")
            
            # Example queries (adjust based on your actual database)
            test_queries = [
                "SELECT 1",
                "SELECT version()",
                "SELECT current_timestamp"
            ]
            
            for query in test_queries:
                try:
                    result = await db_optimizer.execute_optimized_query(query)
                    print(f"Query executed successfully: {query[:30]}...")
                except Exception as e:
                    print(f"Query failed: {query[:30]}... - {e}")
            
            # Get performance summary
            summary = db_optimizer.query_optimizer.get_query_performance_summary()
            print(f"\nQuery Performance Summary:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
            
            # Run optimization analysis
            print("\nRunning optimization analysis...")
            recommendations = await db_optimizer.optimize_database()
            
            print(f"\nOptimization Recommendations:")
            for rec in recommendations:
                print(f"  {rec.title} ({rec.priority} priority)")
                print(f"    {rec.description}")
                print(f"    Potential improvement: {rec.potential_improvement}%")
            
            # Export report
            db_optimizer.export_optimization_report('/tmp/db_optimization_report.json')
            print(f"\nOptimization report exported")
            
        except Exception as e:
            print(f"Demo failed: {e}")
    
    # Run the demo
    asyncio.run(demo_database_optimization())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()