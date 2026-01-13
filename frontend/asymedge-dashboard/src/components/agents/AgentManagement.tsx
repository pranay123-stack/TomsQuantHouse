import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { 
  Brain, 
  Plus, 
  Play, 
  Pause, 
  Settings, 
  Trash2,
  Activity,
  CheckCircle,
  XCircle,
  Loader
} from 'lucide-react';
import { useAppStore } from '../../store';

const mockAgentConfigs = {
  letta: {
    name: 'Letta Agent',
    description: 'AI agent powered by Letta framework',
    config: {
      model: 'llama-2-70b',
      memory: 'vector_store',
      tools: ['web_search', 'python_execution', 'data_analysis']
    }
  },
  custom: {
    name: 'Custom Agent',
    description: 'Custom trading agent with specialized logic',
    config: {
      strategy: 'momentum',
      lookback_period: 20,
      risk_threshold: 0.02
    }
  }
};

export const AgentManagement: React.FC = () => {
  const { agents, setAgents } = useAppStore();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentType, setNewAgentType] = useState<'letta' | 'custom'>('letta');

  React.useEffect(() => {
    // Agents are already set in ActiveAgents component
  }, [agents]);

  const handleCreateAgent = () => {
    const newAgent = {
      id: `agent-${Date.now()}`,
      name: newAgentName,
      type: newAgentType,
      status: 'active' as const,
      description: mockAgentConfigs[newAgentType].description,
      lastActive: Date.now(),
      metrics: {
        successRate: 0,
        totalTasks: 0,
        avgExecutionTime: 0
      },
      config: mockAgentConfigs[newAgentType].config
    };
    
    setAgents([...agents, newAgent]);
    setShowCreateModal(false);
    setNewAgentName('');
  };

  const handleToggleAgent = (agentId: string) => {
    const updatedAgents = agents.map(agent =>
      agent.id === agentId
        ? { 
            ...agent, 
            status: agent.status === 'active' ? 'inactive' as const : 'active' as const 
          }
        : agent
    );
    setAgents(updatedAgents);
  };

  const handleDeleteAgent = (agentId: string) => {
    setAgents(agents.filter(agent => agent.id !== agentId));
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'training':
        return <Loader className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'inactive':
        return <Activity className="h-4 w-4 text-gray-500" />;
      default:
        return <Activity className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'training':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'error':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      case 'inactive':
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Agent Management
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Manage AI agents powered by Letta and custom implementations
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Agent
        </Button>
      </div>

      {/* Agent Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Brain className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Agents</p>
                <p className="text-xl font-bold">{agents.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Active</p>
                <p className="text-xl font-bold">
                  {agents.filter(a => a.status === 'active').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <Loader className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Training</p>
                <p className="text-xl font-bold">
                  {agents.filter(a => a.status === 'training').length}
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
                <p className="text-sm text-gray-600 dark:text-gray-400">Avg Success</p>
                <p className="text-xl font-bold">
                  {agents.length > 0 
                    ? (agents.reduce((sum, a) => sum + a.metrics.successRate, 0) / agents.length).toFixed(1)
                    : 0}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Agents Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {agents.map((agent) => (
          <Card key={agent.id} className="cursor-pointer hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex items-center space-x-2">
                  <Brain className="h-5 w-5 text-blue-600" />
                  <CardTitle className="text-lg">{agent.name}</CardTitle>
                </div>
                <div className="flex items-center space-x-1">
                  {getStatusIcon(agent.status)}
                  <Badge className={getStatusColor(agent.status)}>
                    {agent.status}
                  </Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {agent.description}
                </p>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Type:</span>
                    <Badge variant="outline" className="ml-2">
                      {agent.type}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Success Rate:</span>
                    <span className="ml-2 font-medium">
                      {agent.metrics.successRate.toFixed(1)}%
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Tasks:</span>
                    <span className="ml-2 font-medium">{agent.metrics.totalTasks}</span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Avg Time:</span>
                    <span className="ml-2 font-medium">
                      {agent.metrics.avgExecutionTime.toFixed(1)}s
                    </span>
                  </div>
                </div>

                <div className="flex space-x-2 pt-2">
                  <Button
                    size="sm"
                    variant={agent.status === 'active' ? 'outline' : 'default'}
                    onClick={() => handleToggleAgent(agent.id)}
                    className="flex-1"
                  >
                    {agent.status === 'active' ? (
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
                  <Button 
                    size="sm" 
                    variant="destructive"
                    onClick={() => handleDeleteAgent(agent.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Create Agent Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Create New Agent</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Agent Name</label>
                <Input
                  value={newAgentName}
                  onChange={(e) => setNewAgentName(e.target.value)}
                  placeholder="Enter agent name"
                />
              </div>
              
              <div>
                <label className="text-sm font-medium">Agent Type</label>
                <div className="grid grid-cols-2 gap-2 mt-1">
                  <Button
                    variant={newAgentType === 'letta' ? 'default' : 'outline'}
                    onClick={() => setNewAgentType('letta')}
                    className="flex items-center space-x-2"
                  >
                    <Brain className="h-4 w-4" />
                    <span>Letta</span>
                  </Button>
                  <Button
                    variant={newAgentType === 'custom' ? 'default' : 'outline'}
                    onClick={() => setNewAgentType('custom')}
                    className="flex items-center space-x-2"
                    disabled
                  >
                    <Settings className="h-4 w-4" />
                    <span>Custom</span>
                  </Button>
                </div>
              </div>

              <div className="flex space-x-2 pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleCreateAgent}
                  disabled={!newAgentName.trim()}
                  className="flex-1"
                >
                  Create
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};