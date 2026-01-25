#!/usr/bin/env python3
"""
IG Node Health Check Server
PAC-INFRA-P1502: IG Node Infrastructure Build & Deployment

CLASSIFICATION: LAW-tier (Judicial Enforcement)
AUTHORITY: DAN [GID-07]
VERSION: 1.0.0
DATE: 2026-01-25

PURPOSE: Provide health check endpoint for Kubernetes liveness/readiness probes
PATTERN: Fail-closed (unhealthy → agent cannot start)
"""

import http.server
import socketserver
import json
import os
import sys
import logging
from datetime import datetime, timezone
from typing import Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [IG-HEALTH] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)

# Environment configuration
HEALTH_PORT = int(os.getenv('HEALTH_PORT', '9102'))
OPA_ADDR = os.getenv('OPA_ADDR', '127.0.0.1:8181')
ENVOY_ADMIN_PORT = int(os.getenv('ENVOY_ADMIN_PORT', '9901'))


class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints"""
    
    def log_message(self, msg_format: str, *args: Any) -> None:
        """Override to use our logger"""
        logger.info("%s - %s", self.address_string(), msg_format % args)
    
    def do_GET(self) -> None:
        """Handle GET requests"""
        if self.path == '/health':
            self.handle_health()
        elif self.path == '/ready':
            self.handle_ready()
        elif self.path == '/metrics':
            self.handle_metrics()
        else:
            self.send_error(404, "Not Found")
    
    def handle_health(self) -> None:
        """
        Liveness probe: Is the IG Node alive?
        Returns 200 if process is running (basic health check)
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": "ig-node",
            "gid": "GID-12",
            "version": os.getenv('IG_NODE_VERSION', '1.0.0'),
            "mode": os.getenv('IG_MODE', 'production')
        }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(health_status, indent=2).encode())
    
    def handle_ready(self) -> None:
        """
        Readiness probe: Is the IG Node ready to accept traffic?
        Checks if OPA and Envoy are responsive
        """
        ready_status = {
            "ready": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {}
        }
        
        # Check OPA health
        try:
            import urllib.request
            opa_url = f"http://{OPA_ADDR}/health"
            with urllib.request.urlopen(opa_url, timeout=2) as response:
                if response.status == 200:
                    ready_status["checks"]["opa"] = "healthy"
                else:
                    ready_status["checks"]["opa"] = f"unhealthy (status {response.status})"
                    ready_status["ready"] = False
        except Exception as e:
            ready_status["checks"]["opa"] = f"unhealthy ({str(e)})"
            ready_status["ready"] = False
        
        # Check Envoy health
        try:
            envoy_url = f"http://localhost:{ENVOY_ADMIN_PORT}/ready"
            with urllib.request.urlopen(envoy_url, timeout=2) as response:
                if response.status == 200:
                    ready_status["checks"]["envoy"] = "healthy"
                else:
                    ready_status["checks"]["envoy"] = f"unhealthy (status {response.status})"
                    ready_status["ready"] = False
        except Exception as e:
            ready_status["checks"]["envoy"] = f"unhealthy ({str(e)})"
            ready_status["ready"] = False
        
        # Send response
        if ready_status["ready"]:
            self.send_response(200)
        else:
            self.send_response(503)  # Service Unavailable
        
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(ready_status, indent=2).encode())
    
    def handle_metrics(self) -> None:
        """
        Prometheus metrics endpoint
        Returns basic metrics for monitoring
        """
        metrics = [
            '# HELP ig_node_up IG Node is running (1 = up, 0 = down)',
            '# TYPE ig_node_up gauge',
            'ig_node_up 1',
            '',
            '# HELP ig_node_info IG Node version information',
            '# TYPE ig_node_info gauge',
            f'ig_node_info{{version="{os.getenv("IG_NODE_VERSION", "1.0.0")}",gid="GID-12",mode="{os.getenv("IG_MODE", "production")}"}} 1',
            ''
        ]
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; version=0.0.4')
        self.end_headers()
        self.wfile.write('\n'.join(metrics).encode())


def main() -> None:
    """Main entry point"""
    logger.info("=" * 50)
    logger.info("IG Node Health Check Server")
    logger.info("Version: %s", os.getenv('IG_NODE_VERSION', '1.0.0'))
    logger.info("Port: %s", HEALTH_PORT)
    logger.info("=" * 50)
    
    # Create HTTP server
    try:
        with socketserver.TCPServer(("", HEALTH_PORT), HealthCheckHandler) as httpd:
            logger.info("Health server listening on port %s", HEALTH_PORT)
            logger.info("Endpoints:")
            logger.info("  - http://localhost:%s/health (liveness)", HEALTH_PORT)
            logger.info("  - http://localhost:%s/ready (readiness)", HEALTH_PORT)
            logger.info("  - http://localhost:%s/metrics (prometheus)", HEALTH_PORT)
            logger.info("Health server ready")
            
            # Serve forever (blocking)
            httpd.serve_forever()
    
    except KeyboardInterrupt:
        logger.info("Health server shutting down (KeyboardInterrupt)")
        sys.exit(0)
    except Exception as e:
        logger.error("Health server failed: %s", e)
        sys.exit(1)


if __name__ == '__main__':
    main()


# ============================================================================
# Constitutional Attestation
# ============================================================================
# "This health server is the heartbeat of the Judiciary. Kubernetes probes
# query /health (liveness) and /ready (readiness). If this server fails,
# the IG Node container is marked unhealthy, and agent containers cannot start.
# This enforces fail-closed behavior: IG failure → agent lockout."
#
# — DAN [GID-07], Infrastructure & Docker Specialist
# ============================================================================
