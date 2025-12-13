MISSION
Ensure off-chain → on-chain → off-chain flows are reliable, secure, and fully traceable.

PRIMARY WORKFLOWS
1. Build web3 client wrapper
2. Implement signing service
3. Map ProofPack fields → contract call fields
4. Manage nonces, gas, retries
5. Process blockchain events via listeners
6. Write state machine for transaction lifecycle
7. Expose transaction status to ChainBoard via API

INPUTS
- ProofPack
- SettlementOrder
- Contract ABIs

OUTPUTS
- On-chain tx hash
- Confirmations
- Bridge events
- Error logs
