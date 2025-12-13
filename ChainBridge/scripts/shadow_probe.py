#!/usr/bin/env python3
"""
Shadow Mode Synthetic Performance Probe

Tests Shadow Mode API endpoints for:
- Response latency (p50, p95, p99)
- Response size
- Schema validation (model_version, drift fields)
- Endpoint availability

GOVERNANCE: ALEX Rule #12 - Shadow Mode Performance Budget Enforcement
AUTHOR: DAN (GID-07)
PAC: DAN-PAC-023
"""

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    print("❌ requests library required: pip install requests")
    sys.exit(1)


@dataclass
class PerformanceResult:
    """Performance test result for a single endpoint"""

    endpoint: str
    latencies_ms: List[float]
    response_sizes_bytes: List[int]
    failures: List[str]

    @property
    def p50(self) -> float:
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0.0

    @property
    def p95(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[index]

    @property
    def p99(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_latencies = sorted(self.latencies_ms)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[index]

    @property
    def avg_size_kb(self) -> float:
        if not self.response_sizes_bytes:
            return 0.0
        return statistics.mean(self.response_sizes_bytes) / 1024


class ShadowProbe:
    """Synthetic probe for Shadow Mode API performance testing"""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        iterations: int = 20,
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.iterations = iterations
        self.timeout = timeout
        self.results: Dict[str, PerformanceResult] = {}

    def probe_endpoint(self, path: str, method: str = "GET", json_payload: Dict = None) -> PerformanceResult:
        """
        Probe a single endpoint multiple times and collect performance metrics
        """
        latencies = []
        sizes = []
        failures = []

        print(f"\n🔍 Probing {method} {path}")
        print(f"   Iterations: {self.iterations}")

        for i in range(self.iterations):
            try:
                start_time = time.perf_counter()

                if method == "GET":
                    response = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
                elif method == "POST":
                    response = requests.post(f"{self.base_url}{path}", json=json_payload, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                latency_ms = (time.perf_counter() - start_time) * 1000

                # Record metrics
                latencies.append(latency_ms)
                sizes.append(len(response.content))

                # Validate response
                if response.status_code != 200:
                    failures.append(f"HTTP {response.status_code}")
                    continue

                # Validate JSON structure
                try:
                    data = response.json()
                    self._validate_response_schema(data, path)
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    failures.append(f"Schema validation error: {e}")

                # Progress indicator
                if (i + 1) % 5 == 0:
                    print(f"   Progress: {i + 1}/{self.iterations}")

            except requests.RequestException as e:
                failures.append(f"Request failed: {e}")
            except Exception as e:
                failures.append(f"Unexpected error: {e}")

        result = PerformanceResult(endpoint=path, latencies_ms=latencies, response_sizes_bytes=sizes, failures=failures)

        self._print_result(result)
        return result

    def _validate_response_schema(self, data: Any, path: str) -> None:
        """
        Validate response schema contains required fields

        Raises ValueError if schema validation fails
        """
        if "/shadow/stats" in path:
            # Validate stats endpoint schema
            if not isinstance(data, dict):
                raise ValueError("Stats response must be a dictionary")

            # Check for model_version (SAM requirement)
            if "model_version" not in data:
                raise ValueError("Missing model_version field (SAM REQUIREMENT)")

            # Check for performance metrics
            required_fields = ["p50", "p95", "p99", "count"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Check for drift/delta fields (ALEX requirement)
            drift_fields = ["avg_delta", "max_delta", "corridors"]
            drift_found = any(field in data for field in drift_fields)
            if not drift_found:
                raise ValueError("Missing drift detection fields (ALEX REQUIREMENT)")

        elif "/shadow/events" in path:
            # Validate events endpoint schema
            if not isinstance(data, dict):
                raise ValueError("Events response must be a dictionary")

            if "events" not in data:
                raise ValueError("Missing 'events' array")

            events = data["events"]
            if not isinstance(events, list):
                raise ValueError("'events' must be an array")

            # Validate first event if present
            if events:
                event = events[0]
                required_event_fields = ["corridor", "timestamp", "delta"]
                for field in required_event_fields:
                    if field not in event:
                        raise ValueError(f"Event missing field: {field}")

    def _print_result(self, result: PerformanceResult) -> None:
        """Print formatted result for a single endpoint"""
        print(f"\n   Results for {result.endpoint}:")
        print(f"   ├─ p50: {result.p50:.2f}ms")
        print(f"   ├─ p95: {result.p95:.2f}ms")
        print(f"   ├─ p99: {result.p99:.2f}ms")
        print(f"   ├─ Avg size: {result.avg_size_kb:.2f}KB")
        print(f"   └─ Failures: {len(result.failures)}/{self.iterations}")

        if result.failures:
            print("\n   ⚠️  Failure details:")
            for failure in result.failures[:3]:  # Show first 3 failures
                print(f"      - {failure}")

    def run_all_probes(self) -> None:
        """Run all shadow mode endpoint probes"""
        print("=" * 80)
        print("🟦 Shadow Mode Performance Probe")
        print("=" * 80)
        print(f"Base URL: {self.base_url}")
        print(f"Iterations per endpoint: {self.iterations}")
        print(f"Timeout: {self.timeout}s")

        # Probe 1: Shadow statistics endpoint
        self.results["/iq/shadow/stats"] = self.probe_endpoint("/iq/shadow/stats")

        # Probe 2: Shadow events endpoint
        self.results["/iq/shadow/events"] = self.probe_endpoint("/iq/shadow/events", method="POST", json_payload={"limit": 10})

        print("\n" + "=" * 80)

    def validate_budgets(self, p95_threshold: float = 75.0, p99_threshold: float = 120.0, max_size_kb: float = 25.0) -> bool:
        """
        Validate performance against budgets

        Returns True if all budgets met, False otherwise
        """
        print("\n🟩 ALEX Governance: Performance Budget Validation")
        print("   Thresholds:")
        print(f"   ├─ p95 < {p95_threshold}ms")
        print(f"   ├─ p99 < {p99_threshold}ms")
        print(f"   └─ Size < {max_size_kb}KB")

        violations = []

        for endpoint, result in self.results.items():
            print(f"\n   Checking {endpoint}:")

            # Check p95
            if result.p95 > p95_threshold:
                violation = f"{endpoint}: p95={result.p95:.2f}ms exceeds {p95_threshold}ms"
                violations.append(violation)
                print(f"   ❌ {violation}")
            else:
                print(f"   ✅ p95={result.p95:.2f}ms < {p95_threshold}ms")

            # Check p99
            if result.p99 > p99_threshold:
                violation = f"{endpoint}: p99={result.p99:.2f}ms exceeds {p99_threshold}ms"
                violations.append(violation)
                print(f"   ❌ {violation}")
            else:
                print(f"   ✅ p99={result.p99:.2f}ms < {p99_threshold}ms")

            # Check size
            if result.avg_size_kb > max_size_kb:
                violation = f"{endpoint}: size={result.avg_size_kb:.2f}KB exceeds {max_size_kb}KB"
                violations.append(violation)
                print(f"   ❌ {violation}")
            else:
                print(f"   ✅ size={result.avg_size_kb:.2f}KB < {max_size_kb}KB")

            # Check failures
            failure_rate = len(result.failures) / self.iterations
            if failure_rate > 0.05:  # More than 5% failures
                violation = f"{endpoint}: {failure_rate*100:.1f}% failure rate exceeds 5%"
                violations.append(violation)
                print(f"   ❌ {violation}")
            elif result.failures:
                print(f"   ⚠️  {len(result.failures)} failures (within threshold)")
            else:
                print("   ✅ No failures")

        if violations:
            print("\n" + "=" * 80)
            print("❌ PERFORMANCE BUDGET VIOLATIONS DETECTED")
            print("=" * 80)
            for violation in violations:
                print(f"   - {violation}")
            print("\n🚫 PR BLOCKED: Performance budgets not met (ALEX Rule #12)")
            return False
        else:
            print("\n" + "=" * 80)
            print("✅ ALL PERFORMANCE BUDGETS MET")
            print("=" * 80)
            return True

    def save_results(self, output_path: str = "/tmp/shadow_probe_results.json") -> None:
        """Save probe results to JSON file"""
        results_dict = {
            "timestamp": time.time(),
            "base_url": self.base_url,
            "iterations": self.iterations,
            "endpoints": {
                endpoint: {
                    "p50": result.p50,
                    "p95": result.p95,
                    "p99": result.p99,
                    "avg_size_kb": result.avg_size_kb,
                    "failures": len(result.failures),
                    "failure_rate": len(result.failures) / self.iterations,
                }
                for endpoint, result in self.results.items()
            },
        }

        with open(output_path, "w") as f:
            json.dump(results_dict, f, indent=2)

        print(f"\n📊 Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Shadow Mode Synthetic Performance Probe")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for ChainIQ service (default: http://localhost:8000)")
    parser.add_argument("--iterations", type=int, default=20, help="Number of iterations per endpoint (default: 20)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds (default: 10)")
    parser.add_argument("--p95-threshold", type=float, default=75.0, help="p95 latency threshold in ms (default: 75)")
    parser.add_argument("--p99-threshold", type=float, default=120.0, help="p99 latency threshold in ms (default: 120)")
    parser.add_argument("--max-size-kb", type=float, default=25.0, help="Maximum response size in KB (default: 25)")
    parser.add_argument(
        "--output", default="/tmp/shadow_probe_results.json", help="Output path for results JSON (default: /tmp/shadow_probe_results.json)"
    )

    args = parser.parse_args()

    # Create and run probe
    probe = ShadowProbe(base_url=args.base_url, iterations=args.iterations, timeout=args.timeout)

    try:
        probe.run_all_probes()
        probe.save_results(args.output)

        # Validate budgets and exit with appropriate code
        budgets_met = probe.validate_budgets(
            p95_threshold=args.p95_threshold, p99_threshold=args.p99_threshold, max_size_kb=args.max_size_kb
        )

        sys.exit(0 if budgets_met else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Probe interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Probe failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
