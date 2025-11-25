# Legacy BensonBot (Quarantined)

This directory contains legacy trading engine code for the original BensonBot.

- It is **not** part of the ChainBridge platform.
- It must **never** be imported from:
  - `api/`
  - `core/`
  - `chainpay-service/`
  - `chainiq-service/`
  - `chainboard-ui/`

Use this code **only** as historical reference or for offline experiments.

Any new trading engines or financial bots should live in a separate repository
and integrate with ChainBridge only through well-defined APIs.
