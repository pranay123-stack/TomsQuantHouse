import { useAppStore } from '../store';
import { Agent, Workflow, Trade, MarketData, Alert } from '../types';

// Mock data initialization
export const initializeMockData = () => {
  const { 
    setAgents, 
    setWorkflows, 
    setTradingMetrics,
    setMarketData,
    setAlerts,
    addAlert
  } = useAppStore.getState();

  // Initialize Agents
  const mockAgents: Agent[] = [
    {
      id: 'agent-1',
      name: 'TradingAgent-01',
      type: 'letta',
      status: 'active',
      description: 'Momentum-based equity trading agent',
      lastActive: Date.now() - 30000,
      metrics: {
        successRate: 87.5,
        totalTasks: 234,
        avgExecutionTime: 1.2
      },
      config: {
        maxPositionSize: 10000,
        riskThreshold: 0.02
      }
    },
    {
      id: 'agent-2',
      name: 'SentimentAnalyzer',
      type: 'letta',
      status: 'active',
      description: 'Social media sentiment analysis for trading signals',
      lastActive: Date.now() - 120000,
      metrics: {
        successRate: 73.2,
        totalTasks: 567,
        avgExecutionTime: 2.8
      },
      config: {
        sources: ['twitter', 'reddit', 'news'],
        sentimentThreshold: 0.7
      }
    },
    {
      id: 'agent-3',
      name: 'RiskManager',
      type: 'custom',
      status: 'training',
      description: 'Portfolio risk assessment and management',
      lastActive: Date.now() - 3600000,
      metrics: {
        successRate: 92.1,
        totalTasks: 89,
        avgExecutionTime: 0.8
      },
      config: {
        maxDrawdown: 0.05,
        correlationThreshold: 0.8
      }
    }
  ];

  setAgents(mockAgents);

  // Initialize Workflows
  const mockWorkflows: Workflow[] = [
    {
      id: 'workflow-1',
      name: 'Daily Market Analysis',
      description: 'Comprehensive market analysis and signal generation',
      status: 'running',
      progress: 75,
      nodes: [],
      edges: [],
      created: Date.now() - 3600000,
      updated: Date.now() - 300000
    },
    {
      id: 'workflow-2',
      name: 'Risk Assessment',
      description: 'Portfolio risk monitoring and alerts',
      status: 'completed',
      progress: 100,
      nodes: [],
      edges: [],
      created: Date.now() - 7200000,
      updated: Date.now() - 600000
    },
    {
      id: 'workflow-3',
      name: 'News Sentiment Analysis',
      description: 'Real-time news sentiment tracking',
      status: 'paused',
      progress: 45,
      nodes: [],
      edges: [],
      created: Date.now() - 10800000,
      updated: Date.now() - 1800000
    }
  ];

  setWorkflows(mockWorkflows);

  // Initialize Trading Metrics
  const mockTradingMetrics = {
    portfolioValue: 2456789.32,
    dailyPnL: 12345.67,
    dailyPnLPercent: 0.51,
    totalPnL: 245678.90,
    totalPnLPercent: 11.11,
    winRate: 68.5,
    totalTrades: 1234,
    winningTrades: 845,
    losingTrades: 389,
    avgWin: 1234.56,
    avgLoss: -456.78,
    sharpeRatio: 1.85,
    maxDrawdown: -5.2
  };

  setTradingMetrics(mockTradingMetrics);

  // Initialize Market Data
  const mockMarketData = new Map<string, MarketData>();
  const marketSymbols = [
    { symbol: 'S&P 500', price: 4567.89, change: 23.45, changePercent: 0.52 },
    { symbol: 'NASDAQ', price: 14234.67, change: -45.23, changePercent: -0.32 },
    { symbol: 'DOW', price: 35432.10, change: 156.78, changePercent: 0.44 },
    { symbol: 'BTC-USD', price: 43250.75, change: 1234.50, changePercent: 2.94 },
    { symbol: 'AAPL', price: 175.50, change: 2.30, changePercent: 1.33 },
    { symbol: 'GOOGL', price: 142.30, change: -1.20, changePercent: -0.84 },
    { symbol: 'TSLA', price: 245.80, change: 8.45, changePercent: 3.57 },
    { symbol: 'MSFT', price: 380.25, change: 4.20, changePercent: 1.12 }
  ];

  marketSymbols.forEach(item => {
    const data: MarketData = {
      symbol: item.symbol,
      price: item.price,
      change: item.change,
      changePercent: item.changePercent,
      volume: Math.floor(Math.random() * 1000000000) + 100000000,
      bid: item.price - 0.05,
      ask: item.price + 0.05,
      timestamp: Date.now()
    };
    mockMarketData.set(item.symbol, data);
  });

  setMarketData(mockMarketData);

  // Initialize Alerts
  const mockAlerts: Alert[] = [
    {
      id: 'alert-1',
      type: 'success',
      title: 'Trade Executed',
      message: 'AAPL buy order for 100 shares executed at $175.50',
      timestamp: Date.now() - 300000,
      read: false
    },
    {
      id: 'alert-2',
      type: 'info',
      title: 'Workflow Completed',
      message: 'Daily Market Analysis workflow completed successfully',
      timestamp: Date.now() - 600000,
      read: false
    },
    {
      id: 'alert-3',
      type: 'warning',
      title: 'Risk Threshold Exceeded',
      message: 'Portfolio drawdown reached 4.5%, monitoring closely',
      timestamp: Date.now() - 900000,
      read: true
    },
    {
      id: 'alert-4',
      type: 'error',
      title: 'Agent Error',
      message: 'RiskManager agent encountered an error during execution',
      timestamp: Date.now() - 1200000,
      read: true
    }
  ];

  setAlerts(mockAlerts);
};

// Real-time data simulation
export const startRealTimeSimulation = () => {
  const { updateMarketData, updateTradingMetrics } = useAppStore.getState();
  
  const updateMarketPrices = () => {
    const symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA'];
    
    symbols.forEach(symbol => {
      const change = (Math.random() - 0.5) * 2; // -1 to +1
      const percentChange = change / 100;
      
      // Simulate price movement
      const basePrice = symbol === 'AAPL' ? 175.50 :
                      symbol === 'GOOGL' ? 142.30 :
                      symbol === 'TSLA' ? 245.80 :
                      symbol === 'MSFT' ? 380.25 : 485.90;
      
      const newPrice = basePrice + (basePrice * percentChange * 0.01);
      
      const marketData: MarketData = {
        symbol,
        price: newPrice,
        change: newPrice - basePrice,
        changePercent: ((newPrice - basePrice) / basePrice) * 100,
        volume: Math.floor(Math.random() * 10000000) + 1000000,
        bid: newPrice - 0.05,
        ask: newPrice + 0.05,
        timestamp: Date.now()
      };
      
      updateMarketData(symbol, marketData);
    });
  };

  const updatePortfolioMetrics = () => {
    const change = (Math.random() - 0.5) * 10000; // -5000 to +5000
    const currentMetrics = useAppStore.getState().tradingMetrics;
    
    if (currentMetrics) {
      const newDailyPnL = currentMetrics.dailyPnL + change;
      const newPortfolioValue = currentMetrics.portfolioValue + change;
      
      updateTradingMetrics({
        ...currentMetrics,
        dailyPnL: newDailyPnL,
        dailyPnLPercent: (newDailyPnL / newPortfolioValue) * 100,
        portfolioValue: newPortfolioValue
      });
    }
  };

  // Update market prices every 5 seconds
  const marketInterval = setInterval(updateMarketPrices, 5000);
  
  // Update portfolio metrics every 10 seconds
  const portfolioInterval = setInterval(updatePortfolioMetrics, 10000);

  // Return cleanup function
  return () => {
    clearInterval(marketInterval);
    clearInterval(portfolioInterval);
  };
};

// Application configuration
export const config = {
  app: {
    name: 'ASYMEdge Dashboard',
    version: '1.0.0',
    description: 'AI-Powered Trading Dashboard with Real-time Monitoring'
  },
  websocket: {
    url: process.env.VITE_WS_URL || 'ws://localhost:3001',
    reconnectInterval: 5000,
    maxReconnectAttempts: 10
  },
  api: {
    baseUrl: process.env.VITE_API_URL || 'http://localhost:3000',
    timeout: 30000
  },
  features: {
    enableWebSocket: true,
    enableRealTimeUpdates: true,
    enableNotifications: true,
    enableDarkMode: true,
    enableAnalytics: true
  },
  trading: {
    defaultOrderSize: 100,
    maxOrderSize: 10000,
    supportedOrderTypes: ['market', 'limit', 'stop', 'stop_limit'],
    supportedTimeInForce: ['day', 'gtc', 'ioc', 'fok']
  },
  agents: {
    maxAgents: 20,
    supportedTypes: ['letta', 'custom'],
    defaultSuccessRate: 75.0
  },
  workflows: {
    maxWorkflows: 50,
    maxNodesPerWorkflow: 20,
    autoSaveInterval: 30000
  }
};