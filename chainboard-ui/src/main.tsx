// ═══════════════════════════════════════════════════════════════════════════════
// ChainBoard Main Entry Point
// PAC-BENSON-P20-B: Frontend Hardening — Root-level error handling (SONNY GID-02)
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { ErrorBoundary } from './components/ErrorBoundary';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
