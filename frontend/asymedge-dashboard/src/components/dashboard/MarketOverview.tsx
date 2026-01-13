import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { useAppStore } from '../../store';
import { MarketData } from '../../types';

const mockMarketData: MarketData[] = [
  {
    symbol: 'S&P 500',
    price: 4567.89,
    change: 23.45,
    changePercent: 0.52,
    volume: 3456789000,
    bid: 4567.80,
    ask: 4567.95,
    timestamp: Date.now()
  },
  {
    symbol: 'NASDAQ',
    price: 14234.67,
    change: -45.23,
    changePercent: -0.32,
    volume: 5678900000,
    bid: 14234.50,
    ask: 14234.80,
    timestamp: Date.now()
  },
  {
    symbol: 'DOW',
    price: 35432.10,
    change: 156.78,
    changePercent: 0.44,
    volume: 2345678000,
    bid: 35432.00,
    ask: 35432.25,
    timestamp: Date.now()
  },
  {
    symbol: 'BTC-USD',
    price: 43250.75,
    change: 1234.50,
    changePercent: 2.94,
    volume: 28900000000,
    bid: 43250.25,
    ask: 43251.00,
    timestamp: Date.now()
  }
];

export const MarketOverview: React.FC = () => {
  const { marketData, setMarketData } = useAppStore();

  React.useEffect(() => {
    const dataMap = new Map<string, MarketData>();
    mockMarketData.forEach(item => {
      dataMap.set(item.symbol, item);
    });
    setMarketData(dataMap);
  }, [setMarketData]);

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'decimal',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(price);
  };

  const formatVolume = (volume: number) => {
    if (volume >= 1e9) {
      return `${(volume / 1e9).toFixed(1)}B`;
    }
    if (volume >= 1e6) {
      return `${(volume / 1e6).toFixed(1)}M`;
    }
    if (volume >= 1e3) {
      return `${(volume / 1e3).toFixed(1)}K`;
    }
    return volume.toString();
  };

  const marketIndices = Array.from(marketData.values()).filter(
    data => ['S&P 500', 'NASDAQ', 'DOW'].includes(data.symbol)
  );
  
  const cryptoData = Array.from(marketData.values()).filter(
    data => data.symbol.includes('BTC')
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Activity className="h-5 w-5" />
          <span>Market Overview</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Market Indices */}
          <div>
            <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
              Market Indices
            </h4>
            <div className="space-y-2">
              {marketIndices.map((data) => (
                <div
                  key={data.symbol}
                  className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded"
                >
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-sm">{data.symbol}</span>
                    {data.change >= 0 ? (
                      <TrendingUp className="h-3 w-3 text-green-500" />
                    ) : (
                      <TrendingDown className="h-3 w-3 text-red-500" />
                    )}
                  </div>
                  <div className="text-right">
                    <div className="font-medium text-sm">
                      {formatPrice(data.price)}
                    </div>
                    <div className={`text-xs ${
                      data.change >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {data.change >= 0 ? '+' : ''}{data.changePercent.toFixed(2)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Crypto */}
          {cryptoData.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
                Cryptocurrency
              </h4>
              <div className="space-y-2">
                {cryptoData.map((data) => (
                  <div
                    key={data.symbol}
                    className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded"
                  >
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-sm">{data.symbol}</span>
                      {data.change >= 0 ? (
                        <TrendingUp className="h-3 w-3 text-green-500" />
                      ) : (
                        <TrendingDown className="h-3 w-3 text-red-500" />
                      )}
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-sm">
                        ${formatPrice(data.price)}
                      </div>
                      <div className={`text-xs ${
                        data.change >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {data.change >= 0 ? '+' : ''}{data.changePercent.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Market Status */}
          <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Market Status
              </span>
              <Badge variant="default" className="bg-green-100 text-green-800">
                Open
              </Badge>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Closes in 2h 45m
            </div>
          </div>

          <div className="text-center pt-2">
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              View detailed market data →
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};