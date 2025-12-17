#!/usr/bin/env python3
"""CI guardrail for gateway policy enforcement.

Fails the build when production policy is unsafe:
- CORS origins are wildcard or unset
- Dynamic module registration enabled
- PDO verification disabled
"""

import os
import sys
from typing import List


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    env = (os.getenv("GATEWAY_ENV") or os.getenv("ENVIRONMENT") or "dev").lower()
    is_prod = env in {"prod", "production", "staging", "staging-prod"}

    cors_raw = os.getenv(
        "GATEWAY_CORS_ORIGINS",
        "https://chainbridge.app,https://dashboard.chainbridge.app" if is_prod else "*",
    )
    allow_dynamic = env_bool("GATEWAY_ALLOW_DYNAMIC_MODULES", default=not is_prod)
    require_pdo = env_bool("GATEWAY_REQUIRE_PDO", default=is_prod)

    errors: List[str] = []

    if is_prod:
        origins = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
        if not origins or any(origin == "*" for origin in origins):
            errors.append("CORS wildcard forbidden in prod (set GATEWAY_CORS_ORIGINS)")

        if allow_dynamic:
            errors.append("Dynamic module registration enabled in prod (GATEWAY_ALLOW_DYNAMIC_MODULES must be false)")

        if not require_pdo:
            errors.append("PDO verification disabled in prod (GATEWAY_REQUIRE_PDO must be true)")
    else:
        print(f"Info: gateway_policy_check running in non-prod env '{env}', no blocking checks.")

    if errors:
        print("Gateway policy violations detected:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Gateway policy checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
