import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { 
  GitBranch, 
  Plus, 
  Play, 
  Pause, 
  Square,
  Settings,
  Activity,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import { useAppStore } from '../../store';

const workflowTemplates = [
  {
    id: 'market-analysis',
    name: 'Market Analysis Workflow',
    description: 'Automated market analysis and signal generation',
    nodes: 4,
    category: 'Analysis'
  },
  {
    id: 'risk-assessment',
    name: 'Risk Assessment',
    description: 'Portfolio risk monitoring and alerts',
    nodes: 3,
    category: 'Risk Management'
  },
  {
    id: 'sentiment-analysis',
    name: 'Sentiment Analysis',
    description: 'News and social media sentiment tracking',
    nodes: 5,
    category: 'Data Processing'
  },
  {
    id: 'rebalancing',
    name: 'Portfolio Rebalancing',
    description: 'Automated portfolio rebalancing based on targets',
    nodes: 6,
    category: 'Portfolio Management'
  }
];

export const WorkflowVisualization: React.FC = () => {
  const { workflows, setWorkflows } = useAppStore();
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  React.useEffect(() => {
    // Workflows are already set in WorkflowStatus component
  }, [workflows]);

  const getStatusIcon = (status: string) => {
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

  const getStatusColor = (status: string) => {
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

  const getProgressColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-500';
      case 'paused':
        return 'bg-yellow-500';
      case 'completed':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const handleToggleWorkflow = (workflowId: string) => {
    const updatedWorkflows = workflows.map(workflow =>
      workflow.id === workflowId
        ? { 
            ...workflow, 
            status: workflow.status === 'running' ? 'paused' as const : 'running' as const 
          }
        : workflow
    );
    setWorkflows(updatedWorkflows);
  };

  const SimpleWorkflowDiagram: React.FC<{ workflow: any }> = ({ workflow }) => {
    const nodeCount = workflow.nodes?.length || 4;
    const nodes = Array.from({ length: nodeCount }, (_, i) => ({
      id: `node-${i}`,
      label: `Step ${i + 1}`,
      status: workflow.status === 'completed' ? 'completed' : 
              workflow.status === 'running' && i < Math.floor(nodeCount * workflow.progress / 100) ? 'completed' :
              workflow.status === 'running' && i === Math.floor(nodeCount * workflow.progress / 100) ? 'running' : 'pending'
    }));

    return (
      <div className="flex items-center space-x-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        {nodes.map((node, index) => (
          <React.Fragment key={node.id}>
            <div className="flex flex-col items-center space-y-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                node.status === 'completed' ? 'bg-green-500 text-white' :
                node.status === 'running' ? 'bg-blue-500 text-white animate-pulse' :
                'bg-gray-300 dark:bg-gray-600 text-gray-600 dark:text-gray-400'
              }`}>
                {index + 1}
              </div>
              <span className="text-xs text-gray-600 dark:text-gray-400 max-w-16 truncate">
                {node.label}
              </span>
            </div>
            {index < nodes.length - 1 && (
              <div className={`w-8 h-0.5 ${
                node.status === 'completed' ? 'bg-green-500' :
                workflow.status === 'running' ? 'bg-blue-500' :
                'bg-gray-300 dark:bg-gray-600'
              }`} />
            )}
          </React.Fragment>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Workflow Visualization
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Design and monitor AI-powered trading workflows with LangGraph
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Workflow
        </Button>
      </div>

      {/* Workflow Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <GitBranch className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Workflows</p>
                <p className="text-xl font-bold">{workflows.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Play className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Running</p>
                <p className="text-xl font-bold">
                  {workflows.filter(w => w.status === 'running').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Completed Today</p>
                <p className="text-xl font-bold">
                  {workflows.filter(w => w.status === 'completed').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Activity className="h-5 w-5 text-purple-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Avg Progress</p>
                <p className="text-xl font-bold">
                  {workflows.length > 0 
                    ? Math.round(workflows.reduce((sum, w) => sum + w.progress, 0) / workflows.length)
                    : 0}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Workflows List */}
      <div className="space-y-4">
        {workflows.map((workflow) => (
          <Card key={workflow.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex items-center space-x-2">
                  <GitBranch className="h-5 w-5 text-blue-600" />
                  <CardTitle className="text-lg">{workflow.name}</CardTitle>
                </div>
                <div className="flex items-center space-x-2">
                  {getStatusIcon(workflow.status)}
                  <Badge className={getStatusColor(workflow.status)}>
                    {workflow.status}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {workflow.description}
                </p>
                
                <SimpleWorkflowDiagram workflow={workflow} />
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className="text-sm">
                      <span className="text-gray-600 dark:text-gray-400">Progress:</span>
                      <span className="ml-2 font-medium">{workflow.progress}%</span>
                    </div>
                    <div className="text-sm">
                      <span className="text-gray-600 dark:text-gray-400">Nodes:</span>
                      <span className="ml-2 font-medium">{workflow.nodes?.length || 4}</span>
                    </div>
                  </div>
                  
                  <div className="flex space-x-2">
                    <Button
                      size="sm"
                      variant={workflow.status === 'running' ? 'outline' : 'default'}
                      onClick={() => handleToggleWorkflow(workflow.id)}
                    >
                      {workflow.status === 'running' ? (
                        <>
                          <Pause className="h-3 w-3 mr-1" />
                          Pause
                        </>
                      ) : (
                        <>
                          <Play className="h-3 w-3 mr-1" />
                          Start
                        </>
                      )}
                    </Button>
                    <Button size="sm" variant="outline">
                      <Settings className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Workflow Templates */}
      <Card>
        <CardHeader>
          <CardTitle>Workflow Templates</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {workflowTemplates.map((template) => (
              <div
                key={template.id}
                className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
              >
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-medium">{template.name}</h4>
                  <Badge variant="outline">{template.category}</Badge>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  {template.description}
                </p>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-500">
                    {template.nodes} nodes
                  </span>
                  <Button size="sm" variant="outline">
                    Use Template
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};