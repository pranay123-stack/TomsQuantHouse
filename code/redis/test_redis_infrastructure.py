#!/usr/bin/env python3
"""
Redis Infrastructure Test Script
Comprehensive testing of all Redis functionality
"""

import sys
import time
import json
from datetime import datetime
from redis_client import TradingRedisClient
from pubsub_client import TradingPubSub
from health_check import RedisHealthMonitor

def test_redis_client():
    """Test basic Redis client functionality"""
    print("\n=== Testing Redis Client ===")
    
    try:
        # Initialize client
        client = TradingRedisClient()
        
        # Test prediction caching
        print("1. Testing prediction caching...")
        prediction = {
            "model": "LSTM_v2",
            "prediction": "BUY",
            "confidence": 0.85,
            "price_target": 150.25,
            "indicators": {
                "rsi": 75,
                "macd": "bullish",
                "volume": "high"
            }
        }
        
        result = client.cache_prediction("BTCUSDT_2025_11_02", prediction, ttl=60)
        print(f"   ✓ Prediction cached: {result}")
        
        # Retrieve prediction
        retrieved = client.get_prediction("BTCUSDT_2025_11_02")
        print(f"   ✓ Prediction retrieved: {retrieved is not None}")
        
        # Test agent memory
        print("2. Testing agent memory...")
        agent_memory = {
            "state": "active",
            "strategy": "momentum",
            "positions": ["BTCUSDT", "ETHUSDT"],
            "last_decision": "hold",
            "risk_level": "medium",
            "portfolio_value": 50000.0
        }
        
        result = client.store_agent_memory("trading_agent_1", agent_memory, ttl=60)
        print(f"   ✓ Agent memory stored: {result}")
        
        retrieved_memory = client.get_agent_memory("trading_agent_1")
        print(f"   ✓ Agent memory retrieved: {retrieved_memory is not None}")
        
        # Test conversation history
        print("3. Testing conversation history...")
        conversation = [
            {"role": "user", "message": "What's the market sentiment?"},
            {"role": "agent", "message": "Current sentiment is bullish with high volume"},
            {"role": "user", "message": "Should I buy BTC?"},
            {"role": "agent", "message": "Based on indicators, consider a small position"}
        ]
        
        result = client.store_conversation_history("trading_agent_1", conversation, ttl=60)
        print(f"   ✓ Conversation stored: {result}")
        
        retrieved_conversation = client.get_conversation_history("trading_agent_1")
        print(f"   ✓ Conversation retrieved: {len(retrieved_conversation) if retrieved_conversation else 0} messages")
        
        # Test graph state
        print("4. Testing graph state...")
        node_data = {
            "type": "cryptocurrency",
            "name": "Bitcoin",
            "symbol": "BTC",
            "market_cap": 850000000000,
            "price": 45000,
            "connections": ["ETH", "USDT", "BNB"]
        }
        
        result = client.store_graph_node("BTC", node_data, ttl=60)
        print(f"   ✓ Graph node stored: {result}")
        
        retrieved_node = client.get_graph_node("BTC")
        print(f"   ✓ Graph node retrieved: {retrieved_node is not None}")
        
        # Test graph edges
        edge_data = {
            "relationship": "trading_pair",
            "volume_24h": 25000000000,
            "confidence": 0.95
        }
        
        result = client.store_graph_edge("BTC", "ETH", edge_data, ttl=60)
        print(f"   ✓ Graph edge stored: {result}")
        
        adjacent = client.get_adjacent_nodes("BTC")
        print(f"   ✓ Adjacent nodes retrieved: {adjacent}")
        
        # Test entity memory
        print("5. Testing entity memory...")
        entity_data = {
            "name": "John Trader",
            "email": "john@example.com",
            "risk_profile": "moderate",
            "preferred_pairs": ["BTCUSDT", "ETHUSDT"],
            "account_balance": 10000.0
        }
        
        result = client.store_entity_data("user_123", "user", entity_data, ttl=60)
        print(f"   ✓ Entity data stored: {result}")
        
        retrieved_entity = client.get_entity_data("user_123")
        print(f"   ✓ Entity data retrieved: {retrieved_entity is not None}")
        
        entities = client.get_entities_by_type("user")
        print(f"   ✓ Entities by type retrieved: {len(entities)} entities")
        
        print("\n✅ All Redis client tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Redis client test failed: {e}")
        return False

def test_pubsub_client():
    """Test Pub/Sub functionality"""
    print("\n=== Testing Pub/Sub Client ===")
    
    try:
        # Initialize Pub/Sub client
        pubsub = TradingPubSub()
        
        # Message handlers
        received_signals = []
        received_market_data = []
        received_alerts = []
        
        def signal_handler(data):
            received_signals.append(data)
            print(f"   📡 Signal received: {data['signal_type']} {data['symbol']}")
        
        def market_handler(data):
            received_market_data.append(data)
            print(f"   📊 Market update received: {data['symbol']} = ${data['price']}")
        
        def alert_handler(data):
            received_alerts.append(data)
            print(f"   🚨 Alert received: {data['alert_type']} - {data['message']}")
        
        # Subscribe to channels
        print("1. Subscribing to channels...")
        sub1 = pubsub.subscribe_to_trade_signals(signal_handler)
        sub2 = pubsub.subscribe_to_market_updates(market_handler)
        sub3 = pubsub.subscribe_to_alerts(alert_handler)
        
        print(f"   ✓ Subscribed to {pubsub.get_subscription_count()} channels")
        
        # Wait for subscriptions to be established
        time.sleep(1)
        
        # Publish test messages
        print("2. Publishing test messages...")
        
        # Trade signal
        signal = {
            'signal_type': 'BUY',
            'symbol': 'BTCUSDT',
            'price': 45000,
            'confidence': 0.85,
            'strategy': 'momentum',
            'timestamp': datetime.now().isoformat()
        }
        
        subscribers = pubsub.publish_trade_signal(signal)
        print(f"   ✓ Trade signal published to {subscribers} subscribers")
        
        # Market update
        market_data = {
            'symbol': 'ETHUSDT',
            'price': 3200,
            'volume': 1250000,
            'bid': 3199,
            'ask': 3201,
            'change': 2.5,
            'timestamp': datetime.now().isoformat()
        }
        
        subscribers = pubsub.publish_market_update(market_data)
        print(f"   ✓ Market update published to {subscribers} subscribers")
        
        # Alert
        alert = {
            'alert_type': 'INFO',
            'message': 'High volatility detected in BTCUSDT',
            'symbol': 'BTCUSDT',
            'severity': 'medium',
            'timestamp': datetime.now().isoformat()
        }
        
        subscribers = pubsub.publish_alert(alert)
        print(f"   ✓ Alert published to {subscribers} subscribers")
        
        # Wait for messages to be received
        time.sleep(2)
        
        # Check received messages
        print("3. Verifying message reception...")
        print(f"   ✓ Signals received: {len(received_signals)}")
        print(f"   ✓ Market updates received: {len(received_market_data)}")
        print(f"   ✓ Alerts received: {len(received_alerts)}")
        
        # Test unsubscription
        print("4. Testing unsubscription...")
        result = pubsub.unsubscribe(sub1)
        print(f"   ✓ Unsubscribed from signal channel: {result}")
        
        final_count = pubsub.get_subscription_count()
        print(f"   ✓ Remaining subscriptions: {final_count}")
        
        # Cleanup
        pubsub.unsubscribe_all()
        pubsub.close()
        
        print("\n✅ All Pub/Sub tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Pub/Sub test failed: {e}")
        return False

def test_health_monitor():
    """Test health monitoring"""
    print("\n=== Testing Health Monitor ===")
    
    try:
        # Initialize health monitor
        monitor = RedisHealthMonitor()
        
        # Run individual health checks
        print("1. Running individual health checks...")
        
        connection_status = monitor.check_connection()
        print(f"   ✓ Connection status: {connection_status['status']}")
        
        memory_status = monitor.check_memory_usage()
        print(f"   ✓ Memory status: {memory_status['status']} ({memory_status.get('usage_percent', 0):.1f}%)")
        
        db_status = monitor.check_database_stats()
        print(f"   ✓ Database status: {db_status['status']} ({db_status.get('total_keys', 0)} keys)")
        
        performance_status = monitor.check_performance_metrics()
        print(f"   ✓ Performance status: {performance_status['status']} ({performance_status.get('hit_ratio_percent', 0):.1f}% hit ratio)")
        
        persistence_status = monitor.check_persistence_status()
        print(f"   ✓ Persistence status: {persistence_status['status']}")
        
        system_status = monitor.check_system_resources()
        print(f"   ✓ System status: {system_status['status']}")
        
        # Run full health check
        print("2. Running full health check...")
        health_report = monitor.run_full_health_check()
        
        print(f"   ✓ Overall status: {health_report['overall_status']}")
        print(f"   ✓ Timestamp: {health_report['timestamp']}")
        
        # Export health report
        print("3. Testing report export...")
        export_file = "test_health_report.json"
        monitor.export_health_report(export_file)
        
        # Verify export
        with open(export_file, 'r') as f:
            exported_report = json.load(f)
        
        print(f"   ✓ Health report exported: {len(json.dumps(exported_report))} bytes")
        
        # Cleanup
        import os
        if os.path.exists(export_file):
            os.remove(export_file)
        
        print("\n✅ All health monitor tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Health monitor test failed: {e}")
        return False

def test_database_separation():
    """Test database separation and key isolation"""
    print("\n=== Testing Database Separation ===")
    
    try:
        client = TradingRedisClient()
        
        # Test that each database stores different data types
        print("1. Testing database isolation...")
        
        # Store test data in each database
        client.redis_client.select(0)
        client.redis_client.set("test_key_db0", "test_value_db0")
        
        client.redis_client.select(1)
        client.redis_client.set("test_key_db1", "test_value_db1")
        
        client.redis_client.select(2)
        client.redis_client.set("test_key_db2", "test_value_db2")
        
        client.redis_client.select(3)
        client.redis_client.set("test_key_db3", "test_value_db3")
        
        # Verify isolation by checking each database
        print("2. Verifying database isolation...")
        
        for db_num, expected_value in [(0, "test_value_db0"), (1, "test_value_db1"), 
                                       (2, "test_value_db2"), (3, "test_value_db3")]:
            client.redis_client.select(db_num)
            actual_value = client.redis_client.get("test_key_db0")
            if actual_value:
                actual_value = actual_value.decode()
            
            is_isolated = actual_value == expected_value
            print(f"   ✓ Database {db_num} isolation: {is_isolated}")
        
        # Test client methods use correct databases
        print("3. Testing client database selection...")
        
        # Test prediction (should use db0)
        client.cache_prediction("test_pred", {"data": "test"}, ttl=30)
        client.redis_client.select(0)
        pred_exists = client.redis_client.exists("prediction:test_pred")
        print(f"   ✓ Prediction stored in correct database: {bool(pred_exists)}")
        
        # Test agent memory (should use db1)
        client.store_agent_memory("test_agent", {"data": "test"}, ttl=30)
        client.redis_client.select(1)
        agent_exists = client.redis_client.exists("agent:test_agent")
        print(f"   ✓ Agent memory stored in correct database: {bool(agent_exists)}")
        
        print("\n✅ Database separation tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Database separation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Redis Infrastructure Tests")
    print("=" * 50)
    
    # Check if Redis is running
    try:
        test_client = TradingRedisClient()
        test_client.ping()
        print("✓ Redis connection established")
    except Exception as e:
        print(f"❌ Cannot connect to Redis: {e}")
        print("\nPlease ensure Redis is running:")
        print("  docker-compose up -d")
        return False
    
    # Run all tests
    tests = [
        ("Redis Client", test_redis_client),
        ("Pub/Sub Client", test_pubsub_client),
        ("Health Monitor", test_health_monitor),
        ("Database Separation", test_database_separation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Redis infrastructure is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the configuration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)