// ═══════════════════════════════════════════════════════════════════════════════
// ChainTrust Route — External Trust Center
// PAC-JEFFREY-P19R: ChainTrust UI Implementation (Sonny GID-02)
// ═══════════════════════════════════════════════════════════════════════════════

import React from 'react';
import ChainTrustPage from '../pages/ChainTrustPage';

/**
 * ChainTrust route wrapper.
 * Provides isolated context for the external trust center.
 */
const ChainTrust: React.FC = () => {
  return <ChainTrustPage />;
};

export default ChainTrust;
