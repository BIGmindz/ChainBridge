// ═══════════════════════════════════════════════════════════════════════════════
// ChainBoard Application Root
// PAC-JEFFREY-P19R: Added ChainTrust route (Sonny GID-02)
// PAC-BENSON-P20-B: Frontend hardening — ErrorBoundary + Accessibility (SONNY/LIRA)
// PAC-BENSON-P35R: Added Demo Experience route (SONNY GID-02)
// PAC-BENSON-P42: Added OCC Dashboard route (SONNY GID-02)
// ═══════════════════════════════════════════════════════════════════════════════

import React, { useState, useCallback } from 'react';
import OperatorConsole from './routes/OperatorConsole';
import ChainTrust from './routes/ChainTrust';
import OCCDashboard from './routes/OCCDashboard';
import { ErrorBoundary } from './components/ErrorBoundary';
import { DemoExperienceDashboard } from './components/demo';

type AppRoute = 'console' | 'chaintrust' | 'occ' | 'demo';

/**
 * Navigation header for switching between views.
 * PAC-BENSON-P20-B: Added ARIA labels and keyboard navigation (LIRA GID-09)
 * PAC-BENSON-P35R: Added Demo route (SONNY GID-02)
 */
const AppNav: React.FC<{ currentRoute: AppRoute; onNavigate: (route: AppRoute) => void }> = ({
  currentRoute,
  onNavigate,
}) => {
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, route: AppRoute) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onNavigate(route);
      }
    },
    [onNavigate]
  );

  return (
    <nav
      className="bg-gray-900 border-b border-gray-700 px-6 py-3"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="flex items-center gap-6">
        <span className="text-lg font-bold text-white" aria-hidden="true">
          ChainBoard
        </span>
        <h1 className="sr-only">ChainBoard Application</h1>
        <div className="flex gap-2" role="tablist" aria-label="Application views">
          <button
            onClick={() => onNavigate('console')}
            onKeyDown={(e) => handleKeyDown(e, 'console')}
            role="tab"
            aria-selected={currentRoute === 'console'}
            aria-controls="console-panel"
            tabIndex={currentRoute === 'console' ? 0 : -1}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 ${
              currentRoute === 'console'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Operator Console
          </button>
          <button
            onClick={() => onNavigate('chaintrust')}
            onKeyDown={(e) => handleKeyDown(e, 'chaintrust')}
            role="tab"
            aria-selected={currentRoute === 'chaintrust'}
            aria-controls="chaintrust-panel"
            tabIndex={currentRoute === 'chaintrust' ? 0 : -1}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 ${
              currentRoute === 'chaintrust'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            ChainTrust
          </button>
          <button
            onClick={() => onNavigate('occ')}
            onKeyDown={(e) => handleKeyDown(e, 'occ')}
            role="tab"
            aria-selected={currentRoute === 'occ'}
            aria-controls="occ-panel"
            tabIndex={currentRoute === 'occ' ? 0 : -1}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-gray-900 ${
              currentRoute === 'occ'
                ? 'bg-red-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            ⚙️ OCC
          </button>
          <button
            onClick={() => onNavigate('demo')}
            onKeyDown={(e) => handleKeyDown(e, 'demo')}
            role="tab"
            aria-selected={currentRoute === 'demo'}
            aria-controls="demo-panel"
            tabIndex={currentRoute === 'demo' ? 0 : -1}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:ring-offset-gray-900 ${
              currentRoute === 'demo'
                ? 'bg-green-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            🎬 Demo
          </button>
        </div>
      </div>
    </nav>
  );
};

/**
 * Main App component with ErrorBoundary wrapping.
 * PAC-BENSON-P20-B: Global error handling (SONNY GID-02)
 * PAC-BENSON-P35R: Demo Experience route (SONNY GID-02)
 */
const App: React.FC = () => {
  const [route, setRoute] = useState<AppRoute>('console');

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-950">
        <AppNav currentRoute={route} onNavigate={setRoute} />
        <main>
          <div
            id="console-panel"
            role="tabpanel"
            aria-labelledby="console-tab"
            hidden={route !== 'console'}
          >
            {route === 'console' && <OperatorConsole />}
          </div>
          <div
            id="chaintrust-panel"
            role="tabpanel"
            aria-labelledby="chaintrust-tab"
            hidden={route !== 'chaintrust'}
          >
            {route === 'chaintrust' && <ChainTrust />}
          </div>
          <div
            id="occ-panel"
            role="tabpanel"
            aria-labelledby="occ-tab"
            hidden={route !== 'occ'}
          >
            {route === 'occ' && <OCCDashboard />}
          </div>
          <div
            id="demo-panel"
            role="tabpanel"
            aria-labelledby="demo-tab"
            hidden={route !== 'demo'}
          >
            {route === 'demo' && <DemoExperienceDashboard />}
          </div>
        </main>
      </div>
    </ErrorBoundary>
  );
};

export default App;
