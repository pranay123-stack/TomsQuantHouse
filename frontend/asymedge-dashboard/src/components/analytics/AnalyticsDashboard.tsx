import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
  BarChart3, 
  TrendingUp, 
  PieChart, 
  Activity,
  Calendar,
  Download,
  Filter
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  ComposedChart,
  Area
} from 'recharts';

// Mock analytics data
const portfolioAllocation = [
  { name: 'Technology', value: 35, color: '#3b82f6' },
  { name: 'Healthcare', value: 20, color: '#10b981' },
  { name: 'Finance', value: 18, color: '#f59e0b' },
  { name: 'Energy', value: 12, color: '#ef4444' },
  { name: 'Consumer', value: 15, color: '#8b5cf6' }
];

const performanceByStrategy = [
  { strategy: 'Momentum', return: 15.2, risk: 8.5, trades: 145 },
  { strategy: 'Mean Reversion', return: 12.8, risk: 6.2, trades: 89 },
  { strategy: 'Breakout', return: 18.5, risk: 12.1, trades: 67 },
  { strategy: 'Swing Trading', return: 10.3, risk: 7.8, trades: 234 },
  { strategy: 'Scalping', return: 22.1, risk: 15.3, trades: 567 }
];

const monthlyReturns = [
  { month: 'Jan', returns: 2.1, benchmark: 1.8 },
  { month: 'Feb', returns: -0.5, benchmark: -0.3 },
  { month: 'Mar', returns: 3.2, benchmark: 2.9 },
  { month: 'Apr', returns: 1.8, benchmark: 1.5 },
  { month: 'May', returns: 4.1, benchmark: 3.7 },
  { month: 'Jun', returns: 2.7, benchmark: 2.4 },
  { month: 'Jul', returns: -1.2, benchmark: -0.8 },
  { month: 'Aug', returns: 3.5, benchmark: 3.1 },
  { month: 'Sep', returns: 1.9, benchmark: 1.6 },
  { month: 'Oct', returns: 2.8, benchmark: 2.5 },
  { month: 'Nov', returns: 4.2, benchmark: 3.9 },
  { month: 'Dec', returns: 3.1, benchmark: 2.8 }
];

const riskMetrics = {
  sharpeRatio: 1.85,
  sortinoRatio: 2.34,
  maxDrawdown: -5.2,
  volatility: 12.8,
  beta: 0.92,
  alpha: 2.1
};

export const AnalyticsDashboard: React.FC = () => {
  const [timeRange, setTimeRange] = useState('1Y');
  const [selectedMetric, setSelectedMetric] = useState('returns');

  const timeRanges = ['1D', '1W', '1M', '3M', '6M', '1Y', 'YTD', 'ALL'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Analytics & Performance
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Comprehensive trading analytics and performance metrics
          </p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline">
            <Filter className="h-4 w-4 mr-2" />
            Filter
          </Button>
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Time Range Selector */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Calendar className="h-4 w-4 text-gray-600" />
              <span className="text-sm font-medium">Time Range:</span>
            </div>
            <div className="flex space-x-1">
              {timeRanges.map((range) => (
                <Button
                  key={range}
                  variant={timeRange === range ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setTimeRange(range)}
                >
                  {range}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Return</p>
                <p className="text-2xl font-bold text-green-600">+24.8%</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Sharpe Ratio</p>
                <p className="text-2xl font-bold">{riskMetrics.sharpeRatio}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-red-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown</p>
                <p className="text-2xl font-bold text-red-600">{riskMetrics.maxDrawdown}%</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <PieChart className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Win Rate</p>
                <p className="text-2xl font-bold">68.5%</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Monthly Returns Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Monthly Returns vs Benchmark</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              {/* @ts-ignore */}
              <ComposedChart data={monthlyReturns}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis dataKey="month" stroke="#6b7280" fontSize={12} />
                <YAxis stroke="#6b7280" fontSize={12} />
                <Tooltip />
                <Bar dataKey="returns" fill="#3b82f6" name="Portfolio" />
                <Line type="monotone" dataKey="benchmark" stroke="#10b981" strokeWidth={2} name="Benchmark" />
              </ComposedChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Portfolio Allocation */}
        <Card>
          <CardHeader>
            <CardTitle>Portfolio Allocation</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <RechartsPieChart>
                <Pie
                  data={portfolioAllocation}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  dataKey="value"
                >
                  {portfolioAllocation.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </RechartsPieChart>
            </ResponsiveContainer>
            <div className="grid grid-cols-2 gap-2 mt-4">
              {portfolioAllocation.map((item, index) => (
                <div key={index} className="flex items-center space-x-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {item.name} ({item.value}%)
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Strategy Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Strategy Performance Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-3 px-4">Strategy</th>
                  <th className="text-right py-3 px-4">Total Return</th>
                  <th className="text-right py-3 px-4">Risk Score</th>
                  <th className="text-right py-3 px-4">Total Trades</th>
                  <th className="text-right py-3 px-4">Performance</th>
                </tr>
              </thead>
              <tbody>
                {performanceByStrategy.map((strategy, index) => (
                  <tr key={index} className="border-b border-gray-100 dark:border-gray-800">
                    <td className="py-3 px-4 font-medium">{strategy.strategy}</td>
                    <td className="py-3 px-4 text-right">
                      <span className="text-green-600 font-medium">+{strategy.return}%</span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Badge variant="outline">
                        {strategy.risk <= 8 ? 'Low' : strategy.risk <= 12 ? 'Medium' : 'High'}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-right">{strategy.trades}</td>
                    <td className="py-3 px-4 text-right">
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{ width: `${(strategy.return / 25) * 100}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Risk Metrics Detail */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Risk Metrics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Sharpe Ratio</span>
              <span className="font-medium">{riskMetrics.sharpeRatio}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Sortino Ratio</span>
              <span className="font-medium">{riskMetrics.sortinoRatio}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Max Drawdown</span>
              <span className="font-medium text-red-600">{riskMetrics.maxDrawdown}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Volatility</span>
              <span className="font-medium">{riskMetrics.volatility}%</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Market Beta</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Beta</span>
              <span className="font-medium">{riskMetrics.beta}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Alpha</span>
              <span className="font-medium text-green-600">+{riskMetrics.alpha}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Correlation</span>
              <span className="font-medium">0.87</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Tracking Error</span>
              <span className="font-medium">2.3%</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Trading Stats</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Total Trades</span>
              <span className="font-medium">1,234</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Win Rate</span>
              <span className="font-medium text-green-600">68.5%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Avg Win</span>
              <span className="font-medium text-green-600">+$1,234</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Avg Loss</span>
              <span className="font-medium text-red-600">-$456</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};