/**
 * OCC (Operator Control Center) Dashboard
 * 
 * PAC Reference: PAC-BENSON-P42 — OCC Operationalization
 * PAC Reference: PAC-OCC-P23 — Grand Unification (God-View)
 * Agent: SONNY (GID-02) — UI
 * Effective Date: 2026-01-02
 * 
 * This is the real-time operator control interface for:
 *   - Agent state monitoring
 *   - PDO visibility (Shadow vs Production)
 *   - Kill-switch control
 *   - Operator authentication
 *   - God-View system status (P23)
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  getOCCHealth,
  getAgentStates,
  getPDOList,
  getKillSwitchStatus,
  armKillSwitch,
  engageKillSwitch,
  disengageKillSwitch,
  disarmKillSwitch,
  operatorLogin,
  operatorLogout,
  getCurrentSession,
  getGodView,
  type AgentStateResponse,
  type PDOSummary,
  type KillSwitchStatusResponse,
  type OperatorSession,
  type OCCHealthResponse,
  type GodViewResponse,
  OCCAPIError,
} from '../api/occApi';

// ═══════════════════════════════════════════════════════════════════════════════
// GOD-VIEW COMPONENT (PAC-OCC-P23)
// ═══════════════════════════════════════════════════════════════════════════════

const GodView: React.FC<{ data: GodViewResponse | null; loading: boolean }> = ({ data, loading }) => {
  if (loading) return <div className="text-gray-400 text-center py-4">Loading system status...</div>;
  if (!data) return <div className="text-red-400 text-center py-4">System status unavailable</div>;

  const isKilled = data.system_status === 'KILLED';

  return (
    <div className={`rounded-lg p-6 mb-6 border-2 ${
      isKilled 
        ? 'bg-red-950 border-red-600' 
        : 'bg-green-950 border-green-600'
    }`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className={`text-4xl ${isKilled ? 'animate-pulse' : ''}`}>
            {isKilled ? '🔴' : '🟢'}
          </div>
          <div>
            <h2 className={`text-2xl font-bold ${isKilled ? 'text-red-400' : 'text-green-400'}`}>
              SYSTEM {data.system_status}
            </h2>
            <p className="text-gray-400 text-sm">
              {isKilled ? 'KILL_SWITCH.lock is active — All agents halted' : 'System operating normally'}
            </p>
          </div>
        </div>
        
        <div className="flex gap-6 text-center">
          <div>
            <div className="text-3xl font-bold text-white">{data.active_agents}</div>
            <div className="text-xs text-gray-400 uppercase">Active Agents</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-400">{data.active_policies.length}</div>
            <div className="text-xs text-gray-400 uppercase">Loaded Policies</div>
          </div>
        </div>
      </div>

      {data.active_policies.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-700">
          <div className="text-xs text-gray-500 uppercase mb-2">ChainDocs Policies</div>
          <div className="flex flex-wrap gap-2">
            {data.active_policies.map((policy) => (
              <span 
                key={policy.name}
                className="px-2 py-1 bg-gray-800 rounded text-xs text-gray-300 font-mono"
                title={`Hash: ${policy.full_hash}`}
              >
                [{policy.name}:{policy.hash}]
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 text-right text-xs text-gray-500">
        Last updated: {new Date(data.timestamp).toLocaleTimeString()}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// HEALTH STATUS COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const HealthStatus: React.FC<{ health: OCCHealthResponse | null; loading: boolean }> = ({ health, loading }) => {
  if (loading) return <div className="text-gray-400">Loading health...</div>;
  if (!health) return <div className="text-red-400">Health check failed</div>;

  const statusColor = health.status === 'ok' ? 'text-green-400' : 
                      health.status === 'degraded' ? 'text-yellow-400' : 'text-red-400';

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-300 mb-2">System Health</h3>
      <div className={`text-lg font-bold ${statusColor} uppercase`}>{health.status}</div>
      <div className="grid grid-cols-2 gap-2 mt-2 text-xs">
        {Object.entries(health.components).map(([key, value]) => (
          <div key={key} className="flex items-center gap-1">
            <span className={value ? 'text-green-400' : 'text-red-400'}>●</span>
            <span className="text-gray-400">{key.replace('_', ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// AGENT GRID COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const AgentGrid: React.FC<{ agents: AgentStateResponse[]; loading: boolean }> = ({ agents, loading }) => {
  if (loading) return <div className="text-gray-400">Loading agents...</div>;

  const healthColor = (health: string) => {
    switch (health) {
      case 'HEALTHY': return 'bg-green-500';
      case 'DEGRADED': return 'bg-yellow-500';
      case 'CRITICAL': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const stateColor = (state: string) => {
    switch (state) {
      case 'ACTIVE': return 'text-green-400';
      case 'IDLE': return 'text-blue-400';
      case 'SUSPENDED': return 'text-yellow-400';
      case 'TERMINATED': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Agent States</h3>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
        {agents.map((agent) => (
          <div
            key={agent.gid}
            className="bg-gray-900 rounded p-2 border border-gray-700"
          >
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${healthColor(agent.health)}`} />
              <span className="text-white font-mono text-sm">{agent.gid}</span>
            </div>
            <div className="text-xs text-gray-400 mt-1">{agent.name}</div>
            <div className={`text-xs ${stateColor(agent.state)}`}>{agent.state}</div>
            {agent.current_pac && (
              <div className="text-xs text-purple-400 truncate mt-1">
                PAC: {agent.current_pac}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// PDO LIST COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const PDOList: React.FC<{ 
  pdos: PDOSummary[]; 
  loading: boolean;
  filter: 'all' | 'shadow' | 'production';
  onFilterChange: (filter: 'all' | 'shadow' | 'production') => void;
}> = ({ pdos, loading, filter, onFilterChange }) => {
  const classificationColor = (classification: string) => {
    return classification === 'shadow' ? 'bg-purple-600' : 'bg-green-600';
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-300">PDO Records</h3>
        <select
          value={filter}
          onChange={(e) => onFilterChange(e.target.value as typeof filter)}
          className="bg-gray-700 text-white text-xs rounded px-2 py-1 border border-gray-600"
        >
          <option value="all">All</option>
          <option value="shadow">Shadow Only</option>
          <option value="production">Production Only</option>
        </select>
      </div>
      {loading ? (
        <div className="text-gray-400">Loading PDOs...</div>
      ) : pdos.length === 0 ? (
        <div className="text-gray-500 text-sm">No PDOs found</div>
      ) : (
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {pdos.map((pdo) => (
            <div
              key={pdo.pdo_id}
              className="bg-gray-900 rounded p-2 border border-gray-700 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-gray-300 truncate max-w-[60%]">
                  {pdo.pdo_id.substring(0, 8)}...
                </span>
                <span className={`px-2 py-0.5 rounded text-white ${classificationColor(pdo.classification)}`}>
                  {pdo.classification.toUpperCase()}
                </span>
              </div>
              <div className="flex justify-between mt-1 text-gray-500">
                <span>{pdo.outcome}</span>
                <span>{pdo.source_system}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// KILL SWITCH COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const KillSwitchPanel: React.FC<{
  status: KillSwitchStatusResponse | null;
  loading: boolean;
  session: OperatorSession | null;
  onArm: () => void;
  onEngage: (reason: string) => void;
  onDisengage: () => void;
  onDisarm: () => void;
}> = ({ status, loading, session, onArm, onEngage, onDisengage, onDisarm }) => {
  const [engageReason, setEngageReason] = useState('');
  const [showEngageForm, setShowEngageForm] = useState(false);

  if (loading) return <div className="text-gray-400">Loading kill switch...</div>;
  if (!status) return <div className="text-red-400">Kill switch status unavailable</div>;

  const stateColor = {
    DISARMED: 'bg-green-600',
    ARMED: 'bg-yellow-600',
    ENGAGED: 'bg-red-600',
    COOLDOWN: 'bg-blue-600',
  }[status.state] || 'bg-gray-600';

  const canOperate = session && session.permissions.includes('KILL_SWITCH_CONTROL');

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Kill Switch Control</h3>
      
      <div className="flex items-center gap-3 mb-4">
        <div className={`px-4 py-2 rounded font-bold text-white ${stateColor}`}>
          {status.state}
        </div>
        {status.reason && (
          <span className="text-gray-400 text-sm truncate">
            Reason: {status.reason}
          </span>
        )}
      </div>

      {!canOperate && (
        <div className="text-yellow-400 text-xs mb-3">
          ⚠️ Login required for kill switch operations
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {status.state === 'DISARMED' && (
          <button
            onClick={onArm}
            disabled={!canOperate}
            className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
          >
            ARM
          </button>
        )}
        
        {status.state === 'ARMED' && (
          <>
            {showEngageForm ? (
              <div className="flex items-center gap-2 w-full">
                <input
                  type="text"
                  value={engageReason}
                  onChange={(e) => setEngageReason(e.target.value)}
                  placeholder="Reason for engagement..."
                  className="flex-1 bg-gray-700 text-white text-sm rounded px-2 py-1 border border-gray-600"
                />
                <button
                  onClick={() => {
                    if (engageReason.trim()) {
                      onEngage(engageReason);
                      setEngageReason('');
                      setShowEngageForm(false);
                    }
                  }}
                  disabled={!engageReason.trim()}
                  className="px-3 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 text-white text-sm rounded transition-colors"
                >
                  CONFIRM ENGAGE
                </button>
                <button
                  onClick={() => setShowEngageForm(false)}
                  className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded transition-colors"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <>
                <button
                  onClick={() => setShowEngageForm(true)}
                  disabled={!canOperate}
                  className="px-3 py-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
                >
                  ENGAGE
                </button>
                <button
                  onClick={onDisarm}
                  disabled={!canOperate}
                  className="px-3 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
                >
                  DISARM
                </button>
              </>
            )}
          </>
        )}
        
        {status.state === 'ENGAGED' && (
          <button
            onClick={onDisengage}
            disabled={!canOperate}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
          >
            DISENGAGE
          </button>
        )}
        
        {status.state === 'COOLDOWN' && (
          <div className="text-blue-400 text-sm">
            Cooldown until: {status.cooldown_until}
          </div>
        )}
      </div>

      {status.affected_agents.length > 0 && (
        <div className="mt-3 text-xs text-red-400">
          Affected agents: {status.affected_agents.join(', ')}
        </div>
      )}
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// LOGIN PANEL COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const LoginPanel: React.FC<{
  session: OperatorSession | null;
  onLogin: (operatorId: string, password: string) => void;
  onLogout: () => void;
  error: string | null;
}> = ({ session, onLogin, onLogout, error }) => {
  const [operatorId, setOperatorId] = useState('');
  const [password, setPassword] = useState('');

  if (session) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <h3 className="text-sm font-semibold text-gray-300 mb-2">Operator Session</h3>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-white font-medium">{session.operator_name}</div>
            <div className="text-xs text-purple-400">{session.mode}</div>
            <div className="text-xs text-gray-500">
              Expires: {new Date(session.expires_at).toLocaleTimeString()}
            </div>
          </div>
          <button
            onClick={onLogout}
            className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">Operator Login</h3>
      {error && (
        <div className="text-red-400 text-xs mb-2">{error}</div>
      )}
      <div className="space-y-2">
        <input
          type="text"
          value={operatorId}
          onChange={(e) => setOperatorId(e.target.value)}
          placeholder="Operator ID"
          className="w-full bg-gray-700 text-white text-sm rounded px-3 py-2 border border-gray-600"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="w-full bg-gray-700 text-white text-sm rounded px-3 py-2 border border-gray-600"
        />
        <button
          onClick={() => {
            if (operatorId && password) {
              onLogin(operatorId, password);
            }
          }}
          disabled={!operatorId || !password}
          className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
        >
          Login (JEFFREY_INTERNAL)
        </button>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN OCC DASHBOARD COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

const OCCDashboard: React.FC = () => {
  // State
  const [godView, setGodView] = useState<GodViewResponse | null>(null);
  const [health, setHealth] = useState<OCCHealthResponse | null>(null);
  const [agents, setAgents] = useState<AgentStateResponse[]>([]);
  const [pdos, setPdos] = useState<PDOSummary[]>([]);
  const [killSwitch, setKillSwitch] = useState<KillSwitchStatusResponse | null>(null);
  const [session, setSession] = useState<OperatorSession | null>(null);
  
  const [pdoFilter, setPdoFilter] = useState<'all' | 'shadow' | 'production'>('all');
  const [loginError, setLoginError] = useState<string | null>(null);
  
  const [loadingGodView, setLoadingGodView] = useState(true);
  const [loadingHealth, setLoadingHealth] = useState(true);
  const [loadingAgents, setLoadingAgents] = useState(true);
  const [loadingPdos, setLoadingPdos] = useState(true);
  const [loadingKillSwitch, setLoadingKillSwitch] = useState(true);

  // Load God-View (PAC-OCC-P23)
  const loadGodView = useCallback(async () => {
    try {
      setLoadingGodView(true);
      const data = await getGodView();
      setGodView(data);
    } catch (e) {
      console.error('Failed to load God-View:', e);
    } finally {
      setLoadingGodView(false);
    }
  }, []);

  // Load data
  const loadHealth = useCallback(async () => {
    try {
      setLoadingHealth(true);
      const data = await getOCCHealth();
      setHealth(data);
    } catch (e) {
      console.error('Failed to load health:', e);
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  const loadAgents = useCallback(async () => {
    try {
      setLoadingAgents(true);
      const data = await getAgentStates();
      setAgents(data);
    } catch (e) {
      console.error('Failed to load agents:', e);
    } finally {
      setLoadingAgents(false);
    }
  }, []);

  const loadPdos = useCallback(async () => {
    try {
      setLoadingPdos(true);
      const classification = pdoFilter === 'all' ? undefined : pdoFilter;
      const data = await getPDOList(0, 50, classification);
      setPdos(data.pdos);
    } catch (e) {
      console.error('Failed to load PDOs:', e);
    } finally {
      setLoadingPdos(false);
    }
  }, [pdoFilter]);

  const loadKillSwitch = useCallback(async () => {
    try {
      setLoadingKillSwitch(true);
      const data = await getKillSwitchStatus();
      setKillSwitch(data);
    } catch (e) {
      console.error('Failed to load kill switch:', e);
    } finally {
      setLoadingKillSwitch(false);
    }
  }, []);

  const loadSession = useCallback(async () => {
    try {
      const data = await getCurrentSession();
      setSession(data);
    } catch (e) {
      console.error('Failed to load session:', e);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadGodView();
    loadHealth();
    loadAgents();
    loadPdos();
    loadKillSwitch();
    loadSession();
  }, [loadGodView, loadHealth, loadAgents, loadPdos, loadKillSwitch, loadSession]);

  // Reload PDOs when filter changes
  useEffect(() => {
    loadPdos();
  }, [loadPdos, pdoFilter]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      loadGodView();
      loadHealth();
      loadAgents();
      loadKillSwitch();
    }, 5000);
    return () => clearInterval(interval);
  }, [loadGodView, loadHealth, loadAgents, loadKillSwitch]);

  // Handlers
  const handleLogin = async (operatorId: string, password: string) => {
    try {
      setLoginError(null);
      const sess = await operatorLogin(operatorId, password);
      setSession(sess);
    } catch (e) {
      if (e instanceof OCCAPIError) {
        setLoginError(e.message);
      } else {
        setLoginError('Login failed');
      }
    }
  };

  const handleLogout = async () => {
    try {
      await operatorLogout();
      setSession(null);
    } catch (e) {
      console.error('Logout failed:', e);
    }
  };

  const handleArm = async () => {
    try {
      const status = await armKillSwitch('Manual arm from OCC Dashboard');
      setKillSwitch(status);
    } catch (e) {
      console.error('Arm failed:', e);
    }
  };

  const handleEngage = async (reason: string) => {
    try {
      const status = await engageKillSwitch(reason);
      setKillSwitch(status);
    } catch (e) {
      console.error('Engage failed:', e);
    }
  };

  const handleDisengage = async () => {
    try {
      const status = await disengageKillSwitch('Manual disengage from OCC Dashboard');
      setKillSwitch(status);
    } catch (e) {
      console.error('Disengage failed:', e);
    }
  };

  const handleDisarm = async () => {
    try {
      const status = await disarmKillSwitch('Manual disarm from OCC Dashboard');
      setKillSwitch(status);
    } catch (e) {
      console.error('Disarm failed:', e);
    }
  };

  return (
    <div className="p-6 bg-gray-950 min-h-screen">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">
          Operator Control Center
          <span className="ml-2 text-sm font-normal text-purple-400">
            {session ? `[${session.mode}]` : '[NOT AUTHENTICATED]'}
          </span>
        </h1>
        <p className="text-gray-400 text-sm">
          PAC-BENSON-P42: Real-time OCC Dashboard | PAC-OCC-P23: Grand Unification
        </p>
      </div>

      {/* God-View Banner (PAC-OCC-P23) */}
      <GodView data={godView} loading={loadingGodView} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left Column */}
        <div className="space-y-4">
          <HealthStatus health={health} loading={loadingHealth} />
          <LoginPanel
            session={session}
            onLogin={handleLogin}
            onLogout={handleLogout}
            error={loginError}
          />
          <KillSwitchPanel
            status={killSwitch}
            loading={loadingKillSwitch}
            session={session}
            onArm={handleArm}
            onEngage={handleEngage}
            onDisengage={handleDisengage}
            onDisarm={handleDisarm}
          />
        </div>

        {/* Middle Column */}
        <div className="space-y-4">
          <AgentGrid agents={agents} loading={loadingAgents} />
        </div>

        {/* Right Column */}
        <div className="space-y-4">
          <PDOList
            pdos={pdos}
            loading={loadingPdos}
            filter={pdoFilter}
            onFilterChange={setPdoFilter}
          />
        </div>
      </div>
    </div>
  );
};

export default OCCDashboard;
