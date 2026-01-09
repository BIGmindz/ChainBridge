/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * PAC Rejection Feedback Panel — OCC UI Component
 * PAC-JEFFREY-C05: Deterministic rejection display
 * 
 * INVARIANTS:
 * - INV-PAC-010: Rejection reasons MUST be enumerable
 * - INV-PAC-011: Schema MUST be machine-verifiable
 * - INV-PAC-012: Operator feedback MUST be deterministic
 * - INV-OCC-UI-001: All state is read-only from backend
 * 
 * Author: SONNY (GID-02) — Frontend
 * Constitutional Reference: OCC_CONSTITUTION_v1.0
 * ═══════════════════════════════════════════════════════════════════════════════
 */

import React, { useState } from 'react';
import type { 
  PACUploadResponse, 
  PACUploadRejection, 
  PACUploadSuccess,
  RejectionCategory 
} from './pacRejectionTypes';
import { 
  CATEGORY_ICONS, 
  SEVERITY_COLORS,
  getRejectionCode 
} from './pacRejectionTypes';

// ═══════════════════════════════════════════════════════════════════════════════
// PROPS
// ═══════════════════════════════════════════════════════════════════════════════

interface PACRejectionFeedbackProps {
  response: PACUploadResponse | null;
  loading?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// SUCCESS PANEL
// ═══════════════════════════════════════════════════════════════════════════════

const SuccessPanel: React.FC<{ success: PACUploadSuccess }> = ({ success }) => (
  <div className="bg-green-900/30 border border-green-700 rounded-lg p-4">
    <div className="flex items-center gap-3 mb-3">
      <span className="text-2xl">✅</span>
      <div>
        <h3 className="font-semibold text-green-300">PAC Accepted</h3>
        <p className="text-sm text-green-400">{success.pacId}</p>
      </div>
    </div>
    
    <div className="grid grid-cols-2 gap-4 text-sm">
      <div>
        <span className="text-gray-400">Accepted At:</span>
        <p className="text-green-300 font-mono">
          {new Date(success.acceptedAt).toLocaleString()}
        </p>
      </div>
      <div>
        <span className="text-gray-400">Hash:</span>
        <p className="text-green-300 font-mono text-xs truncate" title={success.hash}>
          {success.hash.substring(0, 16)}...{success.hash.substring(48)}
        </p>
      </div>
    </div>
    
    <div className="mt-3 pt-3 border-t border-green-700/50 text-xs text-gray-500">
      INV-PAC-011: Schema validation passed
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// REJECTION PANEL
// ═══════════════════════════════════════════════════════════════════════════════

const RejectionPanel: React.FC<{ rejection: PACUploadRejection }> = ({ rejection }) => {
  const [expanded, setExpanded] = useState(false);
  const def = getRejectionCode(rejection.rejectionCode);
  
  return (
    <div 
      className="bg-red-900/30 border border-red-700 rounded-lg overflow-hidden"
      style={{ borderLeftWidth: '4px', borderLeftColor: SEVERITY_COLORS[rejection.severity] }}
    >
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{CATEGORY_ICONS[rejection.category]}</span>
            <div>
              <h3 className="font-semibold text-red-300">{rejection.rejectionMessage}</h3>
              <div className="flex items-center gap-2 mt-1">
                <span className="px-2 py-0.5 text-xs bg-red-800 text-red-200 rounded font-mono">
                  {rejection.rejectionCode}
                </span>
                <span className="px-2 py-0.5 text-xs bg-gray-700 text-gray-300 rounded">
                  {rejection.category}
                </span>
                <span 
                  className="px-2 py-0.5 text-xs rounded font-medium"
                  style={{ 
                    backgroundColor: `${SEVERITY_COLORS[rejection.severity]}20`,
                    color: SEVERITY_COLORS[rejection.severity]
                  }}
                >
                  {rejection.severity}
                </span>
              </div>
            </div>
          </div>
          
          {rejection.pacId && (
            <span className="text-sm text-gray-500 font-mono">
              {rejection.pacId}
            </span>
          )}
        </div>
        
        {/* Operator Feedback (INV-PAC-012) */}
        <div className="mt-4 p-3 bg-gray-900 rounded border border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-red-400">⚠️</span>
            <span className="text-sm font-medium text-gray-300">Operator Feedback</span>
            <span className="text-xs text-gray-500">(INV-PAC-012)</span>
          </div>
          <p className="text-sm text-red-300">{rejection.operatorFeedback}</p>
        </div>
        
        {/* Resolution */}
        <div className="mt-3 p-3 bg-blue-900/20 rounded border border-blue-800/50">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-blue-400">💡</span>
            <span className="text-sm font-medium text-gray-300">Resolution</span>
          </div>
          <p className="text-sm text-blue-300">{rejection.resolution}</p>
        </div>
      </div>
      
      {/* Expandable Details */}
      {def && (
        <div className="border-t border-red-800/50">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full px-4 py-2 text-sm text-gray-400 hover:text-gray-300 flex items-center justify-between"
          >
            <span>Technical Details</span>
            <span>{expanded ? '▲' : '▼'}</span>
          </button>
          
          {expanded && (
            <div className="px-4 pb-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-gray-500">Description:</span>
                  <p className="text-gray-300">{def.description}</p>
                </div>
                <div>
                  <span className="text-gray-500">Rejected At:</span>
                  <p className="text-gray-300 font-mono">
                    {new Date(rejection.rejectedAt).toLocaleString()}
                  </p>
                </div>
              </div>
              
              {rejection.details && Object.keys(rejection.details).length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-700">
                  <span className="text-gray-500">Parameters:</span>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {Object.entries(rejection.details).map(([key, value]) => (
                      <span 
                        key={key}
                        className="px-2 py-1 bg-gray-800 rounded text-xs"
                      >
                        <span className="text-gray-500">{key}:</span>{' '}
                        <span className="text-gray-300 font-mono">{value}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Invariant Footer */}
      <div className="px-4 py-2 bg-gray-900/50 text-xs text-gray-500 flex items-center justify-between">
        <span>INV-PAC-010: Enumerable rejection</span>
        <span>Deterministic • Machine-verifiable</span>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// LOADING STATE
// ═══════════════════════════════════════════════════════════════════════════════

const LoadingPanel: React.FC = () => (
  <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
    <div className="flex items-center gap-3">
      <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      <span className="text-gray-300">Validating PAC submission...</span>
    </div>
    <div className="mt-3 text-xs text-gray-500">
      Schema validation in progress (INV-PAC-011)
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// EMPTY STATE
// ═══════════════════════════════════════════════════════════════════════════════

const EmptyPanel: React.FC = () => (
  <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 text-center">
    <span className="text-4xl">📋</span>
    <h3 className="mt-3 text-gray-300 font-medium">No PAC Submission</h3>
    <p className="mt-1 text-sm text-gray-500">
      Submit a PAC to see validation feedback
    </p>
    <div className="mt-4 text-xs text-gray-600">
      Feedback governed by INV-PAC-010, INV-PAC-011, INV-PAC-012
    </div>
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const PACRejectionFeedback: React.FC<PACRejectionFeedbackProps> = ({
  response,
  loading = false,
}) => {
  if (loading) {
    return <LoadingPanel />;
  }
  
  if (!response) {
    return <EmptyPanel />;
  }
  
  if (response.status === 'ACCEPTED') {
    return <SuccessPanel success={response} />;
  }
  
  return <RejectionPanel rejection={response} />;
};

// ═══════════════════════════════════════════════════════════════════════════════
// REJECTION LIST COMPONENT (for multiple validation errors)
// ═══════════════════════════════════════════════════════════════════════════════

interface PACRejectionListProps {
  rejections: PACUploadRejection[];
}

export const PACRejectionList: React.FC<PACRejectionListProps> = ({ rejections }) => {
  if (rejections.length === 0) {
    return null;
  }
  
  // Group by category
  const grouped = rejections.reduce((acc, rej) => {
    if (!acc[rej.category]) {
      acc[rej.category] = [];
    }
    acc[rej.category].push(rej);
    return acc;
  }, {} as Record<RejectionCategory, PACUploadRejection[]>);
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-red-300">
          Validation Errors ({rejections.length})
        </h2>
        <span className="text-xs text-gray-500">
          INV-PAC-010: Enumerable rejections
        </span>
      </div>
      
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category} className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <span>{CATEGORY_ICONS[category as RejectionCategory]}</span>
            <span>{category}</span>
            <span className="text-gray-600">({items.length})</span>
          </div>
          
          <div className="space-y-2 pl-6">
            {items.map((rej, idx) => (
              <RejectionPanel key={`${rej.rejectionCode}-${idx}`} rejection={rej} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export default PACRejectionFeedback;
