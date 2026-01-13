import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from 'react-query'
import {
  CpuChipIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  PlayIcon,
  PauseIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'

interface Agent {
  id: string
  name: string
  type: 'research' | 'prediction' | 'risk' | 'execution'
  status: 'active' | 'idle' | 'error' | 'maintenance'
  lastActivity: string
  performance: {
    accuracy: number
    speed: number
    reliability: number
  }
  memoryUsage: number
  currentTask?: string
  uptime: number
}

const AgentStatus: React.FC = () => {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null)

  const { data: agents, isLoading, refetch } = useQuery('agents-status', async () => {
    const response = await fetch('/api/v1/agents/status')
    return response.json()
  }, {
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const getAgentIcon = (type: string) => {
    switch (type) {
      case 'research':
        return '🔍'
      case 'prediction':
        return '🧠'
      case 'risk':
        return '🛡️'
      case 'execution':
        return '⚡'
      default:
        return '🤖'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-400'
      case 'idle':
        return 'text-yellow-400'
      case 'error':
        return 'text-red-400'
      case 'maintenance':
        return 'text-blue-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircleIcon className="h-4 w-4" />
      case 'idle':
        return <PauseIcon className="h-4 w-4" />
      case 'error':
        return <XCircleIcon className="h-4 w-4" />
      case 'maintenance':
        return <ExclamationTriangleIcon className="h-4 w-4" />
      default:
        return <ClockIcon className="h-4 w-4" />
    }
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white flex items-center">
          <CpuChipIcon className="h-5 w-5 mr-2" />
          Agent Status
        </h3>
        <button
          onClick={() => refetch()}
          className="p-2 text-gray-400 hover:text-white transition-colors"
        >
          <ArrowPathIcon className="h-4 w-4" />
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <div className="space-y-3">
          {agents?.map((agent: Agent) => (
            <motion.div
              key={agent.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={{ scale: 1.02 }}
              className="bg-gray-700 rounded-lg p-4 cursor-pointer transition-all duration-200 hover:bg-gray-600"
              onClick={() => setSelectedAgent(agent)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{getAgentIcon(agent.type)}</span>
                  <div>
                    <h4 className="font-medium text-white">{agent.name}</h4>
                    <p className="text-sm text-gray-400">{agent.currentTask || 'Ready'}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <div className={`flex items-center space-x-1 ${getStatusColor(agent.status)}`}>
                    {getStatusIcon(agent.status)}
                    <span className="text-xs capitalize">{agent.status}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-400">Memory</p>
                    <p className="text-sm text-white">{agent.memoryUsage.toFixed(1)}%</p>
                  </div>
                </div>
              </div>

              {/* Performance Metrics */}
              <div className="mt-3 grid grid-cols-3 gap-2">
                <div className="text-center">
                  <p className="text-xs text-gray-400">Accuracy</p>
                  <div className="flex items-center justify-center mt-1">
                    <div className="w-full bg-gray-600 rounded-full h-2 mr-2">
                      <div
                        className="bg-green-500 h-2 rounded-full"
                        style={{ width: `${agent.performance.accuracy}%` }}
                      ></div>
                    </div>
                    <span className="text-xs text-white">
                      {(agent.performance.accuracy * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-400">Speed</p>
                  <div className="flex items-center justify-center mt-1">
                    <div className="w-full bg-gray-600 rounded-full h-2 mr-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${agent.performance.speed}%` }}
                      ></div>
                    </div>
                    <span className="text-xs text-white">
                      {(agent.performance.speed * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-400">Reliability</p>
                  <div className="flex items-center justify-center mt-1">
                    <div className="w-full bg-gray-600 rounded-full h-2 mr-2">
                      <div
                        className="bg-yellow-500 h-2 rounded-full"
                        style={{ width: `${agent.performance.reliability}%` }}
                      ></div>
                    </div>
                    <span className="text-xs text-white">
                      {(agent.performance.reliability * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Agent Detail Modal */}
      <AnimatePresence>
        {selectedAgent && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => setSelectedAgent(null)}
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold text-white">
                  {getAgentIcon(selectedAgent.type)} {selectedAgent.name}
                </h3>
                <button
                  onClick={() => setSelectedAgent(null)}
                  className="text-gray-400 hover:text-white"
                >
                  <XCircleIcon className="h-6 w-6" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-400">Status</p>
                  <div className={`flex items-center space-x-2 ${getStatusColor(selectedAgent.status)}`}>
                    {getStatusIcon(selectedAgent.status)}
                    <span className="capitalize">{selectedAgent.status}</span>
                  </div>
                </div>

                <div>
                  <p className="text-sm text-gray-400">Current Task</p>
                  <p className="text-white">{selectedAgent.currentTask || 'No active task'}</p>
                </div>

                <div>
                  <p className="text-sm text-gray-400">Uptime</p>
                  <p className="text-white">
                    {Math.floor(selectedAgent.uptime / 3600)}h {Math.floor((selectedAgent.uptime % 3600) / 60)}m
                  </p>
                </div>

                <div>
                  <p className="text-sm text-gray-400 mb-2">Performance Metrics</p>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p className="text-xs text-gray-400">Accuracy</p>
                      <p className="text-lg font-semibold text-white">
                        {(selectedAgent.performance.accuracy * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Speed</p>
                      <p className="text-lg font-semibold text-white">
                        {(selectedAgent.performance.speed * 100).toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Reliability</p>
                      <p className="text-lg font-semibold text-white">
                        {(selectedAgent.performance.reliability * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default AgentStatus