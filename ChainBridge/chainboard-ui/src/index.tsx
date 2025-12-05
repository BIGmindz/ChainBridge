import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import 'mapbox-gl/dist/mapbox-gl.css';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { CommandPalette } from './components/CommandPalette';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastContainer } from './components/ToastContainer';
import { useCommandPalette } from './core/command/hooks';
import { DemoProvider } from './core/demo/DemoContext';
import { NotificationProvider } from './core/notifications/NotificationContext';
import './index.css';
import { AppRoutes } from './routes';
import { registerBackendSyncHook } from '@/ai/weightSync';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

function App() {
  const { open, toggle, items } = useCommandPalette();

  return (
    <BrowserRouter>
      <AppRoutes />
      <ToastContainer />
      <CommandPalette open={open} onClose={() => toggle(false)} items={items} />
    </BrowserRouter>
  );
}

registerBackendSyncHook(async (payload) => {
  try {
    await fetch('/api/ai/presets/analytics/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.warn('[AI Analytics] Failed to sync to backend', err);
  }
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <NotificationProvider>
        <DemoProvider>
          <QueryClientProvider client={queryClient}>
            <App />
            {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
          </QueryClientProvider>
        </DemoProvider>
      </NotificationProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
