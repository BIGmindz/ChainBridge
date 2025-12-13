# Fusion-Adjusted Risk Pricing (PAC-PAX-NEXT-016)

## Mission
Design tokenized risk pricing for corridors, carriers, and lanes, linking Fusion drift to ChainPay settlement discounting.

## 1. Corridor Risk Coefficient Model

The Corridor Risk Coefficient ($C_r$) quantifies the inherent risk of a specific shipping corridor based on historical performance, geopolitical factors, and real-time intelligence.

### Formula
$$ C_r = B_r \times (1 + G_f + S_v) $$

Where:
- $B_r$: Base Risk Score (0.0 - 1.0) derived from historical delay/loss data.
- $G_f$: Geopolitical Factor (0.0 - 0.5) derived from external threat levels.
- $S_v$: Seasonal Volatility (0.0 - 0.3) based on weather/traffic patterns.

### Risk Tiers
| Tier | Coefficient Range | Description |
|------|-------------------|-------------|
| Low | 0.0 - 0.2 | Stable corridor, minimal disruption. |
| Medium | 0.2 - 0.5 | Occasional delays, moderate external risk. |
| High | 0.5 - 0.8 | Frequent disruptions, high geopolitical risk. |
| Critical | > 0.8 | Active conflict zone or severe instability. |

## 2. Fusion-Adjusted APY Model

The Fusion-Adjusted APY ($APY_f$) dynamically adjusts the yield for liquidity providers based on the real-time risk profile of the assets they are underwriting.

### Formula
$$ APY_f = APY_{base} \times (1 + C_r \times D_f) $$

Where:
- $APY_{base}$: Base APY for the asset class (e.g., 5%).
- $C_r$: Corridor Risk Coefficient.
- $D_f$: Drift Factor (0.5 - 2.0), representing the sensitivity to risk.

## 3. CB-USDx Spec Update

CB-USDx is the settlement stablecoin. Its collateralization ratio and settlement speed are now influenced by the Risk Tier.

### Risk-Adjusted Parameters
| Risk Tier | Collateral Ratio | Settlement Time | Fee Modifier |
|-----------|------------------|-----------------|--------------|
| Low | 100% | Instant | 1.0x |
| Medium | 110% | T+1 | 1.2x |
| High | 125% | T+3 | 1.5x |
| Critical | 150% | Manual Review | 2.0x |

## 4. ChainPay Settlement Logic: Risk Tier Modifier

The settlement engine will now query the Risk Pricing Module to determine the applicable fee modifier and settlement timeline before processing a transaction.

### Logic Flow
1. **Transaction Request**: Received with Corridor ID and Carrier ID.
2. **Risk Lookup**: Calculate $C_r$ for the corridor.
3. **Tier Determination**: Map $C_r$ to a Risk Tier.
4. **Fee Calculation**: Apply Fee Modifier to base transaction fee.
5. **Settlement Scheduling**: Set settlement date based on Tier.

## 5. Example Scenarios

### Scenario A: Stable Route (NY-LON)
- **Base Risk ($B_r$)**: 0.05
- **Geopolitical ($G_f$)**: 0.0
- **Seasonal ($S_v$)**: 0.05 (Winter)
- **$C_r$**: $0.05 \times (1 + 0.0 + 0.05) = 0.0525$ (Low Tier)
- **Outcome**: Instant settlement, 1.0x fee.

### Scenario B: Volatile Route (Red Sea)
- **Base Risk ($B_r$)**: 0.3
- **Geopolitical ($G_f$)**: 0.4
- **Seasonal ($S_v$)**: 0.1
- **$C_r$**: $0.3 \times (1 + 0.4 + 0.1) = 0.45$ (Medium Tier)
- **Outcome**: T+1 settlement, 1.2x fee.
