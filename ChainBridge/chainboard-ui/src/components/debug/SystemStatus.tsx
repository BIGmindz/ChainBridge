import { useEffect, useState } from 'react';

export const SystemStatus = () => {
  const [status, setStatus] = useState<'connected' | 'disconnected' | 'latency'>('disconnected');
  const [latency, setLatency] = useState<number>(0);

  useEffect(() => {
    const checkStatus = async () => {
      const start = Date.now();
      try {
        // Attempt to hit the backend API root or health check
        // Assuming backend is on port 8000 for local dev, or proxied via /api
        // Adjust URL as needed for the specific environment
        const response = await fetch('http://localhost:8000/', {
          method: 'GET',
          signal: AbortSignal.timeout(2000),
        });
        const end = Date.now();
        const duration = end - start;

        if (response.ok) {
          if (duration > 500) {
            setStatus('latency');
          } else {
            setStatus('connected');
          }
        } else {
          setStatus('disconnected');
        }
        setLatency(duration);
      } catch {
        setStatus('disconnected');
      }
    };

    // Check immediately and then every 5 seconds
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const getColor = () => {
    switch (status) {
      case 'connected':
        return 'bg-emerald-500';
      case 'latency':
        return 'bg-yellow-500';
      case 'disconnected':
        return 'bg-red-500';
      default:
        return 'bg-slate-500';
    }
  };

  const getLabel = () => {
    switch (status) {
      case 'connected':
        return 'SYSTEM ONLINE';
      case 'latency':
        return `HIGH LATENCY (${latency}ms)`;
      case 'disconnected':
        return 'CONNECTION LOST';
      default:
        return 'OFFLINE';
    }
  };

  return (
    <div className="fixed bottom-4 left-4 z-50 flex items-center gap-3 pointer-events-none select-none">
      <div className="relative flex h-3 w-3">
        {status === 'connected' && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
        )}
        {status === 'disconnected' && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
        )}
        <span className={`relative inline-flex rounded-full h-3 w-3 ${getColor()}`}></span>
      </div>
      <div
        className={`text-[10px] font-mono font-bold tracking-widest ${
          status === 'disconnected' ? 'text-red-500' : 'text-slate-500'
        }`}
      >
        {getLabel()}
      </div>
    </div>
  );
};
