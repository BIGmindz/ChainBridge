// ═══════════════════════════════════════════════════════════════════════════════
// PAC-OCC-P20-BINDING — Cockpit Terminal Component
// Lane 9 (UX / GID-SONNY) Implementation
// Governance Tier: LAW
// Invariant: ARCHITECT_CONTROL | AGENT_OBSERVE | KILL_SWITCH_VISIBLE
// ═══════════════════════════════════════════════════════════════════════════════
/**
 * Cockpit Terminal Component
 * 
 * A secure terminal interface for the Senior Architect (Jeffrey) to control
 * the ChainBridge system. Uses xterm.js for terminal emulation with proper
 * WebSocket integration to the backend.
 * 
 * Security Model:
 * - Architect has full read/write access
 * - Agents have read-only observation
 * - Emergency KILL SESSION button always visible
 * - All connections require valid auth tokens
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import { WebLinksAddon } from '@xterm/addon-web-links';
import '@xterm/xterm/css/xterm.css';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface TerminalMessage {
  type: 'stdin' | 'stdout' | 'stderr' | 'control' | 'error';
  data: string;
  timestamp: string;
  gid?: string;
}

interface CockpitTerminalProps {
  /** Auth token for WebSocket connection */
  token: string;
  /** Agent GID (e.g., "GID-00" for Jeffrey) */
  gid: string;
  /** Whether this is an architect (write) or agent (read-only) connection */
  role: 'architect' | 'agent';
  /** WebSocket endpoint URL */
  wsUrl?: string;
  /** Callback when session is terminated */
  onSessionEnd?: (reason: string) => void;
  /** Callback for connection status changes */
  onConnectionChange?: (connected: boolean) => void;
}

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

// ═══════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const CockpitTerminal: React.FC<CockpitTerminalProps> = ({
  token,
  gid,
  role,
  wsUrl = `ws://${window.location.hostname}:8000/cockpit/ws`,
  onSessionEnd,
  onConnectionChange,
}) => {
  // Refs
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminalInstance = useRef<Terminal | null>(null);
  const fitAddon = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  
  // State
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [commandCount, setCommandCount] = useState(0);
  const [bytesTransferred, setBytesTransferred] = useState({ sent: 0, received: 0 });
  const [killConfirm, setKillConfirm] = useState(false);

  // ═══════════════════════════════════════════════════════════════════════════
  // TERMINAL INITIALIZATION
  // ═══════════════════════════════════════════════════════════════════════════

  useEffect(() => {
    if (!terminalRef.current) return;

    // Create terminal with ChainBridge theme
    const term = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
      fontSize: 14,
      lineHeight: 1.2,
      theme: {
        background: '#0a0a0a',
        foreground: '#e0e0e0',
        cursor: '#00ff00',
        cursorAccent: '#000000',
        selectionBackground: '#264f78',
        black: '#000000',
        red: '#ff5555',
        green: '#50fa7b',
        yellow: '#f1fa8c',
        blue: '#6272a4',
        magenta: '#ff79c6',
        cyan: '#8be9fd',
        white: '#f8f8f2',
        brightBlack: '#6272a4',
        brightRed: '#ff6e6e',
        brightGreen: '#69ff94',
        brightYellow: '#ffffa5',
        brightBlue: '#d6acff',
        brightMagenta: '#ff92df',
        brightCyan: '#a4ffff',
        brightWhite: '#ffffff',
      },
      allowProposedApi: true,
    });

    // Add addons
    const fit = new FitAddon();
    const webLinks = new WebLinksAddon();
    
    term.loadAddon(fit);
    term.loadAddon(webLinks);
    
    // Open terminal
    term.open(terminalRef.current);
    fit.fit();
    
    // Store refs
    terminalInstance.current = term;
    fitAddon.current = fit;

    // Welcome message
    term.writeln('\x1b[1;36m╔══════════════════════════════════════════════════════════════╗\x1b[0m');
    term.writeln('\x1b[1;36m║\x1b[0m     \x1b[1;33mCHAINBRIDGE COCKPIT TERMINAL\x1b[0m                            \x1b[1;36m║\x1b[0m');
    term.writeln('\x1b[1;36m║\x1b[0m     \x1b[1;32mv2.1.4-sovereign\x1b[0m                                        \x1b[1;36m║\x1b[0m');
    term.writeln('\x1b[1;36m╚══════════════════════════════════════════════════════════════╝\x1b[0m');
    term.writeln('');
    term.writeln(`\x1b[90mRole: ${role === 'architect' ? '\x1b[1;32mARCHITECT (READ/WRITE)' : '\x1b[1;33mAGENT (READ-ONLY)'}\x1b[0m`);
    term.writeln(`\x1b[90mGID:  ${gid}\x1b[0m`);
    term.writeln('');
    term.writeln('\x1b[90mConnecting to backend...\x1b[0m');

    // Handle window resize
    const handleResize = () => {
      if (fitAddon.current) {
        fitAddon.current.fit();
      }
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      term.dispose();
    };
  }, [gid, role]);

  // ═══════════════════════════════════════════════════════════════════════════
  // WEBSOCKET CONNECTION
  // ═══════════════════════════════════════════════════════════════════════════

  useEffect(() => {
    const term = terminalInstance.current;
    if (!term) return;

    // Build WebSocket URL with auth
    const fullUrl = `${wsUrl}?token=${encodeURIComponent(token)}&gid=${encodeURIComponent(gid)}`;
    
    setStatus('connecting');
    const ws = new WebSocket(fullUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      onConnectionChange?.(true);
      term.writeln('\x1b[1;32m✓ Connected to backend\x1b[0m');
      term.writeln('');
      
      if (role === 'architect') {
        term.writeln('\x1b[1;33m⚡ You have WRITE access. Type commands below.\x1b[0m');
        term.write('\x1b[1;32m❯\x1b[0m ');
      } else {
        term.writeln('\x1b[1;33m👁 You are observing. Read-only mode.\x1b[0m');
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg: TerminalMessage = JSON.parse(event.data);
        setBytesTransferred(prev => ({ ...prev, received: prev.received + event.data.length }));

        switch (msg.type) {
          case 'stdout':
            term.write(msg.data);
            break;
          case 'stderr':
            term.write(`\x1b[1;31m${msg.data}\x1b[0m`);
            break;
          case 'control':
            term.writeln(`\x1b[1;36m[SYSTEM]\x1b[0m ${msg.data}`);
            if (msg.data.includes('SESSION TERMINATED')) {
              onSessionEnd?.(msg.data);
            }
            if (msg.data.includes('session') && msg.data.includes('initialized')) {
              const match = msg.data.match(/cockpit-[a-f0-9]+/);
              if (match) setSessionId(match[0]);
            }
            break;
          case 'error':
            term.writeln(`\x1b[1;31m[ERROR]\x1b[0m ${msg.data}`);
            break;
          case 'stdin':
            // Echo from another source (if echo cancellation is off)
            if (msg.gid !== gid) {
              term.write(`\x1b[90m${msg.data}\x1b[0m`);
            }
            break;
        }
      } catch (e) {
        console.error('Failed to parse message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setStatus('error');
      term.writeln('\x1b[1;31m✗ Connection error\x1b[0m');
    };

    ws.onclose = (event) => {
      setStatus('disconnected');
      onConnectionChange?.(false);
      term.writeln('');
      term.writeln(`\x1b[1;33m⚠ Connection closed (code: ${event.code})\x1b[0m`);
      if (event.reason) {
        term.writeln(`\x1b[90mReason: ${event.reason}\x1b[0m`);
      }
    };

    // Handle terminal input (architect only)
    if (role === 'architect') {
      let inputBuffer = '';
      
      term.onData((data) => {
        if (ws.readyState !== WebSocket.OPEN) return;

        // Handle special keys
        if (data === '\r') {
          // Enter key - send command
          term.write('\r\n');
          
          const message: TerminalMessage = {
            type: 'stdin',
            data: inputBuffer + '\n',
            timestamp: new Date().toISOString(),
            gid,
          };
          
          ws.send(JSON.stringify(message));
          setBytesTransferred(prev => ({ ...prev, sent: prev.sent + inputBuffer.length }));
          setCommandCount(prev => prev + 1);
          
          inputBuffer = '';
          term.write('\x1b[1;32m❯\x1b[0m ');
          
        } else if (data === '\x7f') {
          // Backspace
          if (inputBuffer.length > 0) {
            inputBuffer = inputBuffer.slice(0, -1);
            term.write('\b \b');
          }
        } else if (data === '\x03') {
          // Ctrl+C
          term.write('^C\r\n');
          inputBuffer = '';
          term.write('\x1b[1;32m❯\x1b[0m ');
        } else if (data >= ' ' || data === '\t') {
          // Printable characters
          inputBuffer += data;
          term.write(data);
        }
      });
    }

    return () => {
      ws.close();
    };
  }, [token, gid, role, wsUrl, onConnectionChange, onSessionEnd]);

  // ═══════════════════════════════════════════════════════════════════════════
  // KILL SESSION HANDLER
  // ═══════════════════════════════════════════════════════════════════════════

  const handleKillSession = useCallback(async () => {
    if (!killConfirm) {
      setKillConfirm(true);
      setTimeout(() => setKillConfirm(false), 3000);
      return;
    }

    // Send kill command via WebSocket
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message: TerminalMessage = {
        type: 'control',
        data: 'KILL_SESSION',
        timestamp: new Date().toISOString(),
        gid,
      };
      wsRef.current.send(JSON.stringify(message));
    }

    // Also hit the REST endpoint as backup
    try {
      await fetch(`http://${window.location.hostname}:8000/cockpit/kill?gid=${gid}&reason=UI%20Kill%20Switch`, {
        method: 'POST',
      });
    } catch (e) {
      console.error('Kill request failed:', e);
    }

    setKillConfirm(false);
  }, [killConfirm, gid]);

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════════

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] rounded-lg overflow-hidden border border-gray-800">
      {/* Header Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#1a1a1a] border-b border-gray-800">
        <div className="flex items-center gap-4">
          {/* Traffic lights */}
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          
          {/* Title */}
          <span className="text-sm font-mono text-gray-400">
            COCKPIT TERMINAL
            {sessionId && <span className="text-gray-600 ml-2">({sessionId})</span>}
          </span>
        </div>

        <div className="flex items-center gap-4">
          {/* Status indicators */}
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className={`px-2 py-0.5 rounded ${
              status === 'connected' ? 'bg-green-900 text-green-300' :
              status === 'connecting' ? 'bg-yellow-900 text-yellow-300' :
              status === 'error' ? 'bg-red-900 text-red-300' :
              'bg-gray-800 text-gray-400'
            }`}>
              {status.toUpperCase()}
            </span>
            
            <span className={`px-2 py-0.5 rounded ${
              role === 'architect' ? 'bg-blue-900 text-blue-300' : 'bg-purple-900 text-purple-300'
            }`}>
              {role === 'architect' ? 'WRITE' : 'READ-ONLY'}
            </span>
          </div>

          {/* Stats */}
          <div className="text-xs font-mono text-gray-500">
            <span className="mr-3">CMD: {commandCount}</span>
            <span>↑{bytesTransferred.sent}B ↓{bytesTransferred.received}B</span>
          </div>

          {/* KILL SESSION BUTTON - Always visible */}
          <button
            onClick={handleKillSession}
            className={`px-3 py-1 text-xs font-bold rounded transition-all ${
              killConfirm
                ? 'bg-red-600 text-white animate-pulse'
                : 'bg-red-900 text-red-300 hover:bg-red-700'
            }`}
          >
            {killConfirm ? '⚠ CONFIRM KILL?' : '🛑 KILL SESSION'}
          </button>
        </div>
      </div>

      {/* Terminal Container */}
      <div 
        ref={terminalRef} 
        className="flex-1 p-2"
        style={{ minHeight: '400px' }}
      />

      {/* Footer */}
      <div className="px-4 py-1 bg-[#1a1a1a] border-t border-gray-800 text-xs font-mono text-gray-600">
        <span className="text-gray-500">{gid}</span>
        <span className="mx-2">|</span>
        <span>ChainBridge v2.1.4-sovereign</span>
        <span className="mx-2">|</span>
        <span>P21 Friction: {role === 'architect' ? 'ENFORCED' : 'N/A'}</span>
      </div>
    </div>
  );
};

export default CockpitTerminal;
