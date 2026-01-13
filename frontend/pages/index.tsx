import React, { useState, useEffect } from 'react'
import Head from 'next/head'
import { useQuery } from 'react-query'
import { Toaster } from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChartBarIcon,
  CpuChipIcon,
  CurrencyDollarIcon,
  GlobeAltIcon,
  BoltIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  BellIcon
} from '@heroicons/react/24/outline'

import { useAuthStore } from '@/stores/auth'
import { useSocketStore } from '@/stores/socket'
import { useDashboardStore } from '@/stores/dashboard'

import Layout from '@/components/Layout'
import AgentStatus from '@/components/dashboard/AgentStatus'
import TradingMetrics from '@/components/dashboard/TradingMetrics'
import WorkflowVisualization from '@/components/dashboard/WorkflowVisualization'
import RealTimeChart from '@/components/dashboard/RealTimeChart'
import SystemHealth from '@/components/dashboard/SystemHealth'
import AgentCommunication from '@/components/dashboard/AgentCommunication'
import RiskManagement from '@/components/dashboard/RiskManagement'

const Dashboard: React.FC = () => {
  const { user, isAuthenticated } = useAuthStore()
  const { socket, isConnected } = useSocketStore()
  const { dashboard, updateWidgetLayout } = useDashboardStore()
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h')

  // Fetch dashboard data
  const { data: dashboardData, isLoading } = useQuery('dashboard-data', async () => {
    const response = await fetch('/api/v1/dashboard/overview')
    return response.json()
  }, {
    refetchInterval: 10000, // Refresh every 10 seconds
    enabled: isAuthenticated
  })

  // WebSocket connection management
  useEffect(() => {
    if (socket && isAuthenticated) {
      socket.emit('subscribe', {
        channels: ['agents', 'trading', 'workflows', 'system']
      })
    }
  }, [socket, isAuthenticated])

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-lg">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Authentication Required</h2>
          <p className="text-gray-600">Please log in to access the dashboard.</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <>
      <Head>
        <title>ASYMEdge Trading Dashboard</title>
        <meta name="description" content="Real-time multi-agent trading dashboard" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <Layout>
        <div className="space-y-6">
          {/* Header */}
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-white">Trading Dashboard</h1>
                <p className="text-gray-300 mt-1">
                  Real-time multi-agent trading system
                </p>
              </div>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span className="text-sm text-gray-300">
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                <div className="text-sm text-gray-300">
                  {new Date().toLocaleTimeString()}
                </div>
              </div>
            </div>
          </div>

          {/* Key Metrics Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-800 rounded-lg p-6"
            >
              <div className="flex items-center">
                <CurrencyDollarIcon className="h-8 w-8 text-green-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-400">Portfolio Value</p>
                  <p className="text-2xl font-semibold text-white">
                    ${dashboardData?.portfolio_value?.toLocaleString() || '0'}
                  </p>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-gray-800 rounded-lg p-6"
            >
              <div className="flex items-center">
                <BoltIcon className="h-8 w-8 text-yellow-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-400">Active Agents</p>
                  <p className="text-2xl font-semibold text-white">
                    {dashboardData?.active_agents || 0}
                  </p>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-gray-800 rounded-lg p-6"
            >
              <div className="flex items-center">
                <ChartBarIcon className="h-8 w-8 text-blue-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-400">Today's P&L</p>
                  <p className="text-2xl font-semibold text-white">
                    {dashboardData?.daily_pnl > 0 ? '+' : ''}
                    ${dashboardData?.daily_pnl?.toFixed(2) || '0.00'}
                  </p>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="bg-gray-800 rounded-lg p-6"
            >
              <div className="flex items-center">
                <ShieldCheckIcon className="h-8 w-8 text-red-500" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-400">Risk Score</p>
                  <p className="text-2xl font-semibold text-white">
                    {dashboardData?.risk_score || 0}/10
                  </p>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Main Dashboard Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column - Trading */}
            <div className="lg:col-span-2 space-y-6">
              <TradingMetrics timeframe={selectedTimeframe} />
              <RealTimeChart />
              <WorkflowVisualization />
            </div>

            {/* Right Column - Agents & Status */}
            <div className="space-y-6">
              <AgentStatus />
              <SystemHealth />
            </div>
          </div>

          {/* Bottom Row - Detailed Views */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AgentCommunication />
            <RiskManagement />
          </div>

          {/* Notifications Panel */}
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, x: 300 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 300 }}
              className="fixed top-4 right-4 w-80 space-y-2 z-50"
            >
              {/* Real-time notifications will be rendered here */}
            </motion.div>
          </AnimatePresence>
        </div>
      </Layout>

      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1F2937',
            color: '#F9FAFB',
            border: '1px solid #374151'
          }
        }}
      />
    </>
  )
}

export default Dashboard