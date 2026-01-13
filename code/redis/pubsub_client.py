"""
Redis Pub/Sub Client for Real-time Trade Signals
Provides real-time communication for trading framework
"""

import redis
import json
import threading
import time
import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingPubSub:
    """Redis Pub/Sub client for real-time trade signals"""
    
    def __init__(self, host='localhost', port=6379, password='trading_framework_2025'):
        """Initialize Pub/Sub client"""
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                password=password,
                decode_responses=True,  # Pub/Sub typically uses JSON strings
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True
            )
            
            self.pubsub = self.redis_client.pubsub()
            self.subscribers = {}
            self.running = False
            self.listener_thread = None
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Pub/Sub client connected to Redis on {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis for Pub/Sub: {e}")
            raise
    
    # =============================================================================
    # PUBLISH METHODS
    # =============================================================================
    
    def publish_trade_signal(self, signal_data: Dict[str, Any]) -> int:
        """
        Publish trading signal to all subscribers
        
        Args:
            signal_data: Dictionary containing signal information
                Required fields:
                - signal_type: 'BUY', 'SELL', 'HOLD'
                - symbol: Trading pair (e.g., 'BTCUSDT')
                - price: Current price
                - timestamp: Signal timestamp
                Optional fields:
                - confidence: Signal confidence (0-1)
                - strategy: Strategy name
                - metadata: Additional information
        
        Returns:
            int: Number of subscribers who received the signal
        """
        try:
            # Validate required fields
            required_fields = ['signal_type', 'symbol', 'price', 'timestamp']
            for field in required_fields:
                if field not in signal_data:
                    logger.error(f"Missing required field: {field}")
                    return 0
            
            # Add metadata
            signal_data['received_at'] = datetime.now().isoformat()
            signal_data['channel'] = 'trade_signals'
            
            # Publish to main trading signals channel
            message = json.dumps(signal_data)
            subscribers = self.redis_client.publish('trade_signals', message)
            
            # Also publish to symbol-specific channel
            symbol_channel = f"trade_signals:{signal_data['symbol']}"
            symbol_subscribers = self.redis_client.publish(symbol_channel, message)
            
            logger.info(f"Published {signal_data['signal_type']} signal for {signal_data['symbol']} to {subscribers} subscribers")
            return subscribers
            
        except Exception as e:
            logger.error(f"Failed to publish trade signal: {e}")
            return 0
    
    def publish_market_update(self, market_data: Dict[str, Any]) -> int:
        """
        Publish market data updates
        
        Args:
            market_data: Dictionary containing market information
                Required fields:
                - symbol: Trading pair
                - price: Current price
                - volume: Trading volume
                - timestamp: Update timestamp
                Optional fields:
                - bid, ask: Bid/Ask prices
                - high, low: 24h high/low
                - change: Price change
        
        Returns:
            int: Number of subscribers who received the update
        """
        try:
            market_data['channel'] = 'market_updates'
            market_data['received_at'] = datetime.now().isoformat()
            
            message = json.dumps(market_data)
            subscribers = self.redis_client.publish('market_updates', message)
            
            # Publish to symbol-specific channel
            symbol_channel = f"market_updates:{market_data['symbol']}"
            symbol_subscribers = self.redis_client.publish(symbol_channel, message)
            
            logger.info(f"Published market update for {market_data['symbol']} to {subscribers} subscribers")
            return subscribers
            
        except Exception as e:
            logger.error(f"Failed to publish market update: {e}")
            return 0
    
    def publish_alert(self, alert_data: Dict[str, Any]) -> int:
        """
        Publish trading alerts
        
        Args:
            alert_data: Dictionary containing alert information
                Required fields:
                - alert_type: 'WARNING', 'ERROR', 'INFO', 'CRITICAL'
                - message: Alert message
                - timestamp: Alert timestamp
                Optional fields:
                - symbol: Related symbol
                - severity: Alert severity level
        
        Returns:
            int: Number of subscribers who received the alert
        """
        try:
            alert_data['channel'] = 'alerts'
            alert_data['received_at'] = datetime.now().isoformat()
            
            message = json.dumps(alert_data)
            subscribers = self.redis_client.publish('alerts', message)
            
            logger.info(f"Published {alert_data.get('alert_type', 'INFO')} alert to {subscribers} subscribers")
            return subscribers
            
        except Exception as e:
            logger.error(f"Failed to publish alert: {e}")
            return 0
    
    def publish_strategy_update(self, strategy_data: Dict[str, Any]) -> int:
        """
        Publish strategy performance updates
        
        Args:
            strategy_data: Dictionary containing strategy information
                Required fields:
                - strategy_name: Name of the strategy
                - performance: Performance metrics
                - timestamp: Update timestamp
        
        Returns:
            int: Number of subscribers who received the update
        """
        try:
            strategy_data['channel'] = 'strategy_updates'
            strategy_data['received_at'] = datetime.now().isoformat()
            
            message = json.dumps(strategy_data)
            subscribers = self.redis_client.publish('strategy_updates', message)
            
            logger.info(f"Published strategy update for {strategy_data['strategy_name']} to {subscribers} subscribers")
            return subscribers
            
        except Exception as e:
            logger.error(f"Failed to publish strategy update: {e}")
            return 0
    
    # =============================================================================
    # SUBSCRIBE METHODS
    # =============================================================================
    
    def subscribe_to_trade_signals(self, callback: Callable[[Dict], None], 
                                 symbol: Optional[str] = None) -> str:
        """
        Subscribe to trade signals
        
        Args:
            callback: Function to call when signal received
            symbol: Optional symbol filter (subscribe to specific trading pair)
        
        Returns:
            str: Subscription ID
        """
        channel = f"trade_signals:{symbol}" if symbol else "trade_signals"
        return self._subscribe(channel, callback, 'trade_signals')
    
    def subscribe_to_market_updates(self, callback: Callable[[Dict], None],
                                  symbol: Optional[str] = None) -> str:
        """
        Subscribe to market updates
        
        Args:
            callback: Function to call when update received
            symbol: Optional symbol filter
        
        Returns:
            str: Subscription ID
        """
        channel = f"market_updates:{symbol}" if symbol else "market_updates"
        return self._subscribe(channel, callback, 'market_updates')
    
    def subscribe_to_alerts(self, callback: Callable[[Dict], None]) -> str:
        """Subscribe to trading alerts"""
        return self._subscribe('alerts', callback, 'alerts')
    
    def subscribe_to_strategy_updates(self, callback: Callable[[Dict], None]) -> str:
        """Subscribe to strategy updates"""
        return self._subscribe('strategy_updates', callback, 'strategy_updates')
    
    def _subscribe(self, channel: str, callback: Callable[[Dict], None], 
                   subscription_type: str) -> str:
        """Internal subscription method"""
        try:
            subscription_id = f"{subscription_type}:{len(self.subscribers)}:{channel}"
            
            self.pubsub.subscribe(channel)
            self.subscribers[subscription_id] = {
                'callback': callback,
                'channel': channel,
                'type': subscription_type,
                'active': True
            }
            
            # Start listener thread if not running
            if not self.running:
                self._start_listener()
            
            logger.info(f"Subscribed to {channel} with ID: {subscription_id}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            raise
    
    def _start_listener(self):
        """Start the message listener thread"""
        self.running = True
        self.listener_thread = threading.Thread(target=self._message_listener, daemon=True)
        self.listener_thread.start()
        logger.info("Pub/Sub message listener started")
    
    def _message_listener(self):
        """Background message listener"""
        while self.running:
            try:
                message = self.pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    self._handle_message(message)
            except Exception as e:
                logger.error(f"Error in message listener: {e}")
                time.sleep(0.1)
    
    def _handle_message(self, message: Dict):
        """Handle received message"""
        try:
            channel = message['channel'].decode() if isinstance(message['channel'], bytes) else message['channel']
            data = json.loads(message['data'])
            
            # Find matching subscribers
            for sub_id, subscriber in self.subscribers.items():
                if subscriber['active'] and subscriber['channel'] == channel:
                    try:
                        subscriber['callback'](data)
                    except Exception as e:
                        logger.error(f"Error in subscriber callback {sub_id}: {e}")
                        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a channel"""
        try:
            if subscription_id in self.subscribers:
                del self.subscribers[subscription_id]
                
                # Unsubscribe from channel if no more subscribers
                channel = self.subscribers[subscription_id]['channel']
                active_subs = [s for s in self.subscribers.values() if s['channel'] == channel and s['active']]
                
                if not active_subs:
                    self.pubsub.unsubscribe(channel)
                
                logger.info(f"Unsubscribed from {subscription_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unsubscribe {subscription_id}: {e}")
            return False
    
    def unsubscribe_all(self):
        """Unsubscribe from all channels"""
        try:
            for subscription_id in list(self.subscribers.keys()):
                self.unsubscribe(subscription_id)
            
            self.pubsub.close()
            logger.info("Unsubscribed from all channels")
        except Exception as e:
            logger.error(f"Error unsubscribing from all: {e}")
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_subscription_count(self) -> int:
        """Get number of active subscriptions"""
        return len([s for s in self.subscribers.values() if s['active']])
    
    def get_channel_subscribers(self, channel: str) -> int:
        """Get number of subscribers for a specific channel"""
        return len([s for s in self.subscribers.values() if s['channel'] == channel and s['active']])
    
    def ping(self) -> bool:
        """Test connection"""
        try:
            return self.redis_client.ping()
        except Exception:
            return False
    
    def close(self):
        """Close Pub/Sub connection"""
        try:
            self.running = False
            if self.listener_thread and self.listener_thread.is_alive():
                self.listener_thread.join(timeout=5.0)
            
            self.unsubscribe_all()
            self.redis_client.close()
            logger.info("Pub/Sub connection closed")
        except Exception as e:
            logger.error(f"Error closing Pub/Sub connection: {e}")

# Example usage and signal handlers
def handle_trade_signal(signal_data):
    """Example trade signal handler"""
    print(f"Received trade signal: {signal_data['signal_type']} {signal_data['symbol']} at {signal_data['price']}")
    # Add your trading logic here

def handle_market_update(market_data):
    """Example market update handler"""
    print(f"Market update: {market_data['symbol']} = ${market_data['price']}")

def handle_alert(alert_data):
    """Example alert handler"""
    print(f"ALERT [{alert_data['alert_type']}]: {alert_data['message']}")

# Example usage
if __name__ == "__main__":
    # Initialize Pub/Sub client
    pubsub_client = TradingPubSub()
    
    # Subscribe to different channels
    sub1 = pubsub_client.subscribe_to_trade_signals(handle_trade_signal, 'BTCUSDT')
    sub2 = pubsub_client.subscribe_to_market_updates(handle_market_update)
    sub3 = pubsub_client.subscribe_to_alerts(handle_alert)
    
    # Publish test messages
    test_signal = {
        'signal_type': 'BUY',
        'symbol': 'BTCUSDT',
        'price': 45000,
        'timestamp': datetime.now().isoformat(),
        'confidence': 0.85,
        'strategy': 'momentum'
    }
    pubsub_client.publish_trade_signal(test_signal)
    
    test_market = {
        'symbol': 'ETHUSDT',
        'price': 3200,
        'volume': 1250000,
        'timestamp': datetime.now().isoformat()
    }
    pubsub_client.publish_market_update(test_market)
    
    test_alert = {
        'alert_type': 'WARNING',
        'message': 'High volatility detected',
        'timestamp': datetime.now().isoformat(),
        'symbol': 'BTCUSDT'
    }
    pubsub_client.publish_alert(test_alert)
    
    # Keep running for a bit to receive messages
    time.sleep(5)
    
    # Cleanup
    pubsub_client.unsubscribe_all()
    pubsub_client.close()
    
    print("Pub/Sub test completed successfully!")