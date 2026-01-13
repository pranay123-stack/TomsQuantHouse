import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Theme, TradingMetrics, Agent, Workflow, DashboardWidget, MarketData, Alert } from '../types';

interface AppState {
  // Auth state
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;

  // Theme state
  theme: Theme;
  setTheme: (theme: Partial<Theme>) => void;

  // Trading state
  tradingMetrics: TradingMetrics | null;
  setTradingMetrics: (metrics: TradingMetrics) => void;

  // Agents state
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  updateAgent: (id: string, updates: Partial<Agent>) => void;

  // Workflows state
  workflows: Workflow[];
  setWorkflows: (workflows: Workflow[]) => void;
  updateWorkflow: (id: string, updates: Partial<Workflow>) => void;

  // Dashboard state
  widgets: DashboardWidget[];
  setWidgets: (widgets: DashboardWidget[]) => void;
  addWidget: (widget: DashboardWidget) => void;
  updateWidget: (id: string, updates: Partial<DashboardWidget>) => void;
  removeWidget: (id: string) => void;

  // Market data state
  marketData: Map<string, MarketData>;
  setMarketData: (data: Map<string, MarketData>) => void;
  updateMarketData: (symbol: string, data: MarketData) => void;

  // Alerts state
  alerts: Alert[];
  setAlerts: (alerts: Alert[]) => void;
  addAlert: (alert: Alert) => void;
  markAlertAsRead: (id: string) => void;
  removeAlert: (id: string) => void;

  // Loading states
  loading: {
    auth: boolean;
    trading: boolean;
    agents: boolean;
    workflows: boolean;
  };
  setLoading: (key: keyof AppState['loading'], value: boolean) => void;

  // Error states
  errors: {
    auth: string | null;
    trading: string | null;
    agents: string | null;
    workflows: string | null;
  };
  setError: (key: keyof AppState['errors'], error: string | null) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Auth state
      user: null,
      isAuthenticated: false,
      login: async (email: string, password: string) => {
        set({ loading: { ...get().loading, auth: true } });
        try {
          // Simulate API call
          await new Promise(resolve => setTimeout(resolve, 1000));
          
          const mockUser: User = {
            id: '1',
            email,
            name: email.split('@')[0],
            role: 'admin',
            permissions: ['read', 'write', 'delete', 'admin']
          };
          
          set({
            user: mockUser,
            isAuthenticated: true,
            loading: { ...get().loading, auth: false }
          });
        } catch (error) {
          set({
            errors: { ...get().errors, auth: 'Login failed' },
            loading: { ...get().loading, auth: false }
          });
        }
      },
      logout: () => {
        set({
          user: null,
          isAuthenticated: false,
          tradingMetrics: null,
          agents: [],
          workflows: [],
          widgets: [],
          marketData: new Map(),
          alerts: []
        });
      },
      updateUser: (updates: Partial<User>) => {
        const user = get().user;
        if (user) {
          set({ user: { ...user, ...updates } });
        }
      },

      // Theme state
      theme: {
        mode: 'dark',
        primaryColor: '#3b82f6',
        secondaryColor: '#6b7280',
        backgroundColor: '#0f172a',
        textColor: '#f1f5f9'
      },
      setTheme: (theme: Partial<Theme>) => {
        set({
          theme: { ...get().theme, ...theme }
        });
      },

      // Trading state
      tradingMetrics: null,
      setTradingMetrics: (metrics: TradingMetrics) => {
        set({ tradingMetrics: metrics });
      },

      // Agents state
      agents: [],
      setAgents: (agents: Agent[]) => {
        set({ agents });
      },
      updateAgent: (id: string, updates: Partial<Agent>) => {
        const agents = get().agents.map(agent =>
          agent.id === id ? { ...agent, ...updates } : agent
        );
        set({ agents });
      },

      // Workflows state
      workflows: [],
      setWorkflows: (workflows: Workflow[]) => {
        set({ workflows });
      },
      updateWorkflow: (id: string, updates: Partial<Workflow>) => {
        const workflows = get().workflows.map(workflow =>
          workflow.id === id ? { ...workflow, ...updates } : workflow
        );
        set({ workflows });
      },

      // Dashboard state
      widgets: [],
      setWidgets: (widgets: DashboardWidget[]) => {
        set({ widgets });
      },
      addWidget: (widget: DashboardWidget) => {
        set({ widgets: [...get().widgets, widget] });
      },
      updateWidget: (id: string, updates: Partial<DashboardWidget>) => {
        const widgets = get().widgets.map(widget =>
          widget.id === id ? { ...widget, ...updates } : widget
        );
        set({ widgets });
      },
      removeWidget: (id: string) => {
        set({ widgets: get().widgets.filter(widget => widget.id !== id) });
      },

      // Market data state
      marketData: new Map(),
      setMarketData: (data: Map<string, MarketData>) => {
        set({ marketData: data });
      },
      updateMarketData: (symbol: string, data: MarketData) => {
        const marketData = new Map(get().marketData);
        marketData.set(symbol, data);
        set({ marketData });
      },

      // Alerts state
      alerts: [],
      setAlerts: (alerts: Alert[]) => {
        set({ alerts });
      },
      addAlert: (alert: Alert) => {
        set({ alerts: [alert, ...get().alerts] });
      },
      markAlertAsRead: (id: string) => {
        const alerts = get().alerts.map(alert =>
          alert.id === id ? { ...alert, read: true } : alert
        );
        set({ alerts });
      },
      removeAlert: (id: string) => {
        set({ alerts: get().alerts.filter(alert => alert.id !== id) });
      },

      // Loading states
      loading: {
        auth: false,
        trading: false,
        agents: false,
        workflows: false,
      },
      setLoading: (key: keyof AppState['loading'], value: boolean) => {
        set({
          loading: { ...get().loading, [key]: value }
        });
      },

      // Error states
      errors: {
        auth: null,
        trading: null,
        agents: null,
        workflows: null,
      },
      setError: (key: keyof AppState['errors'], error: string | null) => {
        set({
          errors: { ...get().errors, [key]: error }
        });
      },
    }),
    {
      name: 'asymedge-dashboard',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        theme: state.theme,
        widgets: state.widgets,
      }),
    }
  )
);