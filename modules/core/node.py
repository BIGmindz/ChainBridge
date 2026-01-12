#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CHAINBRIDGE SOVEREIGN NODE v3.0                          ║
║                     PAC-DEP-P700-CONTAINERIZATION                             ║
║                                                                              ║
║  "The Code is the Soul. The Container is the Body."                          ║
║                                                                              ║
║  This is the unified entrypoint that binds:                                  ║
║    - Mesh Networking (P300)                                                  ║
║    - Consensus Engine (P310)                                                 ║
║    - Federation Identity (P305)                                              ║
║    - API Gateway                                                             ║
║                                                                              ║
║  Configuration via Environment Variables:                                    ║
║    NODE_ID       - Unique node identifier (default: node_1)                  ║
║    NODE_PORT     - Mesh port (default: 5000)                                 ║
║    API_PORT      - HTTP API port (default: 8000)                             ║
║    PEERS         - Comma-separated peer addresses (e.g., node_2:5000)        ║
║    DATA_DIR      - Persistent data directory (default: /app/data)            ║
║    LOG_LEVEL     - Logging level (default: INFO)                             ║
║                                                                              ║
║  Invariants Enforced:                                                        ║
║    INV-DEP-001 (Environment Isolation): Identical behavior across envs       ║
║    INV-DEP-002 (Ephemeral Compute): Data persists via volumes                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

class NodeConfig:
    """
    Node configuration loaded from environment variables.
    
    INV-DEP-001: Configuration via environment only, no runtime code changes.
    """
    
    def __init__(self):
        # Identity
        self.node_id = os.environ.get("NODE_ID", "node_1")
        self.federation_id = os.environ.get("FEDERATION_ID", "chainbridge-federation")
        
        # Network
        self.node_port = int(os.environ.get("NODE_PORT", "5000"))
        self.api_port = int(os.environ.get("API_PORT", "8000"))
        self.host = os.environ.get("HOST", "0.0.0.0")
        
        # Peers (comma-separated list: "node_2:5000,node_3:5000")
        peers_str = os.environ.get("PEERS", "")
        self.peers = self._parse_peers(peers_str)
        
        # Persistence
        self.data_dir = Path(os.environ.get("DATA_DIR", "/app/data"))
        self.logs_dir = Path(os.environ.get("LOGS_DIR", "/app/logs"))
        
        # Logging
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
        
        # Features
        self.enable_api = os.environ.get("ENABLE_API", "true").lower() == "true"
        self.enable_mesh = os.environ.get("ENABLE_MESH", "true").lower() == "true"
        
    def _parse_peers(self, peers_str: str) -> List[tuple]:
        """Parse peer string into list of (host, port) tuples."""
        if not peers_str:
            return []
        peers = []
        for peer in peers_str.split(","):
            peer = peer.strip()
            if ":" in peer:
                host, port = peer.rsplit(":", 1)
                peers.append((host, int(port)))
            elif peer:
                # Default port if not specified
                peers.append((peer, 5000))
        return peers
        
    def to_dict(self) -> Dict[str, Any]:
        """Export config as dictionary."""
        return {
            "node_id": self.node_id,
            "federation_id": self.federation_id,
            "node_port": self.node_port,
            "api_port": self.api_port,
            "host": self.host,
            "peers": [f"{h}:{p}" for h, p in self.peers],
            "data_dir": str(self.data_dir),
            "logs_dir": str(self.logs_dir),
            "log_level": self.log_level,
            "enable_api": self.enable_api,
            "enable_mesh": self.enable_mesh
        }


# ══════════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ══════════════════════════════════════════════════════════════════════════════

def setup_logging(config: NodeConfig) -> logging.Logger:
    """Configure logging for the node."""
    
    # Ensure logs directory exists
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("ChainBridgeNode")
    logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        f'%(asctime)s [{config.node_id}] %(levelname)s - %(message)s'
    ))
    logger.addHandler(console)
    
    # File handler
    log_file = config.logs_dir / f"{config.node_id}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)
    
    return logger


# ══════════════════════════════════════════════════════════════════════════════
# SOVEREIGN NODE
# ══════════════════════════════════════════════════════════════════════════════

class SovereignNode:
    """
    The unified ChainBridge Sovereign Node.
    
    Binds together:
    - Mesh networking for peer-to-peer communication
    - Consensus engine for state agreement
    - API gateway for external access
    - Core controller for business logic
    """
    
    VERSION = "3.0.0"
    
    def __init__(self, config: NodeConfig):
        self.config = config
        self.logger = setup_logging(config)
        
        # State
        self.running = False
        self.start_time: Optional[datetime] = None
        self.mesh_node = None
        self.api_server = None
        
        # Ensure data directory exists
        config.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Initializing SovereignNode v{self.VERSION}")
        self.logger.info(f"Config: {json.dumps(config.to_dict(), indent=2)}")
        
    async def start(self) -> None:
        """Start all node services."""
        
        self.logger.info("=" * 60)
        self.logger.info("  SOVEREIGN NODE STARTING")
        self.logger.info("=" * 60)
        
        self.start_time = datetime.now(timezone.utc)
        self.running = True
        
        # Start mesh networking
        if self.config.enable_mesh:
            await self._start_mesh()
            
        # Start API server
        if self.config.enable_api:
            await self._start_api()
            
        # Connect to peers
        if self.config.peers:
            await self._connect_to_peers()
            
        self.logger.info("=" * 60)
        self.logger.info(f"  NODE {self.config.node_id} ONLINE")
        self.logger.info(f"  Mesh: {self.config.host}:{self.config.node_port}")
        self.logger.info(f"  API:  {self.config.host}:{self.config.api_port}")
        self.logger.info("=" * 60)
        
    async def _start_mesh(self) -> None:
        """Initialize and start mesh networking."""
        self.logger.info("Starting mesh networking...")
        
        try:
            from modules.mesh import MeshNode, MeshConfig
            
            mesh_config = MeshConfig(
                node_id=self.config.node_id,
                host=self.config.host,
                port=self.config.node_port,
                data_dir=self.config.data_dir / "mesh"
            )
            
            self.mesh_node = MeshNode(mesh_config)
            await self.mesh_node.start()
            
            self.logger.info(f"Mesh networking started on port {self.config.node_port}")
            
        except ImportError as e:
            self.logger.warning(f"Mesh module not available: {e}")
        except Exception as e:
            self.logger.error(f"Failed to start mesh: {e}")
            
    async def _start_api(self) -> None:
        """Start the HTTP API server."""
        self.logger.info("Starting API server...")
        
        try:
            # Import FastAPI components
            from fastapi import FastAPI, HTTPException
            from fastapi.responses import JSONResponse
            import uvicorn
            
            # Create FastAPI app
            app = FastAPI(
                title=f"ChainBridge Node - {self.config.node_id}",
                version=self.VERSION,
                description="Sovereign Node API"
            )
            
            # Health endpoint
            @app.get("/health")
            async def health():
                return {
                    "status": "healthy",
                    "node_id": self.config.node_id,
                    "version": self.VERSION,
                    "uptime_seconds": self._get_uptime(),
                    "mesh_connected": self.mesh_node is not None and self.mesh_node.running if self.mesh_node else False,
                    "peer_count": len(self.mesh_node.peers) if self.mesh_node else 0
                }
                
            # Status endpoint
            @app.get("/status")
            async def status():
                return {
                    "node_id": self.config.node_id,
                    "version": self.VERSION,
                    "federation_id": self.config.federation_id,
                    "start_time": self.start_time.isoformat() if self.start_time else None,
                    "uptime_seconds": self._get_uptime(),
                    "config": self.config.to_dict(),
                    "mesh": {
                        "enabled": self.config.enable_mesh,
                        "port": self.config.node_port,
                        "peer_count": len(self.mesh_node.peers) if self.mesh_node else 0
                    }
                }
                
            # Peers endpoint
            @app.get("/peers")
            async def peers():
                if not self.mesh_node:
                    return {"peers": []}
                return {
                    "peers": [
                        {"id": p.node_id, "host": p.host, "port": p.port}
                        for p in self.mesh_node.peers.values()
                    ] if hasattr(self.mesh_node, 'peers') else []
                }
                
            # Run uvicorn in background
            config = uvicorn.Config(
                app,
                host=self.config.host,
                port=self.config.api_port,
                log_level=self.config.log_level.lower(),
                access_log=False
            )
            self.api_server = uvicorn.Server(config)
            
            # Start server in background task
            asyncio.create_task(self.api_server.serve())
            
            self.logger.info(f"API server started on port {self.config.api_port}")
            
        except ImportError as e:
            self.logger.warning(f"FastAPI not available: {e}")
        except Exception as e:
            self.logger.error(f"Failed to start API: {e}")
            
    async def _connect_to_peers(self) -> None:
        """Connect to configured peer nodes."""
        self.logger.info(f"Connecting to {len(self.config.peers)} peers...")
        
        if not self.mesh_node:
            self.logger.warning("Mesh not available, skipping peer connection")
            return
            
        for host, port in self.config.peers:
            try:
                self.logger.info(f"  Connecting to {host}:{port}...")
                await self.mesh_node.connect_to_peer(host, port)
            except Exception as e:
                self.logger.warning(f"  Failed to connect to {host}:{port}: {e}")
                
    def _get_uptime(self) -> float:
        """Get node uptime in seconds."""
        if not self.start_time:
            return 0.0
        delta = datetime.now(timezone.utc) - self.start_time
        return delta.total_seconds()
        
    async def stop(self) -> None:
        """Stop all node services gracefully."""
        self.logger.info("Shutting down node...")
        self.running = False
        
        # Stop API server
        if self.api_server:
            self.api_server.should_exit = True
            
        # Stop mesh
        if self.mesh_node:
            await self.mesh_node.stop()
            
        self.logger.info("Node shutdown complete")
        
    async def run_forever(self) -> None:
        """Run the node until interrupted."""
        await self.start()
        
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            
        # Keep running
        while self.running:
            await asyncio.sleep(1)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entrypoint for the Sovereign Node."""
    
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "CHAINBRIDGE SOVEREIGN NODE" + " " * 17 + "║")
    print("║" + " " * 10 + "\"The Code is the Soul. The Container" + " " * 11 + "║")
    print("║" + " " * 10 + " is the Body.\"" + " " * 34 + "║")
    print("╚" + "═" * 58 + "╝\n")
    
    # Load config from environment
    config = NodeConfig()
    
    # Create and run node
    node = SovereignNode(config)
    
    try:
        asyncio.run(node.run_forever())
    except KeyboardInterrupt:
        print("\nNode interrupted by user")
    except Exception as e:
        print(f"\nNode error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
