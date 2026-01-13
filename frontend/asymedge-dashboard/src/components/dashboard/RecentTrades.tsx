import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { TrendingUp, TrendingDown, Clock } from 'lucide-react';
import { useAppStore } from '../../store';
import { Trade } from '../../types';

const mockTrades: Trade[] = [
  {
    id: '1',
    symbol: 'AAPL',
    side: 'buy',
    size: 100,
    entryPrice: 175.50,
    exitPrice: 177.25,
    pnl: 175,
    pnlPercent: 1.0,
    status: 'closed',
    timestamp: Date.now() - 300000,
    strategy: 'Momentum',
    tags: ['growth', 'tech']
  },
  {
    id: '2',
    symbol: 'TSLA',
    side: 'sell',
    size: 50,
    entryPrice: 245.80,
    exitPrice: 243.20,
    pnl: 130,
    pnlPercent: 1.06,
    status: 'closed',
    timestamp: Date.now() - 600000,
    strategy: 'Mean Reversion',
    tags: ['electric', 'auto']
  },
  {
    id: '3',
    symbol: 'GOOGL',
    side: 'buy',
    size: 75,
    entryPrice: 142.30,
    exitPrice: 141.80,
    pnl: -37.50,
    pnlPercent: -0.35,
    status: 'closed',
    timestamp: Date.now() - 900000,
    strategy: 'Breakout',
    tags: ['search', 'ai']
  },
  {
    id: '4',
    symbol: 'MSFT',
    side: 'buy',
    size: 80,
    entryPrice: 380.25,
    exitPrice: 382.10,
    pnl: 148,
    pnlPercent: 0.49,
    status: 'closed',
    timestamp: Date.now() - 1200000,
    strategy: 'Swing Trading',
    tags: ['cloud', 'enterprise']
  },
  {
    id: '5',
    symbol: 'NVDA',
    side: 'sell',
    size: 25,
    entryPrice: 485.90,
    status: 'open',
    timestamp: Date.now() - 1800000,
    strategy: 'Scalping',
    tags: ['ai', 'chips']
  }
];

export const RecentTrades: React.FC = () => {
  const { tradingMetrics } = useAppStore();

  const formatTime = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    
    return new Date(timestamp).toLocaleDateString();
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Clock className="h-5 w-5" />
          <span>Recent Trades</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {mockTrades.map((trade) => (
            <div
              key={trade.id}
              className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg"
            >
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  {trade.side === 'buy' ? (
                    <TrendingUp className="h-4 w-4 text-green-600" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-600" />
                  )}
                  <span className="font-medium">{trade.symbol}</span>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Badge variant={trade.side === 'buy' ? 'default' : 'destructive'}>
                    {trade.side.toUpperCase()}
                  </Badge>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {trade.size} shares
                  </span>
                </div>

                <div className="text-sm text-gray-600 dark:text-gray-400">
                  @ {formatCurrency(trade.entryPrice)}
                </div>
              </div>

              <div className="flex items-center space-x-4">
                {trade.pnl !== undefined && trade.pnlPercent !== undefined && (
                  <div className="text-right">
                    <div className={`font-medium ${
                      trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl)}
                    </div>
                    <div className={`text-sm ${
                      trade.pnlPercent >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {trade.pnlPercent >= 0 ? '+' : ''}{trade.pnlPercent.toFixed(2)}%
                    </div>
                  </div>
                )}

                <div className="flex items-center space-x-2">
                  <Badge variant={trade.status === 'closed' ? 'secondary' : 'outline'}>
                    {trade.status}
                  </Badge>
                  <span className="text-xs text-gray-500">
                    {formatTime(trade.timestamp)}
                  </span>
                </div>
              </div>
            </div>
          ))}

          <div className="text-center pt-4">
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              View all trades →
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};