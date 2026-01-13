#!/usr/bin/env python3
"""
Activate GID-00 (BENSON) - Orchestrator Agent
=============================================
Emits heartbeat activation event for the primary orchestrator.
"""

import sys
sys.path.insert(0, '/Users/johnbozza/Documents/Projects/ChainBridge-local-repo')

from ChainBridge.core.orchestration.heartbeat.lifecycle_bindings import LifecycleBindings

def main():
    bindings = LifecycleBindings()
    event = bindings.on_agent_activated('GID-00', 'BENSON', 'Orchestrator')
    
    print('╔════════════════════════════════════════════════════════════════════╗')
    print('║                    AGENT ACTIVATION CONFIRMED                       ║')
    print('╠════════════════════════════════════════════════════════════════════╣')
    print(f'║  Agent GID:    GID-00                                              ║')
    print(f'║  Agent Name:   BENSON                                              ║')
    print(f'║  Role:         Orchestrator                                        ║')
    print(f'║  Status:       ACTIVE                                              ║')
    print(f'║  Timestamp:    {event.timestamp:<52}║')
    print(f'║  Session:      {event.session_id[:48]:<52}║')
    print('╠════════════════════════════════════════════════════════════════════╣')
    print('║  BENSON [GID-00]: "The Orchestrator is online. Systems nominal."    ║')
    print('╚════════════════════════════════════════════════════════════════════╝')

if __name__ == '__main__':
    main()
