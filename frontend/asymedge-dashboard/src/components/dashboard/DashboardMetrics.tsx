import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';

// Mock data for portfolio performance
const portfolioData = [
  { time: '09:30', value: 2445000 },
  { time: '10:00', value: 2448000 },
  { time: '10:30', value: 2451000 },
  { time: '11:00', value: 2447000 },
  { time: '11:30', value: 2452000 },
  { time: '12:00', value: 2454000 },
  { time: '12:30', value: 2453000 },
  { time: '13:00', value: 2456000 },
  { time: '13:30', value: 2454000 },
  { time: '14:00', value: 2458000 },
  { time: '14:30', value: 2459000 },
  { time: '15:00', value: 2456789 },
];

const pnlData = [
  { time: '09:30', pnl: 0 },
  { time: '10:00', pnl: 3000 },
  { time: '10:30', pnl: 6000 },
  { time: '11:00', pnl: 2000 },
  { time: '11:30', pnl: 7000 },
  { time: '12:00', pnl: 9000 },
  { time: '12:30', pnl: 8000 },
  { time: '13:00', pnl: 11000 },
  { time: '13:30', pnl: 9000 },
  { time: '14:00', pnl: 13000 },
  { time: '14:30', pnl: 14000 },
  { time: '15:00', pnl: 12345 },
];

export const DashboardMetrics: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Portfolio Value Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Portfolio Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            {/* @ts-ignore */}
            <AreaChart data={portfolioData}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="#6b7280"
                fontSize={12}
              />
              <YAxis 
                stroke="#6b7280"
                fontSize={12}
                tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
              />
              <Tooltip 
                formatter={(value: number) => [`$${value.toLocaleString()}`, 'Portfolio Value']}
                labelStyle={{ color: '#1f2937' }}
                contentStyle={{ 
                  backgroundColor: '#f9fafb', 
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px'
                }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#3b82f6"
                fillOpacity={1}
                fill="url(#colorValue)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Daily P&L Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Daily P&L</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            {/* @ts-ignore */}
            <LineChart data={pnlData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="#6b7280"
                fontSize={12}
              />
              <YAxis 
                stroke="#6b7280"
                fontSize={12}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              />
              <Tooltip 
                formatter={(value: number) => [`$${value.toLocaleString()}`, 'Daily P&L']}
                labelStyle={{ color: '#1f2937' }}
                contentStyle={{ 
                  backgroundColor: '#f9fafb', 
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px'
                }}
              />
              <Line
                type="monotone"
                dataKey="pnl"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
                activeDot={{ r: 6, fill: '#10b981' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
};