# ASYMEdge Dashboard

A modern, AI-powered trading dashboard built with React, TypeScript, and real-time WebSocket connections. Features advanced agent management with Letta integration, workflow visualization using LangGraph, and comprehensive trading analytics.

## 🚀 Features

### Core Functionality
- **Real-time Trading Dashboard** - Live portfolio monitoring with interactive charts
- **AI Agent Management** - Integrated Letta agent deployment and monitoring
- **Workflow Visualization** - LangGraph-powered workflow designer and executor
- **Advanced Analytics** - Performance metrics, risk analysis, and reporting
- **Market Data Integration** - Real-time price feeds and market indicators

### Technical Features
- **Modern React Architecture** - Built with React 18, TypeScript, and Vite
- **Real-time Updates** - WebSocket integration for live data streaming
- **Responsive Design** - Mobile-first approach with Tailwind CSS
- **State Management** - Zustand for efficient global state handling
- **Data Visualization** - Recharts for interactive trading charts
- **Role-based Access Control** - User authentication and permission system

### Dashboard Components
- **Portfolio Overview** - Real-time P&L, portfolio value, and performance metrics
- **Trading Interface** - Order placement, position management, and market data
- **Agent Management** - Create, monitor, and manage AI trading agents
- **Workflow Builder** - Visual workflow designer with node-based execution
- **Market Analysis** - Real-time market data and sentiment analysis
- **Alert System** - Comprehensive notification and alert management

## 🛠 Technology Stack

### Frontend
- **React 18** - Modern React with hooks and concurrent features
- **TypeScript** - Type-safe development with strict configuration
- **Vite** - Fast build tool and development server
- **Tailwind CSS** - Utility-first CSS framework
- **Recharts** - React charting library for data visualization

### State Management & Data
- **Zustand** - Lightweight state management
- **TanStack Query** - Server state management and caching
- **WebSocket** - Real-time data streaming

### UI Components
- **Radix UI** - Accessible component primitives
- **Lucide React** - Beautiful icon library
- **React Hot Toast** - Notification system
- **Framer Motion** - Smooth animations

### Development Tools
- **ESLint** - Code linting and formatting
- **TypeScript** - Static type checking
- **Vite Plugin Source Identifier** - Development debugging

## 📦 Installation

### Prerequisites
- Node.js 18+ 
- pnpm (recommended) or npm

### Setup

1. **Clone and Install**
```bash
cd frontend/asymedge-dashboard
pnpm install
```

2. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Development Server**
```bash
pnpm dev
```

4. **Build for Production**
```bash
pnpm build
```

5. **Preview Production Build**
```bash
pnpm preview
```

## 🔧 Configuration

### Environment Variables

```env
# API Configuration
VITE_API_URL=http://localhost:3000
VITE_WS_URL=ws://localhost:3001

# Application Settings
VITE_APP_NAME=ASYMEdge Dashboard
VITE_ENVIRONMENT=development

# Feature Flags
VITE_ENABLE_WEBSOCKET=true
VITE_ENABLE_REAL_TIME=true
VITE_ENABLE_NOTIFICATIONS=true
```

### Key Configurations

#### WebSocket Connection
```typescript
// src/config/app.ts
websocket: {
  url: process.env.VITE_WS_URL || 'ws://localhost:3001',
  reconnectInterval: 5000,
  maxReconnectAttempts: 10
}
```

#### API Endpoints
```typescript
// src/config/app.ts
api: {
  baseUrl: process.env.VITE_API_URL || 'http://localhost:3000',
  timeout: 30000
}
```

## 🏗 Project Structure

```
src/
├── components/           # React components
│   ├── auth/            # Authentication components
│   ├── dashboard/       # Dashboard widgets and layouts
│   ├── trading/         # Trading interface components
│   ├── agents/          # Agent management components
│   ├── workflows/       # Workflow visualization
│   ├── layout/          # Layout components (Header, Sidebar)
│   └── ui/              # Reusable UI components
├── store/               # Zustand state management
├── services/            # API services and WebSocket
├── types/               # TypeScript type definitions
├── config/              # Application configuration
├── hooks/               # Custom React hooks
└── lib/                 # Utility functions
```

## 🚀 Usage

### Dashboard Navigation
- **Dashboard** - Main overview with key metrics
- **Trading** - Trading interface and order management
- **Agents** - AI agent creation and monitoring
- **Workflows** - Workflow design and execution
- **Analytics** - Advanced performance analytics
- **Market Data** - Real-time market information

### Agent Management
1. Navigate to **Agents** section
2. Click **Create Agent** to add new agents
3. Configure agent parameters and deployment
4. Monitor agent performance and status

### Workflow Creation
1. Go to **Workflows** section
2. Select template or create custom workflow
3. Design workflow using visual interface
4. Execute and monitor workflow progress

### Trading Operations
1. Access **Trading** dashboard
2. Select trading instruments
3. Place orders using intuitive interface
4. Monitor positions and P&L in real-time

## 🔌 API Integration

### WebSocket Events
```typescript
// Real-time trading updates
wsService.subscribe('trading_update', (data) => {
  // Handle trading data updates
});

// Agent status changes
wsService.subscribe('agent_update', (data) => {
  // Handle agent status updates
});

// Workflow progress
wsService.subscribe('workflow_update', (data) => {
  // Handle workflow updates
});
```

### HTTP API Endpoints
```typescript
// Trading operations
GET /api/trading/positions
POST /api/trading/orders
GET /api/trading/metrics

// Agent management
GET /api/agents
POST /api/agents
PUT /api/agents/:id

// Workflow operations
GET /api/workflows
POST /api/workflows
PUT /api/workflows/:id
```

## 🎨 Theming & Customization

### Dark Mode Support
The dashboard supports both light and dark themes with automatic system preference detection.

### Custom Themes
```typescript
// src/store/index.ts
const { setTheme } = useAppStore();
setTheme({
  mode: 'dark',
  primaryColor: '#3b82f6',
  secondaryColor: '#6b7280'
});
```

### Widget Customization
- Drag and drop dashboard widgets
- Resize components dynamically
- Save custom layouts per user

## 📊 Performance Monitoring

### Real-time Metrics
- Portfolio performance tracking
- Agent success rates and execution times
- Workflow completion rates
- System resource utilization

### Analytics Dashboard
- Historical performance analysis
- Risk metrics and drawdown tracking
- Trading strategy effectiveness
- Agent performance comparison

## 🔒 Security Features

### Authentication
- JWT-based authentication
- Role-based access control
- Session management
- Secure API communication

### Data Protection
- Input validation and sanitization
- XSS protection
- CSRF prevention
- Secure WebSocket connections

## 🚀 Deployment

### Build Optimization
```bash
# Production build with optimizations
pnpm build

# Analyze bundle size
pnpm build --analyze
```

### Environment-specific Builds
```bash
# Development
pnpm build:dev

# Staging
pnpm build:staging

# Production
pnpm build:prod
```

### Docker Support
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

## 🧪 Testing

### Unit Testing
```bash
pnpm test
```

### E2E Testing
```bash
pnpm test:e2e
```

### Coverage Reports
```bash
pnpm test:coverage
```

## 📚 Documentation

### Component Documentation
- Individual component README files
- TypeScript interface documentation
- Storybook integration (planned)

### API Documentation
- OpenAPI/Swagger specifications
- WebSocket event documentation
- Integration guides

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Development Guidelines
- Follow TypeScript strict mode
- Use conventional commit messages
- Maintain test coverage above 80%
- Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.asymedge.com](https://docs.asymedge.com)
- **Issues**: [GitHub Issues](https://github.com/asymedge/dashboard/issues)
- **Discussions**: [GitHub Discussions](https://github.com/asymedge/dashboard/discussions)
- **Email**: support@asymedge.com

## 🗺 Roadmap

### Short Term (Q1 2024)
- [ ] Advanced charting with TradingView integration
- [ ] Mobile app development
- [ ] Enhanced agent marketplace
- [ ] Multi-exchange trading support

### Medium Term (Q2-Q3 2024)
- [ ] Machine learning model integration
- [ ] Advanced risk management tools
- [ ] Social trading features
- [ ] API marketplace

### Long Term (Q4 2024+)
- [ ] Decentralized trading integration
- [ ] Quantum computing optimization
- [ ] Advanced AI agent training
- [ ] Global market expansion

---

**ASYMEdge Dashboard** - Empowering AI-driven trading decisions with real-time insights and intelligent automation.
