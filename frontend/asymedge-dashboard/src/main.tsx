import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { ErrorBoundary } from './components/ErrorBoundary.tsx'
import { initializeMockData, startRealTimeSimulation } from './config/app.ts'
import { useWebSocket } from './services/websocket.ts'
import './index.css'
import App from './App.tsx'

// Initialize mock data on app start
initializeMockData();

// Start real-time data simulation
const cleanupSimulation = startRealTimeSimulation();

// Initialize WebSocket connection (optional)
const ws = useWebSocket();
ws.connect();

// Cleanup function for unmount
const cleanup = () => {
  cleanupSimulation();
  ws.disconnect();
};

// Make cleanup available globally for development
if (typeof window !== 'undefined') {
  (window as any).cleanupApp = cleanup;
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
