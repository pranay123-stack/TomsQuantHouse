import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { 
  Search, 
  TrendingUp, 
  TrendingDown, 
  RefreshCw,
  Star,
  Activity,
  DollarSign,
  BarChart3,
  Eye,
  Bell
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import { useAppStore } from '../../store';

// Mock market data
const marketSymbols = [
  { symbol: 'AAPL', name: 'Apple Inc.', price: 176.50, change: 2.35, changePercent: 1.35, volume: 45672000 },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', price: 142.30, change: -1.20, changePercent: -0.84, volume: 23456000 },
  { symbol: 'TSLA', name: 'Tesla Inc.', price: 245.80, change: 8.75, changePercent: 3.69, volume: 67890000 },
  { symbol: 'MSFT', name: 'Microsoft Corp.', price: 380.25, change: 4.12, changePercent: 1.10, volume: 34567000 },
  { symbol: 'NVDA', name: 'NVIDIA Corp.', price: 485.90, change: -5.25, changePercent: -1.07, volume: 89765000 },
  { symbol: 'AMZN', name: 'Amazon.com Inc.', price: 156.75, change: 2.89, changePercent: 1.88, volume: 41234000 },
  { symbol: 'META', name: 'Meta Platforms', price: 321.40, change: -3.22, changePercent: -0.99, volume: 19876000 },
  { symbol: 'NFLX', name: 'Netflix Inc.', price: 467.30, change: 7.45, changePercent: 1.62, volume: 8765000 }
];

const realtimeData = [
  { time: '09:30', price: 176.20, volume: 1200000 },
  { time: '09:45', price: 176.35, volume: 1400000 },
  { time: '10:00', price: 176.80, volume: 1100000 },
  { time: '10:15', price: 176.95, volume: 1300000 },
  { time: '10:30', price: 177.20, volume: 1600000 },
  { time: '10:45', price: 176.90, volume: 1250000 },
  { time: '11:00', price: 177.10, volume: 1800000 },
  { time: '11:15', price: 176.75, volume: 1450000 },
  { time: '11:30', price: 176.50, volume: 1650000 },
  { time: '11:45', price: 176.85, volume: 1950000 },
  { time: '12:00', price: 176.50, volume: 1750000 },
];

export const MarketDataDashboard: React.FC = () => {
  const { marketData, setMarketData, updateMarketData } = useAppStore();
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [searchTerm, setSearchTerm] = useState('');
  const [watchlist, setWatchlist] = useState(['AAPL', 'GOOGL', 'TSLA']);

  React.useEffect(() => {
    // Initialize market data
    const marketMap = new Map();
    marketSymbols.forEach(symbol => {
      marketMap.set(symbol.symbol, {
        symbol: symbol.symbol,
        price: symbol.price,
        change: symbol.change,
        changePercent: symbol.changePercent,
        volume: symbol.volume,
        bid: symbol.price - 0.05,
        ask: symbol.price + 0.05,
        timestamp: Date.now()
      });
    });
    setMarketData(marketMap);
  }, [setMarketData]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1000000) {
      return `${(volume / 1000000).toFixed(1)}M`;
    }
    return `${(volume / 1000).toFixed(0)}K`;
  };

  const toggleWatchlist = (symbol: string) => {
    setWatchlist(prev => 
      prev.includes(symbol) 
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol]
    );
  };

  const selectedSymbolData = marketSymbols.find(s => s.symbol === selectedSymbol);
  const filteredSymbols = marketSymbols.filter(symbol => 
    symbol.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
    symbol.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Market Data
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Real-time market data and price monitoring
        </p>
      </div>

      {/* Market Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">S&P 500</p>
                <p className="text-xl font-bold">4,567.89</p>
                <p className="text-sm text-green-600">+12.34 (+0.27%)</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">NASDAQ</p>
                <p className="text-xl font-bold">14,234.56</p>
                <p className="text-sm text-blue-600">+45.67 (+0.32%)</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">DOW</p>
                <p className="text-xl font-bold">35,678.90</p>
                <p className="text-sm text-purple-600">+89.12 (+0.25%)</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <DollarSign className="h-5 w-5 text-yellow-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">VIX</p>
                <p className="text-xl font-bold">18.45</p>
                <p className="text-sm text-yellow-600">-0.78 (-4.06%)</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Market Watch */}
        <div className="lg:col-span-1 space-y-4">
          {/* Watchlist */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Watchlist</span>
                <Button size="sm" variant="outline">
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {watchlist.map((symbol) => {
                  const symbolData = marketSymbols.find(s => s.symbol === symbol);
                  if (!symbolData) return null;
                  
                  return (
                    <div
                      key={symbol}
                      className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                      onClick={() => setSelectedSymbol(symbol)}
                    >
                      <div>
                        <div className="font-medium">{symbol}</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          {formatCurrency(symbolData.price)}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-sm font-medium ${
                          symbolData.change >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {symbolData.change >= 0 ? '+' : ''}{symbolData.changePercent.toFixed(2)}%
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleWatchlist(symbol);
                          }}
                        >
                          <Star className="h-3 w-3 fill-current" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Market Screener */}
          <Card>
            <CardHeader>
              <CardTitle>Market Screener</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                  <Input
                    placeholder="Search symbols..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
                
                <div className="max-h-96 overflow-y-auto space-y-2">
                  {filteredSymbols.map((symbol) => (
                    <div
                      key={symbol.symbol}
                      className="flex items-center justify-between p-2 hover:bg-gray-50 dark:hover:bg-gray-800 rounded cursor-pointer"
                      onClick={() => setSelectedSymbol(symbol.symbol)}
                    >
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">{symbol.symbol}</span>
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {symbol.name}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium">
                          {formatCurrency(symbol.price)}
                        </span>
                        <div className="flex items-center space-x-1">
                          {symbol.change >= 0 ? (
                            <TrendingUp className="h-3 w-3 text-green-600" />
                          ) : (
                            <TrendingDown className="h-3 w-3 text-red-600" />
                          )}
                          <span className={`text-xs ${
                            symbol.change >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                            {symbol.change >= 0 ? '+' : ''}{symbol.changePercent.toFixed(2)}%
                          </span>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleWatchlist(symbol.symbol);
                          }}
                        >
                          <Star className={`h-3 w-3 ${
                            watchlist.includes(symbol.symbol) 
                              ? 'fill-current text-yellow-500' 
                              : 'text-gray-400'
                          }`} />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Price Chart */}
        <div className="lg:col-span-2 space-y-4">
          {/* Symbol Header */}
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold">{selectedSymbolData?.symbol}</h2>
                  <p className="text-gray-600 dark:text-gray-400">{selectedSymbolData?.name}</p>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold">
                    {formatCurrency(selectedSymbolData?.price || 0)}
                  </div>
                  <div className={`flex items-center space-x-1 ${
                    (selectedSymbolData?.change || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {(selectedSymbolData?.change || 0) >= 0 ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    <span className="font-medium">
                      {(selectedSymbolData?.change || 0) >= 0 ? '+' : ''}
                      {selectedSymbolData?.change.toFixed(2)} 
                      ({(selectedSymbolData?.changePercent || 0) >= 0 ? '+' : ''}
                      {(selectedSymbolData?.changePercent || 0).toFixed(2)}%)
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-4 mt-4">
                <Badge variant="outline">
                  Volume: {formatVolume(selectedSymbolData?.volume || 0)}
                </Badge>
                <Badge variant="outline">
                  Bid: {formatCurrency((selectedSymbolData?.price || 0) - 0.05)}
                </Badge>
                <Badge variant="outline">
                  Ask: {formatCurrency((selectedSymbolData?.price || 0) + 0.05)}
                </Badge>
                <div className="flex space-x-2 ml-auto">
                  <Button size="sm" variant="outline">
                    <Bell className="h-4 w-4 mr-2" />
                    Set Alert
                  </Button>
                  <Button size="sm" variant="outline">
                    <Eye className="h-4 w-4 mr-2" />
                    Watch
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Price Chart */}
          <Card>
            <CardHeader>
              <CardTitle>{selectedSymbolData?.symbol} Price Chart</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <AreaChart data={realtimeData}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                  <XAxis dataKey="time" stroke="#6b7280" fontSize={12} />
                  <YAxis 
                    stroke="#6b7280" 
                    fontSize={12}
                    domain={['dataMin - 1', 'dataMax + 1']}
                    tickFormatter={(value) => `$${value.toFixed(2)}`}
                  />
                  <Tooltip 
                    formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
                    labelStyle={{ color: '#1f2937' }}
                    contentStyle={{ 
                      backgroundColor: '#f9fafb', 
                      border: '1px solid #e5e7eb',
                      borderRadius: '6px'
                    }}
                  />
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
        </div>
      </div>
    </div>
  );
};