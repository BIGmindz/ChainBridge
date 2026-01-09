/**
 * PDODependencyGraph Component
 * 
 * Visualizes cross-agent dependency graph for PDO artifacts.
 * Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-LOAD-024.
 * 
 * Agent: GID-02 (Sonny) — Frontend Engineer
 * 
 * Invariant: INV-UI-010 - Dependency graph must show blocked/pending states
 */

import React, { useMemo, useCallback } from 'react';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

export type NodeStatus = 'PENDING' | 'READY' | 'FINALIZED' | 'BLOCKED';

export interface DependencyNode {
  pdo_id: string;
  agent_gid: string;
  pac_id: string;
  status: NodeStatus;
  created_at: string;
  finalized_at?: string;
}

export interface DependencyEdge {
  edge_id: string;
  upstream_pdo_id: string;
  downstream_pdo_id: string;
  dependency_type: 'DATA' | 'APPROVAL' | 'SEQUENCE';
  created_at: string;
}

export interface DependencyGraphData {
  nodes: DependencyNode[];
  edges: DependencyEdge[];
  statistics?: {
    node_count: number;
    edge_count: number;
    status_distribution: Record<NodeStatus, number>;
    is_acyclic: boolean;
  };
}

export interface PDODependencyGraphProps {
  data: DependencyGraphData | null;
  loading?: boolean;
  error?: string | null;
  onNodeClick?: (node: DependencyNode) => void;
  onRefresh?: () => void;
  selectedNodeId?: string;
  className?: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════════

const STATUS_COLORS: Record<NodeStatus, { bg: string; border: string; text: string }> = {
  PENDING: { bg: '#fef3c7', border: '#f59e0b', text: '#92400e' },
  READY: { bg: '#dbeafe', border: '#3b82f6', text: '#1e40af' },
  FINALIZED: { bg: '#dcfce7', border: '#22c55e', text: '#166534' },
  BLOCKED: { bg: '#fee2e2', border: '#ef4444', text: '#991b1b' },
};

const STATUS_ICONS: Record<NodeStatus, string> = {
  PENDING: '⏳',
  READY: '🔵',
  FINALIZED: '✅',
  BLOCKED: '🚫',
};

const AGENT_COLORS: Record<string, string> = {
  'GID-00': '#6366f1', // Indigo - Orchestrator
  'GID-01': '#8b5cf6', // Purple - Governance
  'GID-02': '#ec4899', // Pink - Frontend
  'GID-07': '#f97316', // Orange - DevOps
  'GID-10': '#14b8a6', // Teal - ML/Risk
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

interface NodeCardProps {
  node: DependencyNode;
  isSelected: boolean;
  onClick: () => void;
  dependencyCount: number;
  dependentCount: number;
}

const NodeCard: React.FC<NodeCardProps> = ({
  node,
  isSelected,
  onClick,
  dependencyCount,
  dependentCount,
}) => {
  const colors = STATUS_COLORS[node.status];
  const agentColor = AGENT_COLORS[node.agent_gid] || '#6b7280';
  
  return (
    <button
      onClick={onClick}
      style={{
        padding: '12px 16px',
        borderRadius: '8px',
        border: `2px solid ${isSelected ? agentColor : colors.border}`,
        backgroundColor: colors.bg,
        cursor: 'pointer',
        textAlign: 'left',
        minWidth: '180px',
        boxShadow: isSelected ? `0 0 0 3px ${agentColor}33` : 'none',
        transition: 'all 0.15s ease',
      }}
      aria-selected={isSelected}
      aria-label={`PDO ${node.pdo_id}, status ${node.status}`}
    >
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '8px',
      }}>
        <span style={{ 
          fontWeight: 600, 
          fontSize: '13px',
          color: colors.text,
        }}>
          {STATUS_ICONS[node.status]} {node.pdo_id}
        </span>
      </div>
      
      {/* Agent Badge */}
      <div style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '9999px',
        backgroundColor: agentColor,
        color: 'white',
        fontSize: '11px',
        fontWeight: 600,
        marginBottom: '8px',
      }}>
        {node.agent_gid}
      </div>
      
      {/* Status */}
      <div style={{
        fontSize: '12px',
        color: colors.text,
        fontWeight: 500,
      }}>
        {node.status}
      </div>
      
      {/* Dependency Info */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '11px',
        color: '#6b7280',
        marginTop: '8px',
      }}>
        <span>↑ {dependencyCount} deps</span>
        <span>↓ {dependentCount} dependents</span>
      </div>
    </button>
  );
};

interface EdgeLineProps {
  fromNode: DependencyNode;
  toNode: DependencyNode;
  edge: DependencyEdge;
  nodePositions: Map<string, { x: number; y: number }>;
}

const EdgeArrow: React.FC<{ 
  type: DependencyEdge['dependency_type'];
  isBlocked: boolean;
}> = ({ type, isBlocked }) => {
  const colors = {
    DATA: '#3b82f6',
    APPROVAL: '#f59e0b',
    SEQUENCE: '#8b5cf6',
  };
  
  return (
    <span style={{
      fontSize: '10px',
      padding: '2px 6px',
      borderRadius: '4px',
      backgroundColor: isBlocked ? '#fee2e2' : `${colors[type]}20`,
      color: isBlocked ? '#991b1b' : colors[type],
      fontWeight: 500,
    }}>
      {type}
    </span>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// LOADING STATE
// ═══════════════════════════════════════════════════════════════════════════════

const LoadingSkeleton: React.FC = () => (
  <div 
    style={{ padding: '24px', textAlign: 'center' }}
    role="status"
    aria-label="Loading dependency graph"
  >
    <div style={{ fontSize: '32px', marginBottom: '16px' }}>🔄</div>
    <div style={{ color: '#6b7280' }}>Loading dependency graph...</div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// EMPTY STATE
// ═══════════════════════════════════════════════════════════════════════════════

const EmptyState: React.FC = () => (
  <div style={{
    padding: '48px 24px',
    textAlign: 'center',
    color: '#6b7280',
  }}>
    <div style={{ fontSize: '48px', marginBottom: '16px' }}>🕸️</div>
    <div style={{ fontSize: '16px' }}>No dependency data</div>
    <div style={{ fontSize: '14px', marginTop: '8px' }}>
      Dependency graph will appear when PDOs are created
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR STATE
// ═══════════════════════════════════════════════════════════════════════════════

const ErrorState: React.FC<{ message: string; onRetry?: () => void }> = ({ 
  message, 
  onRetry 
}) => (
  <div
    style={{
      padding: '24px',
      backgroundColor: '#fee2e2',
      borderRadius: '8px',
      textAlign: 'center',
    }}
    role="alert"
  >
    <div style={{ fontSize: '24px', marginBottom: '8px' }}>❌</div>
    <div style={{ color: '#991b1b', fontWeight: 500, marginBottom: '16px' }}>
      {message}
    </div>
    {onRetry && (
      <button
        onClick={onRetry}
        style={{
          padding: '8px 16px',
          backgroundColor: '#991b1b',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
        }}
      >
        Retry
      </button>
    )}
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// STATISTICS PANEL
// ═══════════════════════════════════════════════════════════════════════════════

const StatisticsPanel: React.FC<{ 
  stats: DependencyGraphData['statistics'] 
}> = ({ stats }) => {
  if (!stats) return null;
  
  return (
    <div style={{
      display: 'flex',
      gap: '16px',
      padding: '12px 16px',
      backgroundColor: '#f9fafb',
      borderRadius: '8px',
      marginBottom: '16px',
    }}>
      <div>
        <div style={{ fontSize: '11px', color: '#6b7280', textTransform: 'uppercase' }}>
          Nodes
        </div>
        <div style={{ fontSize: '18px', fontWeight: 600 }}>{stats.node_count}</div>
      </div>
      <div>
        <div style={{ fontSize: '11px', color: '#6b7280', textTransform: 'uppercase' }}>
          Edges
        </div>
        <div style={{ fontSize: '18px', fontWeight: 600 }}>{stats.edge_count}</div>
      </div>
      <div>
        <div style={{ fontSize: '11px', color: '#6b7280', textTransform: 'uppercase' }}>
          Finalized
        </div>
        <div style={{ fontSize: '18px', fontWeight: 600, color: '#22c55e' }}>
          {stats.status_distribution.FINALIZED || 0}
        </div>
      </div>
      <div>
        <div style={{ fontSize: '11px', color: '#6b7280', textTransform: 'uppercase' }}>
          Blocked
        </div>
        <div style={{ fontSize: '18px', fontWeight: 600, color: '#ef4444' }}>
          {stats.status_distribution.BLOCKED || 0}
        </div>
      </div>
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
        <span style={{
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '12px',
          backgroundColor: stats.is_acyclic ? '#dcfce7' : '#fee2e2',
          color: stats.is_acyclic ? '#166534' : '#991b1b',
        }}>
          {stats.is_acyclic ? '✓ Acyclic' : '⚠ Contains Cycles'}
        </span>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const PDODependencyGraph: React.FC<PDODependencyGraphProps> = ({
  data,
  loading = false,
  error = null,
  onNodeClick,
  onRefresh,
  selectedNodeId,
  className,
}) => {
  // Compute dependency counts for each node
  const dependencyCounts = useMemo(() => {
    if (!data) return { deps: new Map(), dependents: new Map() };
    
    const deps = new Map<string, number>();
    const dependents = new Map<string, number>();
    
    data.nodes.forEach(n => {
      deps.set(n.pdo_id, 0);
      dependents.set(n.pdo_id, 0);
    });
    
    data.edges.forEach(e => {
      deps.set(e.downstream_pdo_id, (deps.get(e.downstream_pdo_id) || 0) + 1);
      dependents.set(e.upstream_pdo_id, (dependents.get(e.upstream_pdo_id) || 0) + 1);
    });
    
    return { deps, dependents };
  }, [data]);

  // Group nodes by level (topological)
  const nodesByLevel = useMemo(() => {
    if (!data) return [];
    
    const levels: DependencyNode[][] = [];
    const processed = new Set<string>();
    const { deps } = dependencyCounts;
    
    // Level 0: nodes with no dependencies
    const level0 = data.nodes.filter(n => deps.get(n.pdo_id) === 0);
    if (level0.length > 0) {
      levels.push(level0);
      level0.forEach(n => processed.add(n.pdo_id));
    }
    
    // Subsequent levels
    while (processed.size < data.nodes.length) {
      const nextLevel = data.nodes.filter(n => {
        if (processed.has(n.pdo_id)) return false;
        
        // Check if all dependencies are processed
        const nodeDeps = data.edges
          .filter(e => e.downstream_pdo_id === n.pdo_id)
          .map(e => e.upstream_pdo_id);
        
        return nodeDeps.every(d => processed.has(d));
      });
      
      if (nextLevel.length === 0) {
        // Handle remaining nodes (cycles or disconnected)
        const remaining = data.nodes.filter(n => !processed.has(n.pdo_id));
        if (remaining.length > 0) {
          levels.push(remaining);
          remaining.forEach(n => processed.add(n.pdo_id));
        }
        break;
      }
      
      levels.push(nextLevel);
      nextLevel.forEach(n => processed.add(n.pdo_id));
    }
    
    return levels;
  }, [data, dependencyCounts]);

  const handleNodeClick = useCallback((node: DependencyNode) => {
    onNodeClick?.(node);
  }, [onNodeClick]);

  // Container styles
  const containerStyle: React.CSSProperties = {
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
    overflow: 'hidden',
  };

  if (loading) {
    return (
      <div style={containerStyle} className={className}>
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div style={containerStyle} className={className}>
        <ErrorState message={error} onRetry={onRefresh} />
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div style={containerStyle} className={className}>
        <EmptyState />
      </div>
    );
  }

  return (
    <div style={containerStyle} className={className}>
      {/* Header */}
      <div style={{
        padding: '16px 24px',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>
            🕸️ Dependency Graph
          </h2>
          <div style={{ color: '#6b7280', fontSize: '13px', marginTop: '4px' }}>
            Cross-agent PDO dependencies
          </div>
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            style={{
              padding: '8px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              backgroundColor: 'white',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            🔄 Refresh
          </button>
        )}
      </div>

      {/* Statistics */}
      <div style={{ padding: '16px 24px 0' }}>
        <StatisticsPanel stats={data.statistics} />
      </div>

      {/* Graph Visualization */}
      <div style={{ 
        padding: '24px',
        overflowX: 'auto',
      }}>
        {/* Level-based layout */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '32px',
          alignItems: 'center',
        }}>
          {nodesByLevel.map((level, levelIndex) => (
            <div key={levelIndex} style={{ width: '100%' }}>
              {/* Level label */}
              <div style={{
                fontSize: '11px',
                color: '#9ca3af',
                textTransform: 'uppercase',
                marginBottom: '12px',
                textAlign: 'center',
              }}>
                Level {levelIndex} {levelIndex === 0 && '(Root)'}
              </div>
              
              {/* Nodes in level */}
              <div style={{
                display: 'flex',
                gap: '16px',
                justifyContent: 'center',
                flexWrap: 'wrap',
              }}>
                {level.map(node => (
                  <NodeCard
                    key={node.pdo_id}
                    node={node}
                    isSelected={selectedNodeId === node.pdo_id}
                    onClick={() => handleNodeClick(node)}
                    dependencyCount={dependencyCounts.deps.get(node.pdo_id) || 0}
                    dependentCount={dependencyCounts.dependents.get(node.pdo_id) || 0}
                  />
                ))}
              </div>
              
              {/* Arrows to next level */}
              {levelIndex < nodesByLevel.length - 1 && (
                <div style={{
                  textAlign: 'center',
                  fontSize: '24px',
                  color: '#d1d5db',
                  marginTop: '16px',
                }}>
                  ↓
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Edge Legend */}
        <div style={{
          marginTop: '24px',
          padding: '12px 16px',
          backgroundColor: '#f9fafb',
          borderRadius: '8px',
          display: 'flex',
          gap: '16px',
          justifyContent: 'center',
          fontSize: '12px',
        }}>
          <span><EdgeArrow type="DATA" isBlocked={false} /> Data dependency</span>
          <span><EdgeArrow type="APPROVAL" isBlocked={false} /> Approval required</span>
          <span><EdgeArrow type="SEQUENCE" isBlocked={false} /> Sequence order</span>
        </div>
      </div>
    </div>
  );
};

export default PDODependencyGraph;
