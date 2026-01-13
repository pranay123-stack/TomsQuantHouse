import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { GitBranch, Play, Pause, CheckCircle, XCircle, Clock } from 'lucide-react';
import { useAppStore } from '../../store';
import { Workflow } from '../../types';

const mockWorkflows: Workflow[] = [
  {
    id: '1',
    name: 'Daily Market Analysis',
    description: 'Comprehensive market analysis and signal generation',
    status: 'running',
    progress: 75,
    nodes: [],
    edges: [],
    created: Date.now() - 3600000,
    updated: Date.now() - 300000
  },
  {
    id: '2',
    name: 'Risk Assessment',
    description: 'Portfolio risk monitoring and alerts',
    status: 'completed',
    progress: 100,
    nodes: [],
    edges: [],
    created: Date.now() - 7200000,
    updated: Date.now() - 600000
  },
  {
    id: '3',
    name: 'News Sentiment Analysis',
    description: 'Real-time news sentiment tracking',
    status: 'paused',
    progress: 45,
    nodes: [],
    edges: [],
    created: Date.now() - 10800000,
    updated: Date.now() - 1800000
  },
  {
    id: '4',
    name: 'Rebalancing Strategy',
    description: 'Automated portfolio rebalancing',
    status: 'failed',
    progress: 20,
    nodes: [],
    edges: [],
    created: Date.now() - 14400000,
    updated: Date.now() - 3600000
  }
];

const getStatusIcon = (status: Workflow['status']) => {
  switch (status) {
    case 'running':
      return <Play className="h-4 w-4 text-green-500" />;
    case 'paused':
      return <Pause className="h-4 w-4 text-yellow-500" />;
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-blue-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-500" />;
  }
};

const getStatusColor = (status: Workflow['status']) => {
  switch (status) {
    case 'running':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
    case 'paused':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
    case 'completed':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
    case 'failed':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
  }
};

export const WorkflowStatus: React.FC = () => {
  const { workflows, setWorkflows } = useAppStore();

  React.useEffect(() => {
    setWorkflows(mockWorkflows);
  }, [setWorkflows]);

  const formatTimeAgo = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    const hours = Math.floor(diff / 3600000);
    
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const runningWorkflows = workflows.filter(w => w.status === 'running').length;
  const completedToday = workflows.filter(w => 
    w.status === 'completed' && 
    Date.now() - w.updated < 86400000
  ).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <GitBranch className="h-5 w-5" />
          <span>Workflow Status</span>
          <Badge variant="secondary">{runningWorkflows}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {workflows.slice(0, 4).map((workflow) => (
            <div
              key={workflow.id}
              className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(workflow.status)}
                  <h4 className="font-medium text-sm">{workflow.name}</h4>
                  <Badge 
                    variant="outline" 
                    className={`text-xs ${getStatusColor(workflow.status)}`}
                  >
                    {workflow.status}
                  </Badge>
                </div>
                <span className="text-xs text-gray-500">
                  {formatTimeAgo(workflow.updated)}
                </span>
              </div>
              
              <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                {workflow.description}
              </p>
              
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      workflow.status === 'running' ? 'bg-blue-500' :
                      workflow.status === 'completed' ? 'bg-green-500' :
                      workflow.status === 'failed' ? 'bg-red-500' :
                      'bg-yellow-500'
                    }`}
                    style={{ width: `${workflow.progress}%` }}
                  />
                </div>
                <span className="text-xs text-gray-600 dark:text-gray-400">
                  {workflow.progress}%
                </span>
              </div>
            </div>
          ))}

          <div className="grid grid-cols-2 gap-4 pt-2">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {completedToday}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                Completed Today
              </div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {runningWorkflows}
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400">
                Currently Running
              </div>
            </div>
          </div>

          <div className="text-center pt-2">
            <button className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              View all workflows →
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};