import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { 
  TrendingUp, 
  TrendingDown, 
  Play, 
  Pause, 
  Square,
  Plus,
  BarChart3,
  AlertTriangle,
  DollarSign
} from 'lucide-react';
import { useAppStore } from '../../store';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Mock real-time trading data
const realTimeData = [
  { time: '09:30', price: 175.25, volume: 1200000 },
  { time: '09:45', price: 175.80, volume: 1400000 },
  { time: '10:00', price: 176.10, volume: 1100000 },
  { time: '10:15', price: 175.90, volume: 1300000 },
  { time: '10:30', price: 176.50, volume: 1600000 },
  { time: '10:45', price: 176.25, volume: 1250000 },
  { time: '11:00', price: 176.80, volume: 1800000 },
];

const orderBookData = [
  { price: 176.80, size: 500, type: 'ask' },
  { price: 176.75, size: 300, type: 'ask' },
  { price: 176.70, size: 800, type: 'ask' },
  { price: 176.65, size: 600, type: 'ask' },
  { price: 176.60, size: 1200, type: 'ask' },
  { price: 176.55, size: 400, type: 'ask' },
  { price: '---', size: '', type: 'separator' },
  { price: 176.50, size: 700, type: 'bid' },
  { price: 176.45, size: 900, type: 'bid' },
  { price: 176.40, size: 550, type: 'bid' },
  { price: 176.35, size: 1100, type: 'bid' },
  { price: 176.30, size: 300, type: 'bid' },
  { price: 176.25, size: 800, type: 'bid' },
];

export const TradingDashboard: React.FC = () => {
  const { tradingMetrics, setTradingMetrics } = useAppStore();
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('limit');
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [quantity, setQuantity] = useState(100);
  const [price, setPrice] = useState(176.50);

  React.useEffect(() => {
    if (tradingMetrics) return;
    
    const mockMetrics = {
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
    setTradingMetrics(mockMetrics);
  }, [tradingMetrics, setTradingMetrics]);

  const handlePlaceOrder = () => {
    // Simulate order placement
    console.log('Placing order:', {
      symbol: selectedSymbol,
      side: orderSide,
      type: orderType,
      quantity,
      price: orderType === 'limit' ? price : undefined
    });
  };

  const symbols = ['AAPL', 'GOOGL', 'TSLA', 'MSFT', 'NVDA', 'AMZN'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Trading Dashboard
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Real-time trading interface with advanced order management
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <DollarSign className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Portfolio</p>
                <p className="text-xl font-bold">$2.46M</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Daily P&L</p>
                <p className="text-xl font-bold text-green-600">+$12.3K</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Win Rate</p>
                <p className="text-xl font-bold">68.5%</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Risk Level</p>
                <p className="text-xl font-bold">Low</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart */}
        <div className="lg:col-span-2 space-y-6">
          {/* Symbol Selection */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{selectedSymbol} Live Price</span>
                <div className="flex items-center space-x-2">
                  <Badge variant="outline">Real-time</Badge>
                  <Badge variant="default" className="bg-green-100 text-green-800">
                    Live
                  </Badge>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2 mb-4">
                {symbols.map(symbol => (
                  <Button
                    key={symbol}
                    variant={selectedSymbol === symbol ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedSymbol(symbol)}
                  >
                    {symbol}
                  </Button>
                ))}
              </div>
              
              <ResponsiveContainer width="100%" height={300}>
                {/* @ts-ignore */}
                <AreaChart data={realTimeData}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                  <XAxis dataKey="time" stroke="#6b7280" fontSize={12} />
                  <YAxis stroke="#6b7280" fontSize={12} />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="price"
                    stroke="#3b82f6"
                    fillOpacity={1}
                    fill="url(#colorPrice)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Order Book */}
          <Card>
            <CardHeader>
              <CardTitle>Order Book</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {orderBookData.map((level, index) => (
                  <div
                    key={index}
                    className={`flex justify-between items-center p-1 text-sm ${
                      level.type === 'separator' 
                        ? 'border-t border-gray-300 dark:border-gray-600 pt-2' 
                        : level.type === 'ask'
                        ? 'hover:bg-red-50 dark:hover:bg-red-900/20'
                        : 'hover:bg-green-50 dark:hover:bg-green-900/20'
                    }`}
                  >
                    <span className={level.type === 'ask' ? 'text-red-600' : 'text-green-600'}>
                      {level.price}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">
                      {level.size}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Order Panel */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Place Order</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Order Type */}
              <div className="flex space-x-2">
                <Button
                  variant={orderSide === 'buy' ? "default" : "outline"}
                  size="sm"
                  onClick={() => setOrderSide('buy')}
                  className="flex-1"
                >
                  Buy
                </Button>
                <Button
                  variant={orderSide === 'sell' ? "destructive" : "outline"}
                  size="sm"
                  onClick={() => setOrderSide('sell')}
                  className="flex-1"
                >
                  Sell
                </Button>
              </div>

              {/* Symbol */}
              <div>
                <label className="text-sm font-medium">Symbol</label>
                <select
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value)}
                  className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-background"
                >
                  {symbols.map(symbol => (
                    <option key={symbol} value={symbol}>{symbol}</option>
                  ))}
                </select>
              </div>

              {/* Order Type */}
              <div>
                <label className="text-sm font-medium">Order Type</label>
                <div className="flex space-x-2 mt-1">
                  <Button
                    variant={orderType === 'market' ? "default" : "outline"}
                    size="sm"
                    onClick={() => setOrderType('market')}
                    className="flex-1"
                  >
                    Market
                  </Button>
                  <Button
                    variant={orderType === 'limit' ? "default" : "outline"}
                    size="sm"
                    onClick={() => setOrderType('limit')}
                    className="flex-1"
                  >
                    Limit
                  </Button>
                </div>
              </div>

              {/* Quantity */}
              <div>
                <label className="text-sm font-medium">Quantity</label>
                <Input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(Number(e.target.value))}
                  className="mt-1"
                />
              </div>

              {/* Price */}
              {orderType === 'limit' && (
                <div>
                  <label className="text-sm font-medium">Price</label>
                  <Input
                    type="number"
                    step="0.01"
                    value={price}
                    onChange={(e) => setPrice(Number(e.target.value))}
                    className="mt-1"
                  />
                </div>
              )}

              {/* Order Button */}
              <Button
                onClick={handlePlaceOrder}
                className={`w-full ${
                  orderSide === 'buy' 
                    ? 'bg-green-600 hover:bg-green-700' 
                    : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                {orderSide === 'buy' ? 'Buy' : 'Sell'} {selectedSymbol}
              </Button>
            </CardContent>
          </Card>

          {/* Active Positions */}
          <Card>
            <CardHeader>
              <CardTitle>Active Positions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-2 bg-green-50 dark:bg-green-900/20 rounded">
                  <div>
                    <span className="font-medium">AAPL</span>
                    <Badge variant="outline" className="ml-2">Long</Badge>
                  </div>
                  <div className="text-right">
                    <div className="font-medium">+$234.50</div>
                    <div className="text-sm text-green-600">+1.3%</div>
                  </div>
                </div>
                
                <div className="flex justify-between items-center p-2 bg-red-50 dark:bg-red-900/20 rounded">
                  <div>
                    <span className="font-medium">TSLA</span>
                    <Badge variant="outline" className="ml-2">Short</Badge>
                  </div>
                  <div className="text-right">
                    <div className="font-medium">-$156.25</div>
                    <div className="text-sm text-red-600">-2.1%</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};