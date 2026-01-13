import React from 'react';
import { useAppStore } from '../../store';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { TrendingUp, TrendingDown, DollarSign, Activity, Users, GitBranch } from 'lucide-react';
import { DashboardMetrics } from './DashboardMetrics';
import { RecentTrades } from './RecentTrades';
import { ActiveAgents } from './ActiveAgents';
import { WorkflowStatus } from './WorkflowStatus';
import { MarketOverview } from './MarketOverview';

export const DashboardHome: React.FC = () => {
  const { tradingMetrics, agents, workflows } = useAppStore();

  // Mock data for demonstration
  const mockTradingMetrics = tradingMetrics || {
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

  const stats = [
    {
      title: 'Portfolio Value',
      value: `$${mockTradingMetrics.portfolioValue.toLocaleString()}`,
      change: `+${mockTradingMetrics.dailyPnLPercent.toFixed(2)}%`,
      trend: mockTradingMetrics.dailyPnL >= 0 ? 'up' : 'down',
      icon: DollarSign,
      color: mockTradingMetrics.dailyPnL >= 0 ? 'text-green-600' : 'text-red-600'
    },
    {
      title: 'Daily P&L',
      value: `$${mockTradingMetrics.dailyPnL.toLocaleString()}`,
      change: `${mockTradingMetrics.dailyPnLPercent.toFixed(2)}%`,
      trend: mockTradingMetrics.dailyPnL >= 0 ? 'up' : 'down',
      icon: TrendingUp,
      color: mockTradingMetrics.dailyPnL >= 0 ? 'text-green-600' : 'text-red-600'
    },
    {
      title: 'Active Agents',
      value: agents.length.toString(),
      change: '+2 this week',
      trend: 'up',
      icon: Users,
      color: 'text-blue-600'
    },
    {
      title: 'Running Workflows',
      value: workflows.filter(w => w.status === 'running').length.toString(),
      change: '3 completed today',
      trend: 'up',
      icon: GitBranch,
      color: 'text-purple-600'
    },
    {
      title: 'Win Rate',
      value: `${mockTradingMetrics.winRate.toFixed(1)}%`,
      change: '+2.3% this month',
      trend: 'up',
      icon: Activity,
      color: 'text-green-600'
    },
    {
      title: 'Total Trades',
      value: mockTradingMetrics.totalTrades.toLocaleString(),
      change: '+127 today',
      trend: 'up',
      icon: TrendingUp,
      color: 'text-indigo-600'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Dashboard Overview
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Real-time trading performance and system monitoring
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {stats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-gray-600 dark:text-gray-400">
                {stat.title}
              </CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {stat.value}
              </div>
              <div className="flex items-center mt-1">
                {stat.trend === 'up' ? (
                  <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-500 mr-1" />
                )}
                <span className={`text-sm ${
                  stat.trend === 'up' ? 'text-green-600' : 'text-red-600'
                }`}>
                  {stat.change}
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Takes up 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          <DashboardMetrics />
          <RecentTrades />
        </div>

        {/* Right Column - Takes up 1 column */}
        <div className="space-y-6">
          <ActiveAgents />
          <WorkflowStatus />
          <MarketOverview />
        </div>
      </div>
    </div>
  );
};