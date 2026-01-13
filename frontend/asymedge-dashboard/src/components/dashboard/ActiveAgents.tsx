import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Brain, Activity, Clock, CheckCircle, XCircle, Loader } from 'lucide-react';
import { useAppStore } from '../../store';
import { Agent } from '../../types';

const mockAgents: Agent[] = [
  {
    id: '1',
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
    id: '2',
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
    id: '3',
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
  },
  {
    id: '4',
    name: 'MarketWatcher',
    type: 'letta',
    status: 'error',
    description: 'Real-time market data monitoring',
    lastActive: Date.now() - 7200000,
    metrics: {
      successRate: 45.3,
      totalTasks: 1234,
      avgExecutionTime: 0.1
    },
    config: {
      symbols: ['AAPL', 'GOOGL', 'TSLA', 'MSFT'],
      updateInterval: 1000
    }
  }
];

const getStatusIcon = (status: Agent['status']) => {
  switch (status) {
    case 'active':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'training':
      return <Loader className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'error':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'inactive':
      return <Clock className="h-4 w-4 text-gray-500" />;
    default:
      return <Activity className="h-4 w-4 text-gray-500" />;
  }
};

const getStatusColor = (status: Agent['status']) => {
  switch (status) {
    case 'active':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
    case 'training':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
    case 'error':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
    case 'inactive':
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
  }
};

export const ActiveAgents: React.FC = () => {
  const { agents, setAgents } = useAppStore();

  React.useEffect(() => {
    setAgents(mockAgents);
  }, [setAgents]);

  const formatLastActive = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / 60000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    
    return new Date(timestamp).toLocaleDateString();
  };

  const activeAgents = agents.filter(agent => agent.status === 'active').length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Brain className="h-5 w-5" />
          <span>Active Agents</span>
          <Badge variant="secondary">{activeAgents}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {agents.slice(0, 4).map((agent) => (
            <div
              key={agent.id}
              className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
            >
              <div className="flex items-center space-x-3">
                {getStatusIcon(agent.status)}
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h4 className="font-medium text-sm">{agent.name}</h4>
                    <Badge 
                      variant="outline" 
                      className={`text-xs ${getStatusColor(agent.status)}`}
                    >
                      {agent.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    {agent.description}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <div className="text-sm font-medium">
                  {agent.metrics.successRate.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500">
                  {formatLastActive(agent.lastActive)}
                </div>
              </div>
            </div>
          ))}

          <div className="text-center pt-4">
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              Manage all agents →
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};