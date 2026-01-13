import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from 'react-hot-toast';

import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { LoginForm } from './components/auth/LoginForm';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { DashboardHome } from './components/dashboard/DashboardHome';
import { TradingDashboard } from './components/trading/TradingDashboard';
import { AgentManagement } from './components/agents/AgentManagement';
import { WorkflowVisualization } from './components/workflows/WorkflowVisualization';
import { AnalyticsDashboard } from './components/analytics/AnalyticsDashboard';
import { MarketDataDashboard } from './components/market/MarketDataDashboard';
import { SettingsDashboard } from './components/settings/SettingsDashboard';
import { ErrorBoundary } from './components/ErrorBoundary';

import './App.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10, // 10 minutes (renamed from cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <Router>
          <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<LoginForm />} />
              
              {/* Protected Routes */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <DashboardLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<DashboardHome />} />
                <Route path="trading" element={<TradingDashboard />} />
                <Route path="agents" element={<AgentManagement />} />
                <Route path="workflows" element={<WorkflowVisualization />} />
                <Route path="analytics" element={<AnalyticsDashboard />} />
                <Route path="market" element={<MarketDataDashboard />} />
                <Route path="settings" element={<SettingsDashboard />} />
              </Route>

              {/* Error Routes */}
              <Route path="/unauthorized" element={
                <div className="min-h-screen flex items-center justify-center">
                  <div className="text-center">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                      Unauthorized
                    </h1>
                    <p className="mt-2 text-gray-600 dark:text-gray-400">
                      You don't have permission to access this resource.
                    </p>
                  </div>
                </div>
              } />

              {/* Catch all route */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </div>

          {/* Toast notifications */}
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 4000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />

          {/* React Query Devtools */}
          <ReactQueryDevtools initialIsOpen={false} />
        </Router>
      </ErrorBoundary>
    </QueryClientProvider>
  );
};

export default App;
