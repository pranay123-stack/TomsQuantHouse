import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { 
  Settings as SettingsIcon, 
  User, 
  Bell, 
  Shield, 
  Palette, 
  Database,
  Monitor,
  Moon,
  Sun,
  Save,
  RefreshCw,
  Download,
  Upload,
  Trash2,
  Key,
  Globe,
  Zap,
  AlertTriangle
} from 'lucide-react';
import { useAppStore } from '../../store';

export const SettingsDashboard: React.FC = () => {
  const { theme, setTheme, user, updateUser } = useAppStore();
  const [activeTab, setActiveTab] = useState('profile');
  const [settings, setSettings] = useState({
    // Profile settings
    name: user?.name || '',
    email: user?.email || '',
    // Notification settings
    emailNotifications: true,
    pushNotifications: true,
    tradeAlerts: true,
    systemUpdates: false,
    // Trading settings
    defaultRiskLevel: 'medium',
    autoExecution: false,
    confirmationRequired: true,
    // Display settings
    themeMode: theme.mode,
    currency: 'USD',
    timezone: 'UTC-5',
    chartType: 'candlestick',
    // API settings
    apiKey: '••••••••••••••••',
    webhookUrl: 'https://api.asymedge.com/webhook',
    // Security settings
    twoFactorEnabled: false,
    sessionTimeout: 30,
    ipWhitelist: ['192.168.1.1', '10.0.0.1']
  });

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'trading', label: 'Trading', icon: Zap },
    { id: 'display', label: 'Display', icon: Monitor },
    { id: 'api', label: 'API & Integrations', icon: Database },
    { id: 'security', label: 'Security', icon: Shield },
  ];

  const handleSave = () => {
    // Save settings logic here
    console.log('Settings saved');
  };

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    
    // Handle theme changes
    if (key === 'themeMode') {
      setTheme({ mode: value });
    }
  };

  const ProfileSettings = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Personal Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Full Name</label>
            <Input
              value={settings.name}
              onChange={(e) => handleSettingChange('name', e.target.value)}
              placeholder="Enter your full name"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Email Address</label>
            <Input
              value={settings.email}
              onChange={(e) => handleSettingChange('email', e.target.value)}
              placeholder="Enter your email"
              type="email"
            />
          </div>
          <div>
            <label className="text-sm font-medium">Role</label>
            <Input value={user?.role || ''} disabled />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Account Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Default Currency</label>
            <select
              value={settings.currency}
              onChange={(e) => handleSettingChange('currency', e.target.value)}
              className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-background"
            >
              <option value="USD">USD - US Dollar</option>
              <option value="EUR">EUR - Euro</option>
              <option value="GBP">GBP - British Pound</option>
              <option value="JPY">JPY - Japanese Yen</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">Timezone</label>
            <select
              value={settings.timezone}
              onChange={(e) => handleSettingChange('timezone', e.target.value)}
              className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-background"
            >
              <option value="UTC-8">Pacific Time (UTC-8)</option>
              <option value="UTC-5">Eastern Time (UTC-5)</option>
              <option value="UTC+0">UTC (UTC+0)</option>
              <option value="UTC+1">Central European Time (UTC+1)</option>
            </select>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const NotificationSettings = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Notification Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">Email Notifications</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Receive notifications via email
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.emailNotifications}
              onChange={(e) => handleSettingChange('emailNotifications', e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">Push Notifications</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Receive browser push notifications
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.pushNotifications}
              onChange={(e) => handleSettingChange('pushNotifications', e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">Trade Alerts</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Get notified about trade executions
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.tradeAlerts}
              onChange={(e) => handleSettingChange('tradeAlerts', e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">System Updates</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Receive notifications about system maintenance
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.systemUpdates}
              onChange={(e) => handleSettingChange('systemUpdates', e.target.checked)}
              className="h-4 w-4"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const TradingSettings = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Trading Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Default Risk Level</label>
            <select
              value={settings.defaultRiskLevel}
              onChange={(e) => handleSettingChange('defaultRiskLevel', e.target.value)}
              className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-background"
            >
              <option value="low">Low Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="high">High Risk</option>
            </select>
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">Auto Execution</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Automatically execute trades without confirmation
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.autoExecution}
              onChange={(e) => handleSettingChange('autoExecution', e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">Confirmation Required</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Require confirmation before executing trades
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.confirmationRequired}
              onChange={(e) => handleSettingChange('confirmationRequired', e.target.checked)}
              className="h-4 w-4"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const DisplaySettings = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Theme & Appearance</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">Theme</label>
            <div className="flex space-x-2 mt-2">
              <Button
                variant={settings.themeMode === 'light' ? 'default' : 'outline'}
                onClick={() => handleSettingChange('themeMode', 'light')}
                className="flex items-center space-x-2"
              >
                <Sun className="h-4 w-4" />
                <span>Light</span>
              </Button>
              <Button
                variant={settings.themeMode === 'dark' ? 'default' : 'outline'}
                onClick={() => handleSettingChange('themeMode', 'dark')}
                className="flex items-center space-x-2"
              >
                <Moon className="h-4 w-4" />
                <span>Dark</span>
              </Button>
            </div>
          </div>
          
          <div>
            <label className="text-sm font-medium">Default Chart Type</label>
            <select
              value={settings.chartType}
              onChange={(e) => handleSettingChange('chartType', e.target.value)}
              className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-background"
            >
              <option value="candlestick">Candlestick</option>
              <option value="line">Line Chart</option>
              <option value="area">Area Chart</option>
              <option value="bar">Bar Chart</option>
            </select>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const APISettings = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>API Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium">API Key</label>
            <div className="flex space-x-2 mt-1">
              <Input
                value={settings.apiKey}
                onChange={(e) => handleSettingChange('apiKey', e.target.value)}
                placeholder="Enter API key"
                type="password"
              />
              <Button variant="outline">
                <Key className="h-4 w-4 mr-2" />
                Generate
              </Button>
            </div>
          </div>
          
          <div>
            <label className="text-sm font-medium">Webhook URL</label>
            <Input
              value={settings.webhookUrl}
              onChange={(e) => handleSettingChange('webhookUrl', e.target.value)}
              placeholder="Enter webhook URL"
            />
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>Data Export</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Button variant="outline" className="flex items-center justify-center space-x-2">
              <Download className="h-4 w-4" />
              <span>Export Trades</span>
            </Button>
            <Button variant="outline" className="flex items-center justify-center space-x-2">
              <Download className="h-4 w-4" />
              <span>Export Analytics</span>
            </Button>
            <Button variant="outline" className="flex items-center justify-center space-x-2">
              <Upload className="h-4 w-4" />
              <span>Import Settings</span>
            </Button>
            <Button variant="outline" className="flex items-center justify-center space-x-2">
              <RefreshCw className="h-4 w-4" />
              <span>Reset to Default</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );

  const SecuritySettings = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Security Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">Two-Factor Authentication</h4>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Add an extra layer of security to your account
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.twoFactorEnabled}
              onChange={(e) => handleSettingChange('twoFactorEnabled', e.target.checked)}
              className="h-4 w-4"
            />
          </div>
          
          <div>
            <label className="text-sm font-medium">Session Timeout (minutes)</label>
            <Input
              type="number"
              value={settings.sessionTimeout}
              onChange={(e) => handleSettingChange('sessionTimeout', parseInt(e.target.value))}
              min="5"
              max="1440"
            />
          </div>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>IP Whitelist</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            {settings.ipWhitelist.map((ip, index) => (
              <div key={index} className="flex items-center space-x-2">
                <Input value={ip} disabled />
                <Button variant="outline" size="sm">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full">
            <Globe className="h-4 w-4 mr-2" />
            Add IP Address
          </Button>
        </CardContent>
      </Card>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case 'profile': return <ProfileSettings />;
      case 'notifications': return <NotificationSettings />;
      case 'trading': return <TradingSettings />;
      case 'display': return <DisplaySettings />;
      case 'api': return <APISettings />;
      case 'security': return <SecuritySettings />;
      default: return <ProfileSettings />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Settings
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Manage your account preferences and system configuration
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Settings Navigation */}
        <Card>
          <CardContent className="p-4">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 text-left rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
                  }`}
                >
                  <tab.icon className="h-4 w-4" />
                  <span className="text-sm font-medium">{tab.label}</span>
                </button>
              ))}
            </nav>
          </CardContent>
        </Card>

        {/* Settings Content */}
        <div className="lg:col-span-3">
          {renderTabContent()}
          
          {/* Save Button */}
          <div className="flex justify-end space-x-2 mt-6">
            <Button variant="outline">
              Cancel
            </Button>
            <Button onClick={handleSave}>
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};