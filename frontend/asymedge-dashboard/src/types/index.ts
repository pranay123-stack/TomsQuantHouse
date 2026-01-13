export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'trader' | 'analyst' | 'viewer';
  avatar?: string;
  permissions: string[];
}

export interface TradingMetrics {
  portfolioValue: number;
  dailyPnL: number;
  dailyPnLPercent: number;
  totalPnL: number;
  totalPnLPercent: number;
  winRate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgWin: number;
  avgLoss: number;
  sharpeRatio: number;
  maxDrawdown: number;
}

export interface Trade {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  size: number;
  entryPrice: number;
  exitPrice?: number;
  pnl?: number;
  pnlPercent?: number;
  status: 'open' | 'closed' | 'cancelled';
  timestamp: number;
  strategy: string;
  tags: string[];
}

export interface Agent {
  id: string;
  name: string;
  type: 'letta' | 'custom';
  status: 'active' | 'inactive' | 'training' | 'error';
  description: string;
  lastActive: number;
  metrics: {
    successRate: number;
    totalTasks: number;
    avgExecutionTime: number;
  };
  config: Record<string, any>;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: 'running' | 'paused' | 'completed' | 'failed';
  progress: number;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  created: number;
  updated: number;
}

export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: {
    label: string;
    status: 'pending' | 'running' | 'completed' | 'error';
    config?: Record<string, any>;
  };
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type: string;
}

export interface DashboardWidget {
  id: string;
  type: string;
  position: { x: number; y: number };
  size: { width: number; height: number };
  config: Record<string, any>;
}

export interface MarketData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  bid: number;
  ask: number;
  timestamp: number;
}

export interface Alert {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: number;
  read: boolean;
}

export interface Theme {
  mode: 'light' | 'dark';
  primaryColor: string;
  secondaryColor: string;
  backgroundColor: string;
  textColor: string;
}

export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: number;
}