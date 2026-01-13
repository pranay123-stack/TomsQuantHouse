import { io, Socket } from 'socket.io-client';
import { useAppStore } from '../store';

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(url: string = 'ws://localhost:3001') {
    if (this.socket?.connected) {
      return;
    }

    this.socket = io(url, {
      transports: ['websocket'],
      autoConnect: true,
      reconnection: true,
      reconnectionDelay: this.reconnectDelay,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.setupEventListeners();
  }

  private setupEventListeners() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log('WebSocket reconnected after', attemptNumber, 'attempts');
    });

    this.socket.on('reconnect_error', (error) => {
      console.error('WebSocket reconnection error:', error);
      this.reconnectAttempts++;
    });

    // Trading data events
    this.socket.on('trading_update', (data) => {
      const { setTradingMetrics, updateMarketData } = useAppStore.getState();
      
      if (data.type === 'metrics') {
        setTradingMetrics(data.payload);
      } else if (data.type === 'market_data') {
        updateMarketData(data.payload.symbol, data.payload);
      }
    });

    // Agent events
    this.socket.on('agent_update', (data) => {
      const { updateAgent } = useAppStore.getState();
      updateAgent(data.agentId, data.updates);
    });

    // Workflow events
    this.socket.on('workflow_update', (data) => {
      const { updateWorkflow } = useAppStore.getState();
      updateWorkflow(data.workflowId, data.updates);
    });

    // Alert events
    this.socket.on('alert', (alert) => {
      const { addAlert } = useAppStore.getState();
      addAlert(alert);
    });

    // Market data events
    this.socket.on('market_data', (data) => {
      const { updateMarketData } = useAppStore.getState();
      updateMarketData(data.symbol, data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  emit(event: string, data: any) {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    }
  }

  subscribe(channel: string, callback: (data: any) => void) {
    if (this.socket) {
      this.socket.on(channel, callback);
    }
  }

  unsubscribe(channel: string) {
    if (this.socket) {
      this.socket.off(channel);
    }
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

// Create singleton instance
export const wsService = new WebSocketService();

// React hook for WebSocket management
export const useWebSocket = () => {
  const connect = (url?: string) => wsService.connect(url);
  const disconnect = () => wsService.disconnect();
  const emit = (event: string, data: any) => wsService.emit(event, data);
  const subscribe = (channel: string, callback: (data: any) => void) => 
    wsService.subscribe(channel, callback);
  const unsubscribe = (channel: string) => wsService.unsubscribe(channel);
  const isConnected = wsService.isConnected();

  return {
    connect,
    disconnect,
    emit,
    subscribe,
    unsubscribe,
    isConnected,
  };
};